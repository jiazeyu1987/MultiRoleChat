#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM请求追踪工具

用于生成唯一请求ID、管理请求上下文和格式化LLM调用日志
帮助追踪完整的LLM调用链路，便于问题排查和性能分析
"""

import uuid
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LLMRequestContext:
    """LLM请求上下文信息"""
    request_id: str
    start_time: float
    layer: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RequestTracker:
    """请求追踪器"""

    _current_context: Optional[LLMRequestContext] = None

    @classmethod
    def generate_request_id(cls) -> str:
        """生成唯一的请求ID"""
        # 使用时间戳+UUID确保唯一性和可读性
        timestamp = int(time.time() * 1000)
        unique_id = str(uuid.uuid4())[:8]
        return f"LLM-{timestamp}-{unique_id}"

    @classmethod
    def set_context(cls, context: LLMRequestContext):
        """设置当前请求上下文"""
        cls._current_context = context

    @classmethod
    def get_context(cls) -> Optional[LLMRequestContext]:
        """获取当前请求上下文"""
        return cls._current_context

    @classmethod
    def clear_context(cls):
        """清除当前请求上下文"""
        cls._current_context = None

    @classmethod
    @contextmanager
    def track_request(
        cls,
        request_id: Optional[str] = None,
        layer: str = "UNKNOWN",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Generator[LLMRequestContext, None, None]:
        """请求追踪上下文管理器"""
        if request_id is None:
            request_id = cls.generate_request_id()

        context = LLMRequestContext(
            request_id=request_id,
            start_time=time.time(),
            layer=layer,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )

        # 保存之前的上下文
        previous_context = cls._current_context
        cls.set_context(context)

        try:
            yield context
        finally:
            # 恢复之前的上下文
            cls.set_context(previous_context)

    @classmethod
    def format_log(
        cls,
        layer: str,
        message: str,
        request_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """格式化LLM日志消息"""
        # 使用传入的request_id或当前上下文的request_id
        if request_id is None:
            context = cls.get_context()
            request_id = context.request_id if context else "UNKNOWN"

        # 基础日志格式
        log_message = f"[LLM-REQ-ID: {request_id}] {layer.upper()}_LAYER - {message}"

        # 添加额外数据
        if extra_data:
            extra_parts = []
            for key, value in extra_data.items():
                if key == "content" and isinstance(value, str):
                    # 内容字段显示长度和开头部分
                    content_preview = value[:100] + "..." if len(value) > 100 else value
                    extra_parts.append(f"{key}长度={len(value)}, 预览='{content_preview}'")
                else:
                    extra_parts.append(f"{key}={value}")

            if extra_parts:
                log_message += f" | {' | '.join(extra_parts)}"

        return log_message

    @classmethod
    def log_info(
        cls,
        layer: str,
        message: str,
        request_id: Optional[str] = None,
        **kwargs
    ):
        """记录信息级别日志"""
        log_message = cls.format_log(layer, message, request_id, kwargs)
        logger.info(log_message)

    @classmethod
    def log_error(
        cls,
        layer: str,
        message: str,
        request_id: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs
    ):
        """记录错误级别日志"""
        extra_data = kwargs.copy()
        if error:
            extra_data["error"] = str(error)
            extra_data["error_type"] = type(error).__name__

        log_message = cls.format_log(layer, message, request_id, extra_data)
        logger.error(log_message)

    @classmethod
    def log_warning(
        cls,
        layer: str,
        message: str,
        request_id: Optional[str] = None,
        **kwargs
    ):
        """记录警告级别日志"""
        log_message = cls.format_log(layer, message, request_id, kwargs)
        logger.warning(log_message)

    @classmethod
    def log_debug(
        cls,
        layer: str,
        message: str,
        request_id: Optional[str] = None,
        **kwargs
    ):
        """记录调试级别日志"""
        log_message = cls.format_log(layer, message, request_id, kwargs)
        logger.debug(log_message)

    @classmethod
    def calculate_duration(cls, start_time: float) -> float:
        """计算持续时间（秒）"""
        return time.time() - start_time

    @classmethod
    def format_duration(cls, duration: float) -> str:
        """格式化持续时间为可读字符串"""
        if duration < 1:
            return f"{duration * 1000:.0f}ms"
        else:
            return f"{duration:.2f}s"


# 便捷函数
def generate_request_id() -> str:
    """生成唯一的请求ID（便捷函数）"""
    return RequestTracker.generate_request_id()


def format_llm_log(
    layer: str,
    message: str,
    request_id: Optional[str] = None,
    **kwargs
) -> str:
    """格式化LLM日志（便捷函数）"""
    return RequestTracker.format_log(layer, message, request_id, kwargs)


def log_llm_info(
    layer: str,
    message: str,
    request_id: Optional[str] = None,
    **kwargs
):
    """记录LLM信息日志（便捷函数）"""
    RequestTracker.log_info(layer, message, request_id, **kwargs)


def log_llm_error(
    layer: str,
    message: str,
    request_id: Optional[str] = None,
    error: Optional[Exception] = None,
    **kwargs
):
    """记录LLM错误日志（便捷函数）"""
    RequestTracker.log_error(layer, message, request_id, error, **kwargs)


def log_llm_warning(
    layer: str,
    message: str,
    request_id: Optional[str] = None,
    **kwargs
):
    """记录LLM警告日志（便捷函数）"""
    RequestTracker.log_warning(layer, message, request_id, **kwargs)


# 上下文管理器的便捷装饰器
def with_llm_tracking(
    layer: str = "UNKNOWN",
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """LLM追踪装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 从kwargs中提取可能的请求ID
            req_id = request_id or kwargs.get('request_id')
            sess_id = session_id or kwargs.get('session_id')

            with RequestTracker.track_request(
                request_id=req_id,
                layer=layer,
                user_id=user_id,
                session_id=sess_id,
                metadata=metadata
            ) as context:
                # 将context添加到kwargs中，以便被装饰的函数使用
                kwargs['_llm_context'] = context
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 示例用法
if __name__ == "__main__":
    # 测试代码
    test_request_id = generate_request_id()
    print(f"Generated request ID: {test_request_id}")

    # 测试日志格式化
    log_message = format_llm_log(
        "API",
        "处理LLM请求",
        test_request_id,
        message_length=100,
        model="claude-3-sonnet"
    )
    print(f"Formatted log: {log_message}")

    # 测试上下文管理器
    with RequestTracker.track_request(
        layer="TEST",
        user_id="user123"
    ) as context:
        log_llm_info("TEST", "开始处理请求")
        time.sleep(0.1)
        duration = RequestTracker.calculate_duration(context.start_time)
        log_llm_info("TEST", "处理完成", duration=RequestTracker.format_duration(duration))