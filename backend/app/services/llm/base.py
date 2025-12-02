from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """LLM消息数据类"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM响应数据类"""
    content: str
    model: str
    usage: Dict[str, int]  # token使用情况
    finish_reason: Optional[str] = None
    response_time: float = 0.0


@dataclass
class LLMConfig:
    """LLM配置数据类"""
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class LLMError(Exception):
    """LLM服务基础异常类"""
    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(message)


class LLMRateLimitError(LLMError):
    """LLM速率限制异常"""
    pass


class LLMTimeoutError(LLMError):
    """LLM超时异常"""
    pass


class LLMQuotaExceededError(LLMError):
    """LLM配额超限异常"""
    pass


class BaseLLMService(ABC):
    """LLM服务基础抽象类"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider_name = self.__class__.__name__.replace('LLMService', '').lower()

    @abstractmethod
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

        Raises:
            LLMError: LLM服务相关错误
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        pass

    async def generate_response_with_retry(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        带重试机制的响应生成

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMResponse: LLM响应对象
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                response = await self.generate_response(messages, **kwargs)
                response.response_time = time.time() - start_time

                if attempt > 0:
                    logger.info(f"LLM调用成功，重试次数: {attempt}")

                return response

            except LLMRateLimitError as e:
                # 速率限制错误，需要等待更长时间
                wait_time = self.config.retry_delay * (2 ** attempt)
                logger.warning(f"LLM速率限制，等待 {wait_time} 秒后重试")
                await asyncio.sleep(wait_time)
                last_exception = e

            except (LLMTimeoutError, asyncio.TimeoutError) as e:
                # 超时错误
                if attempt < self.config.max_retries:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"LLM调用超时，等待 {wait_time} 秒后重试")
                    await asyncio.sleep(wait_time)
                    last_exception = e
                else:
                    logger.error(f"LLM调用超时，已达最大重试次数")
                    raise LLMTimeoutError(f"LLM调用超时: {str(e)}", self.provider_name)

            except LLMQuotaExceededError as e:
                # 配额超限，不重试
                logger.error(f"LLM配额已用完: {str(e)}")
                raise

            except Exception as e:
                # 其他错误
                if attempt < self.config.max_retries:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"LLM调用失败，等待 {wait_time} 秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                    last_exception = e
                else:
                    logger.error(f"LLM调用失败，已达最大重试次数: {str(e)}")
                    raise LLMError(f"LLM调用失败: {str(e)}", self.provider_name)

        # 如果所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise LLMError("LLM调用失败，未知错误", self.provider_name)

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
        task_prompt = f"""
当前任务：
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