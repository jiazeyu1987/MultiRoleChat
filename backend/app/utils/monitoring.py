import time
import functools
import logging
from datetime import datetime
from typing import Callable, Any, Optional
from flask import request, g
from app.services.monitoring_service import performance_monitor
from app.services.health_service import health_check_service
import asyncio

logger = logging.getLogger(__name__)


def monitor_request(func: Callable) -> Callable:
    """请求监控装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        endpoint = request.endpoint or 'unknown'
        method = request.method
        user_id = getattr(g, 'user_id', None)
        session_id = getattr(g, 'session_id', None)

        try:
            # 执行原始函数
            response = func(*args, **kwargs)
            status_code = getattr(response, 'status_code', 200)

            # 计算响应时间
            response_time = time.time() - start_time

            # 记录请求指标
            performance_monitor.record_request(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time=response_time,
                user_id=user_id,
                session_id=session_id
            )

            return response

        except Exception as e:
            # 记录异常请求
            response_time = time.time() - start_time

            performance_monitor.record_request(
                endpoint=endpoint,
                method=method,
                status_code=500,
                response_time=response_time,
                user_id=user_id,
                session_id=session_id
            )

            logger.error(f"请求监控 - 异常: {endpoint} {method} - {str(e)}")
            raise

    return wrapper


def monitor_llm_call(provider: str = None, model: str = None):
    """LLM调用监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            tokens_used = 0
            error_message = None

            # 获取提供商和模型信息
            actual_provider = provider or kwargs.get('provider', 'unknown')
            actual_model = model or kwargs.get('model', 'unknown')

            try:
                result = await func(*args, **kwargs)
                success = True

                # 尝试从结果中获取token使用量
                if hasattr(result, 'usage') and result.usage:
                    tokens_used = result.usage.get('total_tokens', 0)
                elif isinstance(result, dict) and 'usage' in result:
                    tokens_used = result['usage'].get('total_tokens', 0)

                return result

            except Exception as e:
                error_message = str(e)
                logger.error(f"LLM调用监控失败: {actual_provider} {actual_model} - {str(e)}")
                raise

            finally:
                response_time = time.time() - start_time

                # 记录LLM调用指标
                performance_monitor.record_llm_call(
                    provider=actual_provider,
                    model=actual_model,
                    tokens_used=tokens_used,
                    response_time=response_time,
                    success=success,
                    error_message=error_message
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            tokens_used = 0
            error_message = None

            # 获取提供商和模型信息
            actual_provider = provider or kwargs.get('provider', 'unknown')
            actual_model = model or kwargs.get('model', 'unknown')

            try:
                # 如果是同步函数，直接调用
                result = func(*args, **kwargs)
                success = True

                # 尝试从结果中获取token使用量
                if hasattr(result, 'usage') and result.usage:
                    tokens_used = result.usage.get('total_tokens', 0)
                elif isinstance(result, dict) and 'usage' in result:
                    tokens_used = result['usage'].get('total_tokens', 0)

                return result

            except Exception as e:
                error_message = str(e)
                logger.error(f"LLM调用监控失败: {actual_provider} {actual_model} - {str(e)}")
                raise

            finally:
                response_time = time.time() - start_time

                # 记录LLM调用指标
                performance_monitor.record_llm_call(
                    provider=actual_provider,
                    model=actual_model,
                    tokens_used=tokens_used,
                    response_time=response_time,
                    success=success,
                    error_message=error_message
                )

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def monitor_performance(func: Callable) -> Callable:
    """性能监控装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 记录性能数据
            if execution_time > 1.0:  # 只记录执行时间超过1秒的函数
                logger.info(f"性能监控 - {function_name} 执行时间: {execution_time:.2f}s")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"性能监控 - {function_name} 执行失败，耗时: {execution_time:.2f}s，错误: {str(e)}")
            raise

    return wrapper


class MonitoringMiddleware:
    """监控中间件类"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化Flask应用监控"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_appcontext(self._teardown_request)

        # 启动性能监控
        if not app.config.get('TESTING', False):
            performance_monitor.start_monitoring()

        logger.info("监控中间件已初始化")

    def _before_request(self):
        """请求开始前的处理"""
        g.start_time = time.time()
        g.request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(request)}"

        # 尝试从请求中提取用户和会话信息
        try:
            # 从请求头或参数中获取用户ID
            user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
            if user_id:
                g.user_id = user_id

            # 从请求头或参数中获取会话ID
            session_id = request.headers.get('X-Session-ID') or request.args.get('session_id')
            if session_id:
                g.session_id = session_id

        except Exception as e:
            logger.debug(f"提取请求上下文信息失败: {str(e)}")

    def _after_request(self, response):
        """请求结束后的处理"""
        try:
            # 计算请求处理时间
            if hasattr(g, 'start_time'):
                response_time = time.time() - g.start_time

                # 添加响应时间到响应头
                response.headers['X-Response-Time'] = f"{response_time:.3f}s"

                # 记录慢请求
                if response_time > 2.0:
                    logger.warning(
                        f"慢请求警告: {request.method} {request.path} "
                        f"耗时 {response_time:.2f}s，状态码: {response.status_code}"
                    )

            # 添加请求ID到响应头
            if hasattr(g, 'request_id'):
                response.headers['X-Request-ID'] = g.request_id

        except Exception as e:
            logger.error(f"请求后处理失败: {str(e)}")

        return response

    def _teardown_request(self, exception):
        """请求清理处理"""
        try:
            # 记录异常信息
            if exception is not None:
                endpoint = request.endpoint or 'unknown'
                method = request.method

                logger.error(
                    f"请求异常: {method} {endpoint} - "
                    f"异常类型: {type(exception).__name__} - "
                    f"异常信息: {str(exception)}"
                )

                # 如果有用户信息，也记录下来
                if hasattr(g, 'user_id'):
                    logger.error(f"用户ID: {g.user_id}")

                if hasattr(g, 'session_id'):
                    logger.error(f"会话ID: {g.session_id}")

        except Exception as e:
            logger.error(f"请求清理处理失败: {str(e)}")


