"""
速率限制服务

提供API调用速率限制、防刷和保护功能
"""

import time
import hashlib
import logging
import json
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from flask import request, g
from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """速率限制类型"""
    API_CALL = "api_call"          # API调用限制
    DEBUG_ACCESS = "debug_access"   # 调试功能访问限制
    EXPORT = "export"              # 导出功能限制
    REALTIME = "realtime"          # 实时更新限制
    AUTH = "auth"                  # 认证尝试限制


@dataclass
class RateLimitRule:
    """速率限制规则"""
    key: str
    window_seconds: int           # 时间窗口（秒）
    max_requests: int             # 最大请求数
    block_duration: int          # 阻塞持续时间（秒）
    penalty_factor: float = 1.0  # 惩罚因子
    enabled: bool = True         # 是否启用


@dataclass
class RateLimitResult:
    """速率限制检查结果"""
    allowed: bool                # 是否允许
    remaining: int              # 剩余请求数
    reset_time: int             # 重置时间戳
    current_usage: int          # 当前使用量
    blocked: bool               # 是否被阻塞
    block_expires: int          # 阻塞过期时间
    retry_after: int            # 重试等待时间


class RateLimitService:
    """速率限制服务"""

    def __init__(self):
        """初始化速率限制服务"""
        self.cache_service = get_cache_service()
        self.rules = self._load_default_rules()
        self.local_cache = defaultdict(lambda: deque(maxlen=1000))  # 本地缓存用于快速检查

    def _load_default_rules(self) -> Dict[RateLimitType, RateLimitRule]:
        """加载默认速率限制规则"""
        return {
            RateLimitType.API_CALL: RateLimitRule(
                key="api_call",
                window_seconds=60,      # 1分钟
                max_requests=100,       # 最多100次请求
                block_duration=300,     # 阻塞5分钟
                penalty_factor=1.0
            ),
            RateLimitType.DEBUG_ACCESS: RateLimitRule(
                key="debug_access",
                window_seconds=300,     # 5分钟
                max_requests=20,        # 最多20次调试访问
                block_duration=600,     # 阻塞10分钟
                penalty_factor=2.0      # 更严厉的惩罚
            ),
            RateLimitType.EXPORT: RateLimitRule(
                key="export",
                window_seconds=3600,    # 1小时
                max_requests=10,        # 最多10次导出
                block_duration=1800,    # 阻塞30分钟
                penalty_factor=1.5
            ),
            RateLimitType.REALTIME: RateLimitRule(
                key="realtime",
                window_seconds=60,      # 1分钟
                max_requests=30,        # 最多30次实时更新
                block_duration=120,     # 阻塞2分钟
                penalty_factor=1.0
            ),
            RateLimitType.AUTH: RateLimitRule(
                key="auth",
                window_seconds=300,     # 5分钟
                max_requests=5,         # 最多5次认证尝试
                block_duration=900,     # 阻塞15分钟
                penalty_factor=3.0      # 非常严厉的惩罚
            ),
        }

    def check_rate_limit(
        self,
        limit_type: RateLimitType,
        identifier: str = None,
        weight: int = 1
    ) -> RateLimitResult:
        """
        检查速率限制

        Args:
            limit_type: 限制类型
            identifier: 标识符（用户ID、IP等）
            weight: 请求权重

        Returns:
            RateLimitResult: 限制检查结果
        """
        try:
            rule = self.rules.get(limit_type)
            if not rule or not rule.enabled:
                return RateLimitResult(
                    allowed=True,
                    remaining=999999,
                    reset_time=int(time.time()) + rule.window_seconds,
                    current_usage=0,
                    blocked=False,
                    block_expires=0,
                    retry_after=0
                )

            # 获取标识符
            if not identifier:
                identifier = self._get_identifier()

            # 生成缓存键
            cache_key = f"rate_limit:{rule.key}:{identifier}"
            block_key = f"rate_limit:block:{rule.key}:{identifier}"

            current_time = int(time.time())
            window_start = current_time - rule.window_seconds

            # 检查是否被阻塞
            block_info = self.cache_service.get(block_key)
            if block_info:
                block_expires = block_info.get('expires_at', 0)
                if current_time < block_expires:
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_time=block_expires,
                        current_usage=block_info.get('usage', 0),
                        blocked=True,
                        block_expires=block_expires,
                        retry_after=block_expires - current_time
                    )
                else:
                    # 阻塞已过期，删除
                    self.cache_service.delete(block_key)

            # 获取当前使用量
            usage_data = self.cache_service.get(cache_key) or {'requests': [], 'total': 0}

            # 清理过期的请求记录
            valid_requests = [req_time for req_time in usage_data['requests'] if req_time > window_start]

            # 应用权重
            effective_weight = weight * rule.penalty_factor

            # 检查是否超出限制
            current_total = usage_data['total'] + effective_weight
            if current_total > rule.max_requests:
                # 记录违规并应用阻塞
                self._apply_block(identifier, rule, current_total)

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + rule.window_seconds,
                    current_usage=current_total,
                    blocked=True,
                    block_expires=current_time + rule.block_duration,
                    retry_after=rule.block_duration
                )

            # 更新使用记录
            valid_requests.append(current_time)
            usage_data = {
                'requests': valid_requests,
                'total': current_total
            }

            # 更新缓存
            self.cache_service.set(cache_key, usage_data, ttl=rule.window_seconds + 60)

            # 更新本地缓存
            self.local_cache[identifier].append(current_time)

            remaining = max(0, rule.max_requests - current_total)

            return RateLimitResult(
                allowed=True,
                remaining=int(remaining),
                reset_time=current_time + rule.window_seconds,
                current_usage=int(current_total),
                blocked=False,
                block_expires=0,
                retry_after=0
            )

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # 出错时默认允许访问
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=int(time.time()) + 300,
                current_usage=0,
                blocked=False,
                block_expires=0,
                retry_after=0
            )

    def _apply_block(self, identifier: str, rule: RateLimitRule, current_usage: float):
        """应用阻塞惩罚"""
        block_key = f"rate_limit:block:{rule.key}:{identifier}"
        block_info = {
            'identifier': identifier,
            'rule_key': rule.key,
            'usage': current_usage,
            'created_at': int(time.time()),
            'expires_at': int(time.time()) + rule.block_duration,
            'violation_count': 1
        }

        # 检查是否已有阻塞记录
        existing_block = self.cache_service.get(block_key)
        if existing_block:
            block_info['violation_count'] = existing_block.get('violation_count', 0) + 1
            # 重复违规增加阻塞时间
            additional_block = block_info['violation_count'] * rule.block_duration * 0.5
            block_info['expires_at'] = int(time.time()) + rule.block_duration + additional_block

        self.cache_service.set(block_key, block_info, ttl=rule.block_duration + 300)

        logger.warning(
            f"Rate limit applied: {identifier} blocked for {rule.key} "
            f"until {datetime.fromtimestamp(block_info['expires_at'])}"
        )

    def _get_identifier(self) -> str:
        """获取请求标识符"""
        # 优先使用用户ID
        user_id = getattr(g, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # 使用IP地址
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')

        return f"ip:{client_ip}"

    def get_usage_stats(self, limit_type: RateLimitType, identifier: str = None) -> Dict[str, Any]:
        """
        获取使用统计

        Args:
            limit_type: 限制类型
            identifier: 标识符

        Returns:
            Dict: 使用统计信息
        """
        try:
            rule = self.rules.get(limit_type)
            if not rule:
                return {}

            if not identifier:
                identifier = self._get_identifier()

            cache_key = f"rate_limit:{rule.key}:{identifier}"
            usage_data = self.cache_service.get(cache_key) or {'requests': [], 'total': 0}

            current_time = int(time.time())
            window_start = current_time - rule.window_seconds
            valid_requests = [req_time for req_time in usage_data['requests'] if req_time > window_start]

            # 获取阻塞信息
            block_key = f"rate_limit:block:{rule.key}:{identifier}"
            block_info = self.cache_service.get(block_key)

            return {
                'rule': asdict(rule),
                'current_usage': len(valid_requests),
                'total_weighted_usage': usage_data['total'],
                'remaining': max(0, rule.max_requests - usage_data['total']),
                'reset_time': current_time + rule.window_seconds,
                'is_blocked': bool(block_info and current_time < block_info.get('expires_at', 0)),
                'block_info': block_info,
                'usage_in_window': len(valid_requests),
                'window_start': window_start,
                'window_end': current_time
            }

        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {}

    def reset_limit(self, limit_type: RateLimitType, identifier: str = None):
        """
        重置速率限制

        Args:
            limit_type: 限制类型
            identifier: 标识符
        """
        try:
            rule = self.rules.get(limit_type)
            if not rule:
                return False

            if not identifier:
                identifier = self._get_identifier()

            cache_key = f"rate_limit:{rule.key}:{identifier}"
            block_key = f"rate_limit:block:{rule.key}:{identifier}"

            # 删除使用记录和阻塞记录
            self.cache_service.delete(cache_key)
            self.cache_service.delete(block_key)

            # 清理本地缓存
            if identifier in self.local_cache:
                del self.local_cache[identifier]

            logger.info(f"Rate limit reset for {identifier} ({rule.key})")
            return True

        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}")
            return False

    def add_custom_rule(self, rule: RateLimitRule):
        """
        添加自定义速率限制规则

        Args:
            rule: 速率限制规则
        """
        self.rules[RateLimitType(rule.key)] = rule
        logger.info(f"Added custom rate limit rule: {rule.key}")

    def cleanup_expired_entries(self):
        """清理过期的速率限制条目"""
        try:
            current_time = int(time.time())
            cleaned_count = 0

            # 遍历本地缓存并清理过期条目
            for identifier in list(self.local_cache.keys()):
                request_times = self.local_cache[identifier]
                valid_times = [req_time for req_time in request_times if current_time - req_time < 3600]  # 保留1小时内的记录

                if valid_times:
                    self.local_cache[identifier] = deque(valid_times, maxlen=1000)
                else:
                    del self.local_cache[identifier]
                    cleaned_count += 1

            logger.info(f"Cleaned up {cleaned_count} expired rate limit entries")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up rate limit entries: {str(e)}")
            return 0


