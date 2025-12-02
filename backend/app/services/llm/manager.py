"""
简化的LLM服务管理器

基于simple_llm.py的重写版本，专注于Anthropic集成
大幅简化架构复杂度，保持API兼容性
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..simple_llm import SimpleLLMService, LLMResponse, get_llm_service
from ...utils.request_tracker import RequestTracker, log_llm_info, log_llm_error, log_llm_warning

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """LLM消息数据结构（兼容性）"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


class SimpleLLMManager:
    """
    简化的LLM管理器

    专注于Anthropic集成，使用simple_llm服务
    保持与现有系统的接口兼容性
    """

    def __init__(self):
        """初始化简化LLM管理器"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.default_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        self.max_tokens = int(os.getenv('ANTHROPIC_MAX_TOKENS', '4096'))

        # 获取简化LLM服务实例
        self.simple_llm_service = get_llm_service()

        logger.info(f"简化LLM管理器已初始化，模型: {self.default_model}")

    async def generate_response(
        self,
        provider: str = None,
        messages: List[LLMMessage] = None,
        request_id: str = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成LLM响应（保持接口兼容性）

        Args:
            provider: 提供商名称（简化版本忽略此参数）
            messages: 消息列表
            request_id: 请求ID用于日志追踪
            **kwargs: 其他参数

        Returns:
            LLMResponse: LLM响应
        """
        # 如果没有传入request_id，尝试从当前上下文获取
        if request_id is None:
            context = RequestTracker.get_context()
            request_id = context.request_id if context else "UNKNOWN"

        start_time = time.time()

        log_llm_info(
            "MANAGER",
            "开始生成LLM响应",
            request_id,
            provider=provider,
            message_count=len(messages) if messages else 0,
            model=kwargs.get('model', self.default_model),
            max_tokens=kwargs.get('max_tokens', self.max_tokens)
        )

        try:
            # 转换消息格式
            message_dicts = []
            if messages:
                log_llm_info(
                    "MANAGER",
                    "开始消息格式转换",
                    request_id,
                    input_type="LLMMessage对象列表",
                    count=len(messages)
                )

                for i, msg in enumerate(messages):
                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                        message_dict = {
                            'role': msg.role,
                            'content': msg.content
                        }
                        message_dicts.append(message_dict)

                        log_llm_info(
                            "MANAGER",
                            f"消息转换[{i}] - {msg.role}",
                            request_id,
                            content_length=len(msg.content),
                            content_preview=msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                        )
                    else:
                        # 兼容字典格式
                        if isinstance(msg, dict):
                            role = msg.get('role', 'user')
                            content = msg.get('content', str(msg))
                            message_dict = {
                                'role': role,
                                'content': content
                            }
                            message_dicts.append(message_dict)

                            log_llm_info(
                                "MANAGER",
                                f"消息转换[{i}] - {role} (字典格式)",
                                request_id,
                                content_length=len(content),
                                content_preview=content[:100] + "..." if len(content) > 100 else content
                            )

                log_llm_info(
                    "MANAGER",
                    "消息格式转换完成",
                    request_id,
                    output_type="字典列表",
                    output_count=len(message_dicts),
                    conversion_success=True
                )
            else:
                log_llm_warning(
                    "MANAGER",
                    "消息列表为空，跳过格式转换",
                    request_id
                )

            # 获取参数
            model = kwargs.get('model', self.default_model)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)

            log_llm_info(
                "MANAGER",
                "参数提取完成，准备调用简化服务",
                request_id,
                model=model,
                max_tokens=max_tokens,
                additional_params={k: v for k, v in kwargs.items() if k not in ['model', 'max_tokens']}
            )

            # 构建完整的提示词用于日志记录
            full_prompt = ""
            for msg_dict in message_dicts:
                full_prompt += f"{msg_dict['role']}: {msg_dict['content']}\n"

            log_llm_info(
                "MANAGER",
                "完整提示词构建完成",
                request_id,
                content=full_prompt.strip(),
                total_prompt_length=len(full_prompt),
                message_count=len(message_dicts)
            )

            # 调用简化服务
            log_llm_info(
                "MANAGER",
                "开始调用简化LLM服务",
                request_id,
                service_type="SimpleLLMService",
                api_call_start_time=start_time
            )

            response = self.simple_llm_service.generate_response(
                messages=message_dicts,
                model=model,
                max_tokens=max_tokens,
                request_id=request_id,  # 传递request_id
                **kwargs
            )

            end_time = time.time()
            total_time = end_time - start_time

            # 检查响应质量
            is_success = not response.content.startswith('调用失败')
            if is_success:
                log_llm_info(
                    "MANAGER",
                    "LLM响应生成成功",
                    request_id,
                    response_length=len(response.content),
                    response_time=f"{total_time:.3f}s",
                    model=response.model,
                    provider=response.provider,
                    usage=response.usage,
                    service_response_time=f"{response.response_time:.3f}s"
                )

                # 记录完整的返回内容
                log_llm_info(
                    "MANAGER",
                    "LLM返回内容详情",
                    request_id,
                    content=response.content,
                    content_length=len(response.content),
                    is_success=is_success
                )
            else:
                log_llm_error(
                    "MANAGER",
                    "LLM响应生成失败",
                    request_id,
                    error_content=response.content,
                    response_time=f"{total_time:.3f}s",
                    model=response.model,
                    provider=response.provider
                )

            return response

        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time

            log_llm_error(
                "MANAGER",
                "LLM响应生成异常",
                request_id,
                error=str(e),
                error_type=type(e).__name__,
                response_time=f"{total_time:.3f}s",
                stack_trace=f"异常位置: {__name__}.generate_response"
            )

            # 返回错误响应
            return LLMResponse(
                content=f"LLM调用失败: {str(e)}",
                model=self.default_model,
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                response_time=total_time,
                provider="anthropic"
            )

    def list_available_providers(self) -> List[str]:
        """
        列出可用的提供商

        Returns:
            List[str]: 提供商列表（简化版本只返回anthropic）
        """
        return ["anthropic"]

    def get_provider_info(self, provider: str = None) -> Dict[str, Any]:
        """
        获取提供商信息

        Args:
            provider: 提供商名称

        Returns:
            Dict[str, Any]: 提供商信息
        """
        return {
            'provider': 'anthropic',
            'model': self.default_model,
            'status': 'available',
            'type': 'simplified_anthropic'
        }

    def set_default_provider(self, provider: str):
        """
        设置默认提供商（简化版本只支持anthropic）

        Args:
            provider: 提供商名称
        """
        if provider == 'anthropic':
            logger.info("已设置默认LLM提供商: anthropic")
        else:
            logger.warning(f"简化版本只支持anthropic提供商，忽略: {provider}")

    async def test_connection(self, provider: str = None) -> bool:
        """
        测试LLM服务连接

        Args:
            provider: 提供商名称

        Returns:
            bool: 连接是否成功
        """
        try:
            return self.simple_llm_service.quick_test()
        except Exception as e:
            logger.error(f"LLM连接测试失败: {str(e)}")
            return False

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 服务是否健康
        """
        return self.simple_llm_service.quick_test()

    # 便捷方法，兼容原有接口
    def get_service(self, provider: str = None):
        """
        获取LLM服务实例

        Args:
            provider: 提供商名称（简化版本忽略）

        Returns:
            SimpleLLMService: LLM服务实例
        """
        return self.simple_llm_service

    def register_service(self, provider: str, service):
        """
        注册LLM服务（简化版本为空实现）

        Args:
            provider: 提供商名称
            service: LLM服务实例
        """
        logger.info(f"简化版本忽略服务注册: {provider}")

    def build_system_prompt(self, role_info: Dict[str, Any]) -> str:
        """
        构建系统提示词

        Args:
            role_info: 角色信息

        Returns:
            str: 系统提示词
        """
        return f"""你是{role_info.get('name', 'AI助手')}。

