#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM专用日志记录器

为LLM调用创建独立的高性能日志系统，不依赖Flask的日志配置
确保LLM日志始终写入文件，便于追踪和调试
"""

import os
import logging
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class LLMSpecialLogger:
    """LLM专用日志记录器"""

    __instance = None
    __lock = threading.Lock()

    def __new__(cls):
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = super().__new__(cls)
                    cls.__instance._initialized = False
        return cls.__instance

    def __init__(self):
        """初始化LLM日志记录器"""
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.logger = None
        self.log_file_path = None
        self._setup_logger()

    def _setup_logger(self):
        """设置LLM专用日志器"""
        # 创建logs目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 设置日志文件路径
        timestamp = datetime.now().strftime("%Y-%m-%d")
        self.log_file_path = log_dir / f"llm_requests_{timestamp}.log"

        # 创建专用logger
        self.logger = logging.getLogger('llm_special')
        self.logger.setLevel(logging.INFO)

        # 清除现有处理器
        self.logger.handlers.clear()

        # 创建文件处理器
        file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )

        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)

        # 记录初始化信息
        self.logger.info("=" * 80)
        self.logger.info("LLM专用日志系统初始化完成")
        self.logger.info(f"日志文件: {self.log_file_path}")
        self.logger.info("=" * 80)

    def log_request_start(self, request_id: str, user_id: str = None, session_id: str = None, **kwargs):
        """记录请求开始"""
        user_info = f" (用户: {user_id})" if user_id else ""
        session_info = f" (会话: {session_id})" if session_id else ""

        extra_info = []
        for key, value in kwargs.items():
            if key not in ['password', 'token', 'secret', 'key']:
                extra_info.append(f"{key}={value}")

        extra_str = f" | {' | '.join(extra_info)}" if extra_info else ""

        self.logger.info(f"[{request_id}] 请求开始{user_info}{session_info}{extra_str}")

    def log_request_end(self, request_id: str, success: bool = True, response_length: int = None,
                       response_time: float = None, error_msg: str = None, **kwargs):
        """记录请求结束"""
        status = "成功" if success else "失败"

        info_parts = [f"[{request_id}] 请求结束 - {status}"]

        if response_length is not None:
            info_parts.append(f"响应长度: {response_length}")

        if response_time is not None:
            info_parts.append(f"响应时间: {response_time:.3f}s")

        if not success and error_msg:
            info_parts.append(f"错误: {error_msg}")

        for key, value in kwargs.items():
            if key not in ['password', 'token', 'secret', 'key']:
                info_parts.append(f"{key}: {value}")

        self.logger.info(" | ".join(info_parts))

    def log_api_call(self, request_id: str, layer: str, action: str, **kwargs):
        """记录API调用"""
        detail_parts = [f"[{request_id}] [{layer.upper()}] {action}"]

        for key, value in kwargs.items():
            if key not in ['password', 'token', 'secret', 'key']:
                detail_parts.append(f"{key}={value}")

        self.logger.info(" | ".join(detail_parts))

    def log_content(self, request_id: str, content_type: str, content: str, max_preview: int = 200):
        """记录内容信息"""
        if not content:
            self.logger.info(f"[{request_id}] [{content_type}] 内容为空")
            return

        content_preview = content
        if len(content) > max_preview:
            content_preview = content[:max_preview] + f"...(共{len(content)}字符)"

        self.logger.info(f"[{request_id}] [{content_type}] {content_preview}")

    def log_error(self, request_id: str, error_type: str, error_msg: str, layer: str = None, **kwargs):
        """记录错误信息"""
        layer_info = f"[{layer}]" if layer else ""
        detail_parts = [f"[{request_id}] {layer_info}[{error_type.upper()}] {error_msg}"]

        for key, value in kwargs.items():
            detail_parts.append(f"{key}: {value}")

        self.logger.error(" | ".join(detail_parts))

    def log_warning(self, request_id: str, warning_msg: str, layer: str = None, **kwargs):
        """记录警告信息"""
        layer_info = f"[{layer}]" if layer else ""
        detail_parts = [f"[{request_id}] {layer_info}[WARNING] {warning_msg}"]

        for key, value in kwargs.items():
            detail_parts.append(f"{key}: {value}")

        self.logger.warning(" | ".join(detail_parts))

    def log_info(self, request_id: str, message: str, layer: str = None, **kwargs):
        """记录信息"""
        layer_info = f"[{layer}]" if layer else ""
        detail_parts = [f"[{request_id}] {layer_info}[INFO] {message}"]

        for key, value in kwargs.items():
            if key not in ['password', 'token', 'secret', 'key']:
                detail_parts.append(f"{key}: {value}")

        self.logger.info(" | ".join(detail_parts))

    def get_log_file_path(self) -> str:
        """获取当前日志文件路径"""
        return str(self.log_file_path) if self.log_file_path else None

    def get_log_size(self) -> int:
        """获取日志文件大小（字节）"""
        if self.log_file_path and self.log_file_path.exists():
            return self.log_file_path.stat().st_size
        return 0


# 全局实例
llm_special_logger = LLMSpecialLogger()


def get_llm_logger() -> LLMSpecialLogger:
    """获取LLM专用日志记录器实例"""
    return llm_special_logger


# 便捷函数
def log_llm_request_start(request_id: str, user_id: str = None, session_id: str = None, **kwargs):
    """记录LLM请求开始"""
    llm_special_logger.log_request_start(request_id, user_id, session_id, **kwargs)


def log_llm_request_end(request_id: str, success: bool = True, response_length: int = None,
                        response_time: float = None, error_msg: str = None, **kwargs):
    """记录LLM请求结束"""
    llm_special_logger.log_request_end(request_id, success, response_length, response_time, error_msg, **kwargs)


def log_llm_api_call(request_id: str, layer: str, action: str, **kwargs):
    """记录LLM API调用"""
    llm_special_logger.log_api_call(request_id, layer, action, **kwargs)


def log_llm_content(request_id: str, content_type: str, content: str, max_preview: int = 200):
    """记录LLM内容"""
    llm_special_logger.log_content(request_id, content_type, content, max_preview)


def log_llm_error(request_id: str, error_type: str, error_msg: str, layer: str = None, **kwargs):
    """记录LLM错误"""
    llm_special_logger.log_error(request_id, error_type, error_msg, layer, **kwargs)


def log_llm_warning(request_id: str, warning_msg: str, layer: str = None, **kwargs):
    """记录LLM警告"""
    llm_special_logger.log_warning(request_id, warning_msg, layer, **kwargs)


def log_llm_info(request_id: str, message: str, layer: str = None, **kwargs):
    """记录LLM信息"""
    llm_special_logger.log_info(request_id, message, layer, **kwargs)