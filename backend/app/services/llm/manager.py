from typing import Dict, Any, Optional, List
import os
import logging
from enum import Enum

from .base import BaseLLMService, LLMMessage, LLMResponse, LLMConfig, LLMError
from .openai_service import OpenAILLMService

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    # 未来可以添加更多提供商
    # ANTHROPIC = "anthropic"
    # AZURE_OPENAI = "azure_openai"
    # LOCAL_LLM = "local_llm"


class LLMManager:
    """LLM服务管理器"""

    def __init__(self):
        self._services: Dict[str, BaseLLMService] = {}
        self._default_provider: Optional[str] = None
        self._load_configurations()

    def _load_configurations(self):
        """加载配置文件"""
        # 从环境变量或配置文件加载
        self._configs = {
            LLMProvider.OPENAI.value: {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'base_url': os.getenv('OPENAI_BASE_URL'),  # 支持自定义API端点
                'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
                'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                'timeout': int(os.getenv('OPENAI_TIMEOUT', '30')),
                'max_retries': int(os.getenv('OPENAI_MAX_RETRIES', '3')),
            }
        }

        # 设置默认提供商
        self._default_provider = os.getenv('LLM_DEFAULT_PROVIDER', LLMProvider.OPENAI.value)

    def register_service(self, provider: str, service: BaseLLMService):
        """
        注册LLM服务

        Args:
            provider: 提供商名称
            service: LLM服务实例
        """
        self._services[provider] = service
        logger.info(f"已注册LLM服务: {provider}")

    def get_service(self, provider: str = None) -> BaseLLMService:
        """
        获取LLM服务实例

        Args:
            provider: 提供商名称，如果为None则使用默认提供商

        Returns:
            BaseLLMService: LLM服务实例

        Raises:
            LLMError: 服务不存在或初始化失败
        """
        if not provider:
            provider = self._default_provider

        if not provider:
            raise LLMError("未指定LLM提供商，且没有配置默认提供商")

        # 如果服务已存在，直接返回
        if provider in self._services:
            return self._services[provider]

        # 动态创建服务
        service = self._create_service(provider)
        if service:
            self.register_service(provider, service)
            return service

        raise LLMError(f"无法创建LLM服务: {provider}")

    def _create_service(self, provider: str) -> Optional[BaseLLMService]:
        """
        创建LLM服务实例

        Args:
            provider: 提供商名称

        Returns:
            BaseLLMService: LLM服务实例，失败返回None
        """
        try:
            if provider == LLMProvider.OPENAI.value:
                return self._create_openai_service()
            # 未来可以添加更多提供商
            # elif provider == LLMProvider.ANTHROPIC.value:
            #     return self._create_anthropic_service()
            else:
                logger.error(f"不支持的LLM提供商: {provider}")
                return None

        except Exception as e:
            logger.error(f"创建LLM服务失败 {provider}: {str(e)}")
            return None

    def _create_openai_service(self) -> OpenAILLMService:
        """创建OpenAI服务"""
        config_dict = self._configs.get(LLMProvider.OPENAI.value, {})
        api_key = config_dict.get('api_key')
        base_url = config_dict.get('base_url')

        if not api_key:
            raise LLMError("OpenAI API密钥未配置")

        config = LLMConfig(
            model=config_dict.get('model', 'gpt-3.5-turbo'),
            max_tokens=config_dict.get('max_tokens', 1000),
            temperature=config_dict.get('temperature', 0.7),
            timeout=config_dict.get('timeout', 30),
            max_retries=config_dict.get('max_retries', 3)
        )

        return OpenAILLMService(config, api_key=api_key, base_url=base_url)

    async def generate_response(
        self,
        provider: str = None,
        messages: List[LLMMessage] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成LLM响应

        Args:
            provider: 提供商名称
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMResponse: LLM响应
        """
        service = self.get_service(provider)
        return await service.generate_response_with_retry(messages, **kwargs)

    def list_available_providers(self) -> List[str]:
        """
        列出可用的提供商

        Returns:
            List[str]: 提供商列表
        """
        providers = []
        for provider in LLMProvider:
            config = self._configs.get(provider.value, {})
            if self._is_provider_available(provider.value, config):
                providers.append(provider.value)
        return providers

    def _is_provider_available(self, provider: str, config: Dict[str, Any]) -> bool:
        """
        检查提供商是否可用

        Args:
            provider: 提供商名称
            config: 配置信息

        Returns:
            bool: 是否可用
        """
        if provider == LLMProvider.OPENAI.value:
            return bool(config.get('api_key'))
        # 未来可以添加更多提供商的检查
        return False

    def get_provider_info(self, provider: str = None) -> Dict[str, Any]:
        """
        获取提供商信息

        Args:
            provider: 提供商名称

        Returns:
            Dict[str, Any]: 提供商信息
        """
        if not provider:
            provider = self._default_provider

        try:
            service = self.get_service(provider)
            if hasattr(service, 'get_model_info'):
                return service.get_model_info()
            else:
                return {
                    'provider': provider,
                    'model': getattr(service.config, 'model', 'unknown'),
                    'status': 'available'
                }
        except Exception as e:
            return {
                'provider': provider,
                'status': 'unavailable',
                'error': str(e)
            }

    def set_default_provider(self, provider: str):
        """
        设置默认提供商

        Args:
            provider: 提供商名称
        """
        if provider in self._services or self._is_provider_available(
            provider, self._configs.get(provider, {})
        ):
            self._default_provider = provider
            logger.info(f"已设置默认LLM提供商: {provider}")
        else:
            raise LLMError(f"提供商 {provider} 不可用")

    async def test_connection(self, provider: str = None) -> bool:
        """
        测试LLM服务连接

        Args:
            provider: 提供商名称

        Returns:
            bool: 连接是否成功
        """
        try:
            service = self.get_service(provider)
            test_messages = [
                LLMMessage(role="user", content="Hello, this is a test message.")
            ]
            response = await service.generate_response(test_messages)
            return bool(response.content)
        except Exception as e:
            logger.error(f"LLM连接测试失败 {provider}: {str(e)}")
            return False


# 全局LLM管理器实例
llm_manager = LLMManager()