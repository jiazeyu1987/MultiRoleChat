"""
简化的LLM对话API

基于simple_llm.py的重写版本，专注于Anthropic集成
大幅简化架构复杂度，保持API兼容性
"""
from flask import request, jsonify, Blueprint
from flask_restful import Resource
import logging
import traceback
from datetime import datetime
import asyncio

from app.services.llm.manager import llm_manager, LLMMessage
from app.services.llm.conversation_service import LLMError
from app.utils.request_tracker import RequestTracker, log_llm_info, log_llm_error, log_llm_warning

logger = logging.getLogger(__name__)

llm_bp = Blueprint('llm', __name__)


class LLMChatResource(Resource):
    """简化的LLM对话资源"""

    def post(self):
        """发送消息到LLM并获取回复"""
        # 生成唯一请求ID用于追踪
        request_id = RequestTracker.generate_request_id()

        # 提取用户和会话信息
        user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
        session_id = request.args.get('session_id') or request.headers.get('X-Session-ID')

        # 添加调试信息
        print(f"DEBUG: 开始处理LLM请求，request_id={request_id}")

        with RequestTracker.track_request(
            request_id=request_id,
            layer="API",
            user_id=user_id,
            session_id=session_id
        ):
            print(f"DEBUG: 进入请求上下文，开始处理请求")
            try:
                data = request.get_json()

                # 验证请求数据
                if not data or 'message' not in data:
                    log_llm_warning("API", "请求验证失败: 缺少必需的message参数", request_id)
                    return {
                        'success': False,
                        'error_code': 'INVALID_REQUEST',
                        'message': '缺少必需的message参数'
                    }, 400

                message = data['message'].strip()
                history = data.get('history', [])
                provider = data.get('provider', None)  # 简化版本忽略此参数

                if not message:
                    log_llm_warning("API", "请求验证失败: 消息内容为空", request_id)
                    return {
                        'success': False,
                        'error_code': 'EMPTY_MESSAGE',
                        'message': '消息内容不能为空'
                    }, 400

                # 记录请求接收信息
                log_llm_info(
                    "API",
                    "收到LLM对话请求",
                    request_id,
                    message_length=len(message),
                    history_count=len(history),
                    user_id=user_id,
                    session_id=session_id
                )

                # 记录完整的提示词内容
                log_llm_info(
                    "API",
                    "用户输入消息内容",
                    request_id,
                    content=message,
                    message_length=len(message)
                )

                # 构建LLM消息列表
                llm_messages = []

                # 添加历史消息
                for i, msg in enumerate(history):
                    if isinstance(msg, dict):
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        if content:
                            llm_messages.append(LLMMessage(role=role, content=content))
                            log_llm_info(
                                "API",
                                f"历史消息[{i}] - {role}",
                                request_id,
                                content=content,
                                content_length=len(content)
                            )

                # 添加当前用户消息
                llm_messages.append(LLMMessage(role='user', content=message))
                log_llm_info(
                    "API",
                    "当前消息添加完成，准备调用LLM管理器",
                    request_id,
                    total_messages=len(llm_messages)
                )

                # 记录提示词预览
                full_prompt = ""
                for msg in llm_messages:
                    full_prompt += f"{msg.role}: {msg.content}\n"

                log_llm_info(
                    "API",
                    "完整提示词构建完成",
                    request_id,
                    content=full_prompt.strip(),
                    total_prompt_length=len(full_prompt),
                    message_count=len(llm_messages)
                )

                # 调用简化的LLM管理器
                start_time = datetime.now()
                log_llm_info("API", "开始调用LLM管理器", request_id, start_time=start_time.isoformat())

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(
                        llm_manager.generate_response(
                            provider=provider,
                            messages=llm_messages,
                            request_id=request_id  # 传递request_id
                        )
                    )
                finally:
                    loop.close()
                end_time = datetime.now()

                # 计算响应时间
                response_time = (end_time - start_time).total_seconds()

                # 检查响应是否成功
                is_success = not response.content.startswith('调用失败')
                if is_success:
                    log_llm_info(
                        "API",
                        "LLM回复成功",
                        request_id,
                        response_length=len(response.content),
                        response_time=f"{response_time:.2f}s",
                        model=response.model,
                        provider=response.provider,
                        usage=response.usage
                    )

                    # 记录完整的返回内容
                    log_llm_info(
                        "API",
                        "LLM返回内容详情",
                        request_id,
                        content=response.content,
                        content_length=len(response.content),
                        is_success=is_success
                    )
                else:
                    log_llm_error(
                        "API",
                        "LLM调用失败",
                        request_id,
                        error_content=response.content,
                        response_time=f"{response_time:.2f}s"
                    )

                # 记录LLM调用指标到监控系统
                try:
                    from app.services.monitoring_service import performance_monitor
                    tokens_used = response.usage.get('total_tokens', 0) if response.usage else 0
                    performance_monitor.record_llm_call(
                        provider=response.provider,
                        model=response.model,
                        tokens_used=tokens_used,
                        response_time=response_time,
                        success=is_success
                    )
                    log_llm_info(
                        "API",
                        "监控指标记录完成",
                        request_id,
                        tokens_used=tokens_used,
                        monitoring_success=True
                    )
                except Exception as e:
                    log_llm_warning(
                        "API",
                        "记录LLM监控指标失败",
                        request_id,
                        error=str(e),
                        monitoring_success=False
                    )

                # 构建最终响应
                final_response = {
                    'success': True,
                    'data': {
                        'response': response.content,
                        'model': response.model,
                        'usage': response.usage,
                        'response_time': response.response_time,
                        'timestamp': end_time.isoformat(),
                        'provider': response.provider
                    }
                }

                log_llm_info(
                    "API",
                    "请求处理完成，返回响应",
                    request_id,
                    total_time=f"{response_time:.2f}s",
                    success=is_success,
                    response_size=len(str(final_response))
                )

                return final_response

            except LLMError as e:
                log_llm_error(
                    "API",
                    "简化LLM服务错误",
                    request_id,
                    error=str(e),
                    provider=e.provider,
                    error_type="LLMError"
                )
                return {
                    'success': False,
                    'error_code': 'LLM_ERROR',
                    'message': f'LLM服务错误: {str(e)}',
                    'provider': e.provider
                }, 500

            except Exception as e:
                log_llm_error(
                    "API",
                    "简化LLM对话处理异常",
                    request_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    stack_trace=traceback.format_exc()
                )
                return {
                    'success': False,
                    'error_code': 'INTERNAL_ERROR',
                    'message': f'内部服务器错误: {str(e)}'
                }, 500

    def get(self):
        """获取简化LLM服务信息"""
        try:
            # 获取可用的提供商（简化版本只返回anthropic）
            available_providers = llm_manager.list_available_providers()

            # 获取提供商信息
            provider_info = llm_manager.get_provider_info()

            return {
                'success': True,
                'data': {
                    'available_providers': available_providers,
                    'default_provider': 'anthropic',
                    'provider_info': provider_info,
                    'type': 'simplified_anthropic',
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"获取简化LLM服务信息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': f'获取服务信息失败: {str(e)}'
            }, 500


class LLMHealthResource(Resource):
    """简化的LLM健康检查资源"""

    def get(self):
        """检查简化LLM服务健康状态"""
        try:
            # 使用简化管理器的健康检查
            is_healthy = llm_manager.health_check()
            provider_info = llm_manager.get_provider_info()

            return {
                'success': True,
                'data': {
                    'overall_healthy': is_healthy,
                    'default_provider': 'anthropic',
                    'default_healthy': is_healthy,
                    'provider_health': {
                        'anthropic': {
                            'healthy': is_healthy,
                            'service_info': provider_info,
                            'tested_at': datetime.now().isoformat()
                        }
                    },
                    'type': 'simplified_anthropic',
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"简化LLM健康检查失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'HEALTH_CHECK_ERROR',
                'message': f'健康检查失败: {str(e)}'
            }, 500


# 注册API路由
def register_llm_routes(api):
    """注册简化LLM相关路由"""
    api.add_resource(LLMChatResource, '/api/llm/chat')
    api.add_resource(LLMHealthResource, '/api/llm/health')