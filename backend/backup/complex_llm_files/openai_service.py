import openai
import asyncio
from typing import List, Dict, Any, Optional
import logging
from .base import (
    BaseLLMService, LLMMessage, LLMResponse, LLMConfig,
    LLMError, LLMRateLimitError, LLMTimeoutError, LLMQuotaExceededError
)

logger = logging.getLogger(__name__)


class OpenAILLMService(BaseLLMService):
    """OpenAI GPT模型服务"""

    def __init__(self, config: LLMConfig, api_key: str = None, base_url: str = None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = base_url
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            client_config = {
                'api_key': self.api_key,
                'timeout': self.config.timeout
            }

            if self.base_url:
                client_config['base_url'] = self.base_url

            self.client = openai.OpenAI(**client_config)

        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {str(e)}")
            raise LLMError(f"OpenAI客户端初始化失败: {str(e)}", "openai")

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            logger.error("OpenAI API密钥未配置")
            return False

        if not self.config.model:
            logger.error("OpenAI模型未配置")
            return False

        # 验证模型名称是否支持
        supported_models = [
            'gpt-3.5-turbo', 'gpt-3.5-turbo-16k',
            'gpt-4', 'gpt-4-32k', 'gpt-4-turbo-preview',
            'gpt-4o', 'gpt-4o-mini'
        ]

        if self.config.model not in supported_models:
            logger.warning(f"模型 {self.config.model} 可能不在支持列表中")

        return True

    async def generate_response(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        生成OpenAI响应

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMResponse: OpenAI响应对象
        """
        if not self.validate_config():
            raise LLMError("OpenAI配置无效", "openai")

        try:
            # 转换消息格式
            openai_messages = []
            for msg in messages:
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content
                }
                if msg.name:
                    openai_msg["name"] = msg.name
                openai_messages.append(openai_msg)

            # 调用OpenAI API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.config.model,
                    messages=openai_messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    frequency_penalty=self.config.frequency_penalty,
                    presence_penalty=self.config.presence_penalty,
                    **kwargs
                )
            )

            # 解析响应
            choice = response.choices[0]
            content = choice.message.content or ""

            # 构建使用信息
            usage = {}
            if response.usage:
                usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                response_time=0.0  # 将在调用方设置
            )

        except openai.RateLimitError as e:
            logger.error(f"OpenAI API速率限制: {str(e)}")
            raise LLMRateLimitError(f"OpenAI API速率限制: {str(e)}", "openai", "rate_limit")

        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API超时: {str(e)}")
            raise LLMTimeoutError(f"OpenAI API超时: {str(e)}", "openai", "timeout")

        except openai.APIConnectionError as e:
            logger.error(f"OpenAI API连接错误: {str(e)}")
            raise LLMError(f"OpenAI API连接错误: {str(e)}", "openai", "connection_error")

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API认证错误: {str(e)}")
            raise LLMError(f"OpenAI API认证错误: {str(e)}", "openai", "auth_error")

        except openai.PermissionError as e:
            logger.error(f"OpenAI API权限错误: {str(e)}")
            raise LLMQuotaExceededError(f"OpenAI API权限错误: {str(e)}", "openai", "permission_error")

        except openai.BadRequestError as e:
            logger.error(f"OpenAI API请求错误: {str(e)}")
            raise LLMError(f"OpenAI API请求错误: {str(e)}", "openai", "bad_request")

        except Exception as e:
            logger.error(f"OpenAI API未知错误: {str(e)}")
            raise LLMError(f"OpenAI API未知错误: {str(e)}", "openai", "unknown_error")

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        model_info = {
            'provider': 'OpenAI',
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'supports_streaming': True,
            'supports_function_calling': True,
            'context_length': self._get_context_length(),
        }
        return model_info

    def _get_context_length(self) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            'gpt-3.5-turbo': 4096,
            'gpt-3.5-turbo-16k': 16384,
            'gpt-4': 8192,
            'gpt-4-32k': 32768,
            'gpt-4-turbo-preview': 128000,
            'gpt-4o': 128000,
            'gpt-4o-mini': 128000,
        }
        return context_lengths.get(self.config.model, 4096)

    async def generate_streaming_response(
        self,
        messages: List[LLMMessage],
        **kwargs
    ):
        """
        生成流式响应（用于实时聊天）

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Yields:
            str: 流式响应内容块
        """
        if not self.validate_config():
            raise LLMError("OpenAI配置无效", "openai")

        try:
            # 转换消息格式
            openai_messages = []
            for msg in messages:
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content
                }
                if msg.name:
                    openai_msg["name"] = msg.name
                openai_messages.append(openai_msg)

            # 调用流式API
            stream = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.config.model,
                    messages=openai_messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    frequency_penalty=self.config.frequency_penalty,
                    presence_penalty=self.config.presence_penalty,
                    stream=True,
                    **kwargs
                )
            )

            # 流式返回内容
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI流式响应错误: {str(e)}")
            raise LLMError(f"OpenAI流式响应错误: {str(e)}", "openai")