角色描述：{role_info.get('description', '无描述')}
发言风格：{role_info.get('style', '自然友好')}
关注点：{', '.join(role_info.get('focus_points', []))}

请严格按照你的角色设定进行回复，保持角色的一致性和真实感。"""

    def build_context_messages(
        self,
        role_info: Dict[str, Any],
        task_info: Dict[str, Any],
        history_messages: List[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """
        构建上下文消息列表

        Args:
            role_info: 角色信息
            task_info: 任务信息
            history_messages: 历史消息

        Returns:
            List[LLMMessage]: 消息列表
        """
        messages = []

        # 系统消息
        system_prompt = self.build_system_prompt(role_info)
        messages.append(LLMMessage(role="system", content=system_prompt))

        # 任务描述
        task_prompt = f"""当前任务：
任务类型：{task_info.get('task_type', '无')}
任务描述：{task_info.get('description', '无')}
对话主题：{task_info.get('session_topic', '无')}
当前轮次：{task_info.get('current_round', 1)}
已执行步数：{task_info.get('step_count', 0)}

请根据你的角色设定和当前任务，发表你的观点。"""

        messages.append(LLMMessage(role="user", content=task_prompt))

        # 历史对话
        if history_messages:
            for msg in history_messages[-5:]:  # 只取最近5条消息避免token超限
                speaker = msg.get('speaker_role', '未知角色')
                content = msg.get('content', '')

                if speaker == role_info.get('name'):
                    messages.append(LLMMessage(role="assistant", content=content))
                else:
                    messages.append(LLMMessage(
                        role="user",
                        content=f"{speaker}: {content}"
                    ))

        return messages


# 全局简化LLM管理器实例
llm_manager = SimpleLLMManager()


def get_llm_manager() -> SimpleLLMManager:
    """
    获取LLM管理器实例

    Returns:
        SimpleLLMManager: LLM管理器实例
    """
    return llm_manager