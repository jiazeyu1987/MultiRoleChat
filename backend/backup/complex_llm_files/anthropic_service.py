"""
Anthropic LLM服务
基于官方Anthropic Python库实现，无需CLI工具
"""
import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

import anthropic

from .base import BaseLLMService, LLMMessage, LLMResponse, LLMConfig, LLMError

logger = logging.getLogger(__name__)


class AnthropicLLMService(BaseLLMService):
    """Anthropic LLM服务实现"""

    def __init__(self, config: Optional[Union[Dict, LLMConfig]] = None):
        """
        初始化Anthropic LLM服务

        Args:
            config: 配置字典或LLMConfig对象
        """
        # 处理配置
        if isinstance(config, dict):
            llm_config = LLMConfig(
                model=config.get('model', 'claude-3-5-sonnet-20241022'),
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.7),
                timeout=config.get('timeout', 60),
                max_retries=config.get('max_retries', 3),
                retry_delay=config.get('retry_delay', 1.0)
            )
            api_key = config.get('api_key')
        else:
            llm_config = config or LLMConfig(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.7,
                timeout=60,
                max_retries=3,
                retry_delay=1.0
            )
            api_key = None

        super().__init__(llm_config)

        # 初始化Anthropic客户端
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"初始化Anthropic客户端失败: {e}")
            raise LLMError(f"初始化Anthropic客户端失败: {e}", "anthropic")

    async def generate_response(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        生成LLM响应

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMResponse: LLM响应对象
        """
        try:
            # 转换消息格式
            anthropic_messages = self._convert_messages(messages)

            # 提取系统消息
            system_message = None
            user_messages = []

            for msg in anthropic_messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg)

            # 调用Anthropic API
            start_time = time.time()

            response = await self._call_anthropic_api(
                messages=user_messages,
                system=system_message,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature)
            )

            response_time = time.time() - start_time

            # 创建LLMResponse对象
            return LLMResponse(
                content=response.content[0].text,
                model=self.config.model,
                usage={
                    'prompt_tokens': response.usage.input_tokens,
                    'completion_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.input_tokens + response.usage.output_tokens
                },
                finish_reason=response.stop_reason,
                response_time=response_time
            )

        except anthropic.APIError as e:
            logger.error(f"Anthropic API错误: {e}")
            raise LLMError(f"Anthropic API错误: {e}", "anthropic", "API_ERROR")
        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic API速率限制: {e}")
            from .base import LLMRateLimitError
            raise LLMRateLimitError(f"Anthropic API速率限制: {e}", "anthropic")
        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API超时: {e}")
            from .base import LLMTimeoutError
            raise LLMTimeoutError(f"Anthropic API超时: {e}", "anthropic")
        except Exception as e:
            logger.error(f"Anthropic服务异常: {e}")
            raise LLMError(f"Anthropic服务异常: {e}", "anthropic")

    async def _call_anthropic_api(self, messages: List[Dict], system: str = None, **kwargs) -> Any:
        """
        异步调用Anthropic API

        Args:
            messages: 消息列表
            system: 系统提示词
            **kwargs: 其他参数

        Returns:
            API响应对象
        """
        loop = asyncio.get_event_loop()

        def sync_call():
            return self.client.messages.create(
                model=self.config.model,
                messages=messages,
                system=system,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature)
            )

        return await loop.run_in_executor(None, sync_call)

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        转换消息格式为Anthropic API格式

        Args:
            messages: LLMMessage列表

        Returns:
            Anthropic API格式的消息列表
        """
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                anthropic_messages.append({
                    'role': 'system',
                    'content': msg.content
                })
            elif msg.role == "user":
                anthropic_messages.append({
                    'role': 'user',
                    'content': msg.content
                })
            elif msg.role == "assistant":
                anthropic_messages.append({
                    'role': 'assistant',
                    'content': msg.content
                })

        return anthropic_messages

    def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        try:
            # 检查API密钥是否可用
            if not self.client.api_key:
                logger.error("Anthropic API密钥未配置")
                return False

            # 可以添加更多验证，比如测试连接
            return True
        except Exception as e:
            logger.error(f"Anthropic配置验证失败: {e}")
            return False

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 服务是否健康
        """
        try:
            # 执行简单的测试
            test_messages = [
                LLMMessage(role="user", content="Hello")
            ]

            # 使用同步方式检查
            response = self.client.messages.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                temperature=0.1
            )

            return bool(response and response.content)
        except Exception as e:
            logger.error(f"Anthropic健康检查失败: {e}")
            return False

    def supports_streaming(self) -> bool:
        """
        是否支持流式响应

        Returns:
            True，Anthropic支持流式响应
        """
        return True

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 输入文本

        Returns:
            估算的token数量（Anthropic大约4个字符等于1个token）
        """
        return len(text) // 4

    def get_max_tokens(self) -> int:
        """
        获取支持的最大token数量

        Returns:
            最大token数量（Claude 3.5 Sonnet支持200K上下文）
        """
        return 200000

    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息

        Returns:
            服务信息字典
        """
        return {
            'service_name': 'Anthropic',
            'provider': 'anthropic',
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'supports_streaming': True,
            'created_at': datetime.now().isoformat()
        }

    def cleanup(self):
        """
        清理资源
        """
        logger.info("Anthropic LLM服务清理完成")

    async def generate_response_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ):
        """
        生成流式响应

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Yields:
            str: 流式响应片段
        """
        try:
            # 转换消息格式
            anthropic_messages = self._convert_messages(messages)

            # 提取系统消息
            system_message = None
            user_messages = []

            for msg in anthropic_messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg)

            # 创建流式响应
            loop = asyncio.get_event_loop()

            def sync_stream():
                return self.client.messages.create(
                    model=self.config.model,
                    messages=user_messages,
                    system=system_message,
                    max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                    temperature=kwargs.get('temperature', self.config.temperature),
                    stream=True
                )

            stream = await loop.run_in_executor(None, sync_stream)

            for text in stream:
                if text.type == 'content_block_delta':
                    yield text.delta.text

        except Exception as e:
            logger.error(f"Anthropic流式响应失败: {e}")
            raise LLMError(f"Anthropic流式响应失败: {e}", "anthropic")