# 全局速率限制服务实例
rate_limit_service = RateLimitService()


def get_rate_limit_service() -> RateLimitService:
    """获取速率限制服务实例"""
    return rate_limit_service


def rate_limit(limit_type: RateLimitType, weight: int = 1):
    """
    速率限制装饰器

    Args:
        limit_type: 限制类型
        weight: 请求权重
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 检查速率限制
            result = rate_limit_service.check_rate_limit(limit_type, weight=weight)

            if not result.allowed:
                if result.blocked:
                    logger.warning(f"Request blocked due to rate limit violation: {result.retry_after}s")
                    return {
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests',
                        'retry_after': result.retry_after,
                        'reset_time': result.reset_time
                    }, 429
                else:
                    logger.warning(f"Request denied due to rate limit: {result.remaining} remaining")
                    return {
                        'error': 'Rate limit exceeded',
                        'message': 'Rate limit exceeded',
                        'remaining': result.remaining,
                        'reset_time': result.reset_time
                    }, 429

            # 添加速率限制头信息
            response = func(*args, **kwargs)

            if isinstance(response, tuple):
                data, status_code = response
                if isinstance(data, dict):
                    data['rate_limit'] = {
                        'remaining': result.remaining,
                        'reset_time': result.reset_time,
                        'current_usage': result.current_usage
                    }
                return data, status_code
            elif isinstance(response, dict):
                response['rate_limit'] = {
                    'remaining': result.remaining,
                    'reset_time': result.reset_time,
                    'current_usage': result.current_usage
                }
                return response

            return response

        return wrapper
    return decorator