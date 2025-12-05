"""Redis缓存服务

提供高性能的数据缓存功能，支持步骤进度和LLM交互数据的缓存
"""

import json
import pickle
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from flask import current_app
from app import db


class CacheService:
    """Redis缓存服务类"""

    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self.default_ttl = 300  # 5分钟默认TTL
        self.logger = logging.getLogger(__name__)

        if REDIS_AVAILABLE:
            self._initialize_redis()

    def _initialize_redis(self):
        """初始化Redis连接"""
        try:
            # 从环境变量获取Redis配置
            redis_host = current_app.config.get('REDIS_HOST', 'localhost')
            redis_port = current_app.config.get('REDIS_PORT', 6379)
            redis_db = current_app.config.get('REDIS_DB', 0)
            redis_password = current_app.config.get('REDIS_PASSWORD', None)

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # 测试连接
            self.redis_client.ping()
            self.enabled = True
            self.logger.info("Redis cache service initialized successfully")

        except Exception as e:
            self.enabled = False
            self.logger.warning(f"Redis not available, cache disabled: {str(e)}")

    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """生成缓存键"""
        return f"{prefix}:{identifier}"

    def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return pickle.dumps(value).hex()

    def _deserialize_value(self, value: str, use_pickle: bool = False) -> Any:
        """反序列化值"""
        if not value:
            return None

        try:
            if use_pickle:
                return pickle.loads(bytes.fromhex(value))
            else:
                return json.loads(value)
        except (json.JSONDecodeError, ValueError, TypeError, pickle.UnpicklingError):
            self.logger.warning(f"Failed to deserialize cached value: {value[:100]}...")
            return None

    def get(self, key: str, default: Any = None, use_pickle: bool = False) -> Any:
        """获取缓存值"""
        if not self.enabled:
            return default

        try:
            cached_value = self.redis_client.get(key)
            if cached_value is None:
                return default

            return self._deserialize_value(cached_value, use_pickle)

        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {str(e)}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None, use_pickle: bool = False) -> bool:
        """设置缓存值"""
        if not self.enabled:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized_value = self._serialize_value(value)

            if self.redis_client.setex(key, ttl, serialized_value):
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return True

        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.enabled:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {str(e)}")
            return False

    def clear(self, pattern: Optional[str] = None) -> int:
        """清除缓存"""
        if not self.enabled:
            return 0

        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                return self.redis_client.flushdb()
        except Exception as e:
            self.logger.error(f"Cache clear error: {str(e)}")
            return 0

    def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        if not self.enabled:
            return 0

        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            self.logger.error(f"Cache increment error for key {key}: {str(e)}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        if not self.enabled:
            return False

        try:
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            self.logger.error(f"Cache expire error for key {key}: {str(e)}")
            return False


class StepProgressCache:
    """步骤进度专用缓存"""

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.logger = logging.getLogger(__name__)

    def get_session_progress(self, session_id: int, include_details: bool = False) -> Optional[Dict]:
        """获取会话进度缓存"""
        key = self.cache._get_cache_key('step_progress', f"session_{session_id}_details_{include_details}")
        return self.cache.get(key)

    def set_session_progress(self, session_id: int, progress_data: Dict, ttl: int = 600) -> bool:
        """设置会话进度缓存"""
        key = self.cache._get_cache_key('step_progress', f"session_{session_id}_details_{progress_data.get('include_details', False)}")
        return self.cache.set(key, progress_data, ttl)

    def invalidate_session_progress(self, session_id: int) -> bool:
        """清除会话进度缓存"""
        pattern = self.cache._get_cache_key('step_progress', f"session_{session_id}_*")
        return self.cache.clear(pattern)

    def get_flow_visualization(self, session_id: int) -> Optional[Dict]:
        """获取流程可视化缓存"""
        key = self.cache._get_cache_key('flow_viz', f"session_{session_id}")
        return self.cache.get(key)

    def set_flow_visualization(self, session_id: int, viz_data: Dict, ttl: int = 300) -> bool:
        """设置流程可视化缓存"""
        key = self.cache._get_cache_key('flow_viz', f"session_{session_id}")
        return self.cache.set(key, viz_data, ttl)


class LLMInteractionCache:
    """LLM交互专用缓存"""

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.logger = logging.getLogger(__name__)

    def get_session_interactions(self, session_id: int, page: int = 1, per_page: int = 50) -> Optional[Dict]:
        """获取会话LLM交互缓存"""
        key = self.cache._get_cache_key('llm_interactions', f"session_{session_id}_page_{page}_perpage_{per_page}")
        return self.cache.get(key)

    def set_session_interactions(self, session_id: int, interactions_data: Dict, ttl: int = 180) -> bool:
        """设置会话LLM交互缓存"""
        key = self.cache._get_cache_key('llm_interactions', f"session_{session_id}_page_{interactions_data.get('pagination', {}).get('page', 1)}_perpage_{interactions_data.get('pagination', {}).get('per_page', 50)}")
        return self.cache.set(key, interactions_data, ttl)

    def get_llm_interaction_details(self, interaction_id: int) -> Optional[Dict]:
        """获取LLM交互详情缓存"""
        key = self.cache._get_cache_key('llm_detail', f"interaction_{interaction_id}")
        return self.cache.get(key)

    def set_llm_interaction_details(self, interaction_id: int, details: Dict, ttl: int = 600) -> bool:
        """设置LLM交互详情缓存"""
        key = self.cache._get_cache_key('llm_detail', f"interaction_{interaction_id}")
        return self.cache.set(key, details, ttl)

    def invalidate_session_llm_data(self, session_id: int) -> bool:
        """清除会话LLM数据缓存"""
        pattern = self.cache._get_cache_key('llm_interactions', f"session_{session_id}_*")
        return self.cache.clear(pattern)

    def get_session_statistics(self, session_id: int, days: int = 7) -> Optional[Dict]:
        """获取会话统计缓存"""
        key = self.cache._get_cache_key('llm_stats', f"session_{session_id}_days_{days}")
        return self.cache.get(key)

    def set_session_statistics(self, session_id: int, stats: Dict, ttl: int = 300) -> bool:
        """设置会话统计缓存"""
        key = self.cache._get_cache_key('llm_stats', f"session_{session_id}_days_{days}")
        return self.cache.set(key, stats, ttl)

    def get_system_metrics(self) -> Optional[Dict]:
        """获取系统指标缓存"""
        key = self.cache._get_cache_key('system', 'metrics')
        return self.cache.get(key)

    def set_system_metrics(self, metrics: Dict, ttl: int = 60) -> bool:
        """设置系统指标缓存"""
        key = self.cache._get_cache_key('system', 'metrics')
        return self.cache.set(key, metrics, ttl)

    def get_usage_trends(self, days: int = 30) -> Optional[Dict]:
        """获取使用趋势缓存"""
        key = self.cache._get_cache_key('usage_trends', f"days_{days}")
        return self.cache.get(key)

    def set_usage_trends(self, trends: Dict, ttl: int = 3600) -> bool:
        """设置使用趋势缓存"""
        key = self.cache._get_cache_key('usage_trends', f"days_{days}")
        return self.cache.set(key, trends, ttl)


class RealtimeUpdateCache:
    """实时更新专用缓存"""

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.logger = logging.getLogger(__name__)

    def get_active_sessions(self) -> Optional[List]:
        """获取活跃会话列表缓存"""
        key = self.cache._get_cache_key('realtime', 'active_sessions')
        return self.cache.get(key)

    def set_active_sessions(self, sessions: List, ttl: int = 30) -> bool:
        """设置活跃会话列表缓存"""
        key = self.cache._get_cache_key('realtime', 'active_sessions')
        return self.cache.set(key, sessions, ttl)

    def get_connection_stats(self) -> Optional[Dict]:
        """获取连接统计缓存"""
        key = self.cache._get_cache_key('realtime', 'connection_stats')
        return self.cache.get(key)

    def set_connection_stats(self, stats: Dict, ttl: int = 60) -> bool:
        """设置连接统计缓存"""
        key = self.cache._get_cache_key('realtime', 'connection_stats')
        return self.cache.set(key, stats, ttl)


def cache_result(ttl: Optional[int] = None, key_prefix: str = "", use_pickle: bool = False):
    """缓存结果装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            cache_service = get_cache_service()

            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key, use_pickle=use_pickle)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            cache_service.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """清理特定模式的缓存"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            cache_service.clear(pattern)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 全局缓存服务实例
_cache_service_instance = None

def get_cache_service() -> CacheService:
    """获取缓存服务实例（单例模式）"""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService()
    return _cache_service_instance

def get_step_progress_cache() -> StepProgressCache:
    """获取步骤进度缓存实例"""
    return StepProgressCache(get_cache_service())

def get_llm_interaction_cache() -> LLMInteractionCache:
    """获取LLM交互缓存实例"""
    return LLMInteractionCache(get_cache_service())

def get_realtime_update_cache() -> RealtimeUpdateCache:
    """获取实时更新缓存实例"""
    return RealtimeUpdateCache(get_cache_service())