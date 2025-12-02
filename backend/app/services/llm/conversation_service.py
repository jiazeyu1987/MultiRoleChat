from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from ..simple_llm import LLMResponse
from .manager import LLMMessage

class LLMError(Exception):
    """自定义LLM错误"""
    def __init__(self, message, provider=None):
        super().__init__(message)
        self.provider = provider
from .manager import llm_manager

logger = logging.getLogger(__name__)


class ConversationLLMService:
    """对话LLM服务 - 专门处理多角色对话生成"""

    def __init__(self, default_provider: str = None):
        self.default_provider = default_provider
        self.response_cache = {}  # 简单的响应缓存

    async def generate_role_response(
        self,
        role_info: Dict[str, Any],
        task_info: Dict[str, Any],
        history_messages: List[Dict[str, Any]] = None,
        provider: str = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """
        为特定角色生成对话响应

        Args:
            role_info: 角色信息
            task_info: 任务信息
            history_messages: 历史消息列表
            provider: LLM提供商
            use_cache: 是否使用缓存

        Returns:
            LLMResponse: 生成的响应
        """
        # 生成缓存键
        cache_key = None
        if use_cache:
            cache_key = self._generate_cache_key(role_info, task_info, history_messages)
            if cache_key in self.response_cache:
                logger.debug(f"使用缓存响应: {cache_key}")
                return self.response_cache[cache_key]

        try:
            # 获取LLM服务
            service = llm_manager.get_service(provider or self.default_provider)

            # 构建上下文消息
            messages = service.build_context_messages(role_info, task_info, history_messages)

            # 生成响应
            response = await service.generate_response_with_retry(messages)

            # 缓存响应
            if use_cache and cache_key:
                self.response_cache[cache_key] = response

            return response

        except Exception as e:
            logger.error(f"生成角色响应失败: {str(e)}")
            raise LLMError(f"生成角色响应失败: {str(e)}")

    async def generate_response_with_context(
        self,
        speaker_role: Dict[str, Any],
        target_role: Dict[str, Any] = None,
        session_topic: str = "",
        task_type: str = "general",
        task_description: str = "",
        history_messages: List[Dict[str, Any]] = None,
        current_round: int = 1,
        step_count: int = 0,
        provider: str = None
    ) -> LLMResponse:
        """
        基于上下文生成响应

        Args:
            speaker_role: 发言角色信息
            target_role: 目标角色信息
            session_topic: 会话主题
            task_type: 任务类型
            task_description: 任务描述
            history_messages: 历史消息
            current_round: 当前轮次
            step_count: 已执行步数
            provider: LLM提供商

        Returns:
            LLMResponse: 生成的响应
        """
        # 构建角色信息
        role_info = {
            'name': speaker_role.get('name', '未知角色'),
            'description': speaker_role.get('description', ''),
            'style': speaker_role.get('style', '自然友好'),
            'focus_points': speaker_role.get('focus_points', []),
        }

        # 构建任务信息
        task_info = {
            'task_type': task_type,
            'description': task_description,
            'session_topic': session_topic,
            'current_round': current_round,
            'step_count': step_count,
        }

        # 如果有目标角色，添加到任务信息中
        if target_role:
            task_info['target_role'] = target_role.get('name', '未知角色')

        return await self.generate_role_response(
            role_info=role_info,
            task_info=task_info,
            history_messages=history_messages,
            provider=provider
        )

    def _generate_cache_key(
        self,
        role_info: Dict[str, Any],
        task_info: Dict[str, Any],
        history_messages: List[Dict[str, Any]] = None
    ) -> str:
        """
        生成缓存键

        Args:
            role_info: 角色信息
            task_info: 任务信息
            history_messages: 历史消息

        Returns:
            str: 缓存键
        """
        import hashlib
        import json

        # 构建缓存数据
        cache_data = {
            'role_name': role_info.get('name'),
            'task_type': task_info.get('task_type'),
            'session_topic': task_info.get('session_topic'),
            'current_round': task_info.get('current_round'),
            'history_count': len(history_messages) if history_messages else 0,
        }

        # 如果有历史消息，只取最后一条的消息内容作为缓存的一部分
        if history_messages:
            last_message = history_messages[-1]
            cache_data['last_message_speaker'] = last_message.get('speaker_role')
            cache_data['last_message_content'] = last_message.get('content', '')[:100]  # 只取前100个字符

        # 生成哈希
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def clear_cache(self):
        """清空响应缓存"""
        self.response_cache.clear()
        logger.info("已清空LLM响应缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计
        """
        return {
            'cache_size': len(self.response_cache),
            'cache_keys': list(self.response_cache.keys())[:10]  # 只显示前10个键
        }

    async def validate_response_quality(
        self,
        response: LLMResponse,
        role_info: Dict[str, Any],
        task_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证响应质量

        Args:
            response: LLM响应
            role_info: 角色信息
            task_info: 任务信息

        Returns:
            Dict[str, Any]: 质量评估结果
        """
        content = response.content.lower()
        role_name = role_info.get('name', '').lower()
        task_type = task_info.get('task_type', '').lower()

        quality_score = 0.0
        issues = []

        # 检查响应长度
        if len(response.content) < 20:
            issues.append("响应过短")
        elif len(response.content) > 2000:
            issues.append("响应过长")
        else:
            quality_score += 0.2

        # 检查角色一致性
        if role_name and role_name in content:
            issues.append("响应中包含角色名称")
        else:
            quality_score += 0.2

        # 检查任务相关性
        task_keywords = {
            'ask_question': ['问题', '?', '请问', '想问'],
            'answer_question': ['回答', '我认为', '根据', '我的看法'],
            'summarize': ['总结', '概括', '归纳', '总的来说'],
            'evaluate': ['评估', '评价', '分析', '判断'],
        }

        if task_type in task_keywords:
            if any(keyword in content for keyword in task_keywords[task_type]):
                quality_score += 0.3
            else:
                issues.append(f"响应与任务类型 {task_type} 不匹配")

        # 检查语言质量
        if not response.content.strip():
            issues.append("响应为空")
        elif len(set(response.content)) < 20:  # 字符多样性检查
            issues.append("响应字符多样性不足")
        else:
            quality_score += 0.3

        return {
            'quality_score': min(quality_score, 1.0),
            'issues': issues,
            'response_length': len(response.content),
            'token_usage': response.usage,
            'model': response.model
        }


# 全局对话LLM服务实例
conversation_llm_service = ConversationLLMService()