def create_monitoring_alerts():
    """创建监控告警配置"""
    def email_alert_callback(alert):
        """邮件告警回调（示例）"""
        try:
            # 这里可以集成邮件发送服务
            logger.warning(f"告警邮件通知: {alert['message']}")
            # send_email_alert(alert)
        except Exception as e:
            logger.error(f"发送告警邮件失败: {str(e)}")

    def webhook_alert_callback(alert):
        """Webhook告警回调（示例）"""
        try:
            # 这里可以调用webhook通知
            logger.warning(f"告警Webhook通知: {alert['message']}")
            # call_webhook_alert(alert)
        except Exception as e:
            logger.error(f"调用告警Webhook失败: {str(e)}")

    # 添加告警回调
    performance_monitor.add_alert_callback(email_alert_callback)
    performance_monitor.add_alert_callback(webhook_alert_callback)

    logger.info("监控告警配置已创建")


# 健康检查装饰器
def health_check(component: str = None):
    """健康检查装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from app.services.health_service import HealthCheckResult

            start_time = time.time()
            actual_component = component or func.__name__

            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time

                # 这里可以记录组件健康状态
                logger.debug(f"健康检查 - {actual_component}: 正常 ({response_time:.3f}s)")
                return result

            except Exception as e:
                response_time = time.time() - start_time

                # 记录健康检查失败
                logger.error(f"健康检查 - {actual_component}: 失败 - {str(e)} ({response_time:.3f}s)")

                # 返回健康检查结果
                return HealthCheckResult(
                    component=actual_component,
                    status='unhealthy',
                    message=f"健康检查失败: {str(e)}",
                    details={'error': str(e)},
                    response_time=response_time
                )

        return wrapper
    return decorator


# 系统工具函数
def get_system_info() -> dict:
    """获取系统信息"""
    try:
        import psutil
        import platform

        # 基本系统信息
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024 ** 3),
            'disk_total_gb': psutil.disk_usage('/').total / (1024 ** 3),
        }

        # 当前性能指标
        current_metrics = performance_monitor.get_current_metrics()
        if current_metrics:
            system_info['current_metrics'] = current_metrics

        return system_info

    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        return {'error': str(e)}


def log_application_start():
    """记录应用启动信息"""
    try:
        system_info = get_system_info()
        startup_time = datetime.now().isoformat()

        logger.info("=" * 50)
        logger.info("MultiRoleChat 后端服务启动")
        logger.info(f"启动时间: {startup_time}")
        logger.info(f"系统平台: {system_info.get('platform', 'Unknown')}")
        logger.info(f"Python版本: {system_info.get('python_version', 'Unknown')}")
        logger.info(f"CPU核心数: {system_info.get('cpu_count', 'Unknown')}")
        logger.info(f"总内存: {system_info.get('memory_total_gb', 0):.1f} GB")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"记录启动信息失败: {str(e)}")


# 初始化监控系统
def init_monitoring(app):
    """初始化监控系统"""
    try:
        # 添加监控中间件
        monitoring_middleware = MonitoringMiddleware(app)

        # 创建告警配置
        create_monitoring_alerts()

        # 记录应用启动
        log_application_start()

        logger.info("监控系统初始化完成")
        return monitoring_middleware

    except Exception as e:
        logger.error(f"监控系统初始化失败: {str(e)}")
        raise