"""
API密钥管理和权限控制服务

提供安全的API密钥管理、权限验证和敏感信息过滤功能
"""

import os
import re
import logging
import hashlib
import hmac
import json
import base64
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
from dataclasses import dataclass

from flask import current_app, request, g
from app import db

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """权限级别枚举"""
    READ_ONLY = "read_only"          # 只读权限，只能查看基本信息
    BASIC = "basic"                  # 基础权限，可以使用LLM功能
    DEBUG = "debug"                  # 调试权限，可以查看详细信息
    ADMIN = "admin"                  # 管理员权限，完全访问权限


class SensitiveDataType(Enum):
    """敏感数据类型枚举"""
    API_KEY = "api_key"
    TOKEN = "token"
    PASSWORD = "password"
    SECRET = "secret"
    PRIVATE_KEY = "private_key"
    PERSONAL_INFO = "personal_info"


@dataclass
class Permission:
    """权限数据结构"""
    user_id: str
    level: PermissionLevel
    resources: List[str]
    expires_at: Optional[datetime] = None
    ip_whitelist: Optional[List[str]] = None


class APIKeyManager:
    """API密钥管理器"""

    def __init__(self):
        """初始化API密钥管理器"""
        self.sensitive_patterns = self._load_sensitive_patterns()
        self.permission_cache = {}
        self.api_key_aliases = {}
        self._load_api_key_aliases()

    def _load_sensitive_patterns(self) -> Dict[SensitiveDataType, List[re.Pattern]]:
        """加载敏感数据识别模式"""
        patterns = {
            SensitiveDataType.API_KEY: [
                # OpenAI API Keys
                re.compile(r'sk-[A-Za-z0-9]{48}', re.IGNORECASE),
                # Anthropic API Keys
                re.compile(r'sk-ant-api03-[A-Za-z0-9_-]{95}', re.IGNORECASE),
                # Generic API keys pattern
                re.compile(r'[A-Za-z0-9_-]{32,}'),
                # Secret keys pattern
                re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'),
            ],
            SensitiveDataType.TOKEN: [
                # JWT tokens
                re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
                # Bearer tokens
                re.compile(r'Bearer\s+[A-Za-z0-9_.-]+'),
            ],
            SensitiveDataType.PASSWORD: [
                # Password fields
                re.compile(r'"password"\s*:\s*"[^"]+"', re.IGNORECASE),
                # Pass phrases
                re.compile(r'"pass"\s*:\s*"[^"]+"', re.IGNORECASE),
            ],
            SensitiveDataType.SECRET: [
                # Secret fields
                re.compile(r'"secret"\s*:\s*"[^"]+"', re.IGNORECASE),
                # Private keys
                re.compile(r'-----BEGIN [A-Z ]+-----[^-]+-----END [A-Z ]+-----'),
            ],
            SensitiveDataType.PERSONAL_INFO: [
                # Email addresses
                re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\--]+\.[A-Z|a-z]{2,}\b'),
                # Phone numbers
                re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
                # Credit card numbers (simplified)
                re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
            ],
            SensitiveDataType.PRIVATE_KEY: [
                # RSA private keys
                re.compile(r'-----BEGIN RSA PRIVATE KEY-----[^-]+-----END RSA PRIVATE KEY-----'),
                # SSH private keys
                re.compile(r'-----BEGIN OPENSSH PRIVATE KEY-----[^-]+-----END OPENSSH PRIVATE KEY-----'),
                # Generic private keys
                re.compile(r'-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----'),
            ],
        }
        return patterns

    def _load_api_key_aliases(self):
        """加载API密钥别名映射"""
        # 为API密钥创建安全的别名
        self.api_key_aliases = {
            'OPENAI_API_KEY': 'openai_key_alias',
            'ANTHROPIC_API_KEY': 'anthropic_key_alias',
            'GOOGLE_API_KEY': 'google_key_alias',
            'AZURE_API_KEY': 'azure_key_alias',
        }

    def mask_sensitive_data(self, text: str, mask_char: str = "*", mask_length: int = 8) -> str:
        """
        过滤和屏蔽敏感数据

        Args:
            text: 要过滤的文本
            mask_char: 屏蔽字符
            mask_length: 屏蔽长度

        Returns:
            str: 过滤后的文本
        """
        if not text:
            return text

        masked_text = text

        # 对每种敏感数据类型进行过滤
        for data_type, patterns in self.sensitive_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(masked_text)
                for match in matches:
                    sensitive_value = match.group()
                    masked_value = self._mask_sensitive_value(
                        sensitive_value, mask_char, mask_length, data_type
                    )
                    masked_text = masked_text.replace(sensitive_value, masked_value)

        # 特殊处理：环境变量中的API密钥
        masked_text = self._mask_env_api_keys(masked_text, mask_char, mask_length)

        return masked_text

    def _mask_sensitive_value(
        self,
        value: str,
        mask_char: str,
        mask_length: int,
        data_type: SensitiveDataType
    ) -> str:
        """
        屏蔽敏感值

        Args:
            value: 原始值
            mask_char: 屏蔽字符
            mask_length: 屏蔽长度
            data_type: 数据类型

        Returns:
            str: 屏蔽后的值
        """
        if data_type == SensitiveDataType.API_KEY:
            # API密钥显示前3个字符和后4个字符
            if len(value) > 7:
                return value[:3] + mask_char * (len(value) - 7) + value[-4:]
            else:
                return mask_char * len(value)
        elif data_type == SensitiveDataType.TOKEN:
            # Token显示前8个字符
            if len(value) > 8:
                return value[:8] + mask_char * (len(value) - 8)
            else:
                return mask_char * len(value)
        elif data_type == SensitiveDataType.PERSONAL_INFO:
            # 个人信息显示部分内容
            if '@' in value:  # Email
                local, domain = value.split('@', 1)
                return local[:2] + mask_char * (len(local) - 2) + '@' + domain
            elif re.match(r'\d+', value):  # Phone or card number
                return value[:4] + mask_char * (len(value) - 4) + value[-4:]
        else:
            # 其他类型显示前几个字符
            visible_length = min(mask_length, len(value) // 3)
            return value[:visible_length] + mask_char * (len(value) - visible_length)

        return mask_char * mask_length

    def _mask_env_api_keys(self, text: str, mask_char: str, mask_length: int) -> str:
        """屏蔽环境变量中的API密钥"""
        # 替换常见的API密钥环境变量
        env_patterns = {
            'OPENAI_API_KEY': r'(OPENAI_API_KEY\s*=?\s*)([A-Za-z0-9_-]+)',
            'ANTHROPIC_API_KEY': r'(ANTHROPIC_API_KEY\s*=?\s*)([A-Za-z0-9_-]+)',
            'API_KEY': r'(API_KEY\s*=?\s*)([A-Za-z0-9_-]+)',
        }

        for env_var, pattern in env_patterns.items():
            def replace_func(match):
                key_part = match.group(1)
                value_part = match.group(2)
                if len(value_part) > 10:
                    masked_value = value_part[:4] + mask_char * (len(value_part) - 8) + value_part[-4:]
                else:
                    masked_value = mask_char * len(value_part)
                return key_part + masked_value

            text = re.sub(pattern, replace_func, text, flags=re.IGNORECASE)

        return text

    def get_safe_api_key(self, provider: str) -> Optional[str]:
        """
        获取安全的API密钥（带验证和过滤）

        Args:
            provider: 提供商名称

        Returns:
            Optional[str]: 安全的API密钥或None
        """
        try:
            # 优先从环境变量获取
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.getenv(env_key)

            if not api_key:
                logger.warning(f"API key not found for provider: {provider}")
                return None

            # 验证API密钥格式
            if not self._validate_api_key_format(provider, api_key):
                logger.error(f"Invalid API key format for provider: {provider}")
                return None

            # 检查API密钥是否过期（如果支持）
            if self._is_api_key_expired(api_key):
                logger.error(f"API key expired for provider: {provider}")
                return None

            return api_key

        except Exception as e:
            logger.error(f"Error getting API key for provider {provider}: {str(e)}")
            return None

    def _validate_api_key_format(self, provider: str, api_key: str) -> bool:
        """验证API密钥格式"""
        if not api_key or len(api_key) < 10:
            return False

        # 根据提供商验证格式
        if provider.lower() == 'openai':
            return api_key.startswith('sk-') and len(api_key) >= 20
        elif provider.lower() == 'anthropic':
            return api_key.startswith('sk-ant-api03-') and len(api_key) >= 50
        elif provider.lower() in ['google', 'azure']:
            return len(api_key) >= 20
        else:
            # 通用验证：至少20个字符，包含字母和数字
            return len(api_key) >= 20 and any(c.isalpha() for c in api_key) and any(c.isdigit() for c in api_key)

    def _is_api_key_expired(self, api_key: str) -> bool:
        """检查API密钥是否过期（简化版本）"""
        # 这里可以实现更复杂的过期检查逻辑
        # 例如，与API提供商验证密钥状态
        return False

    def create_permission(
        self,
        user_id: str,
        level: PermissionLevel,
        resources: List[str] = None,
        expires_at: Optional[datetime] = None,
        ip_whitelist: Optional[List[str]] = None
    ) -> Permission:
        """
        创建权限

        Args:
            user_id: 用户ID
            level: 权限级别
            resources: 资源列表
            expires_at: 过期时间
            ip_whitelist: IP白名单

        Returns:
            Permission: 权限对象
        """
        permission = Permission(
            user_id=user_id,
            level=level,
            resources=resources or [],
            expires_at=expires_at,
            ip_whitelist=ip_whitelist
        )

        # 缓存权限
        cache_key = f"permission:{user_id}"
        self.permission_cache[cache_key] = permission

        logger.info(f"Created permission for user {user_id} with level {level.value}")
        return permission

    def check_permission(self, user_id: str, required_level: PermissionLevel, resource: str = None) -> bool:
        """
        检查用户权限

        Args:
            user_id: 用户ID
            required_level: 所需权限级别
            resource: 资源名称

        Returns:
            bool: 是否有权限
        """
        try:
            # 从缓存获取权限
            cache_key = f"permission:{user_id}"
            permission = self.permission_cache.get(cache_key)

            if not permission:
                # 创建默认权限
                permission = self.create_permission(user_id, PermissionLevel.READ_ONLY)

            # 检查权限级别
            if not self._has_sufficient_permission(permission.level, required_level):
                return False

            # 检查资源权限
            if resource and not self._has_resource_access(permission, resource):
                return False

            # 检查过期时间
            if permission.expires_at and datetime.utcnow() > permission.expires_at:
                logger.warning(f"Permission expired for user {user_id}")
                return False

            # 检查IP白名单
            if permission.ip_whitelist and not self._is_ip_allowed(permission.ip_whitelist):
                logger.warning(f"IP not in whitelist for user {user_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking permission for user {user_id}: {str(e)}")
            return False

    def _has_sufficient_permission(self, user_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        """检查权限级别是否足够"""
        level_hierarchy = {
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.BASIC: 2,
            PermissionLevel.DEBUG: 3,
            PermissionLevel.ADMIN: 4,
        }

        return level_hierarchy.get(user_level, 0) >= level_hierarchy.get(required_level, 0)

    def _has_resource_access(self, permission: Permission, resource: str) -> bool:
        """检查资源访问权限"""
        if not permission.resources:
            return True  # 空资源列表表示可以访问所有资源

        return resource in permission.resources

    def _is_ip_allowed(self, ip_whitelist: List[str]) -> bool:
        """检查IP是否在白名单中"""
        try:
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
            if client_ip:
                # 处理代理情况，取第一个IP
                client_ip = client_ip.split(',')[0].strip()

            return client_ip in ip_whitelist or '*' in ip_whitelist
        except Exception:
            return False

    def audit_log(self, user_id: str, action: str, resource: str, details: Dict[str, Any] = None):
        """
        记录审计日志

        Args:
            user_id: 用户ID
            action: 操作类型
            resource: 资源名称
            details: 详细信息
        """
        try:
            audit_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '')),
                'user_agent': request.environ.get('HTTP_USER_AGENT', ''),
                'details': details or {}
            }

            # 过滤敏感信息
            audit_data['details'] = self.mask_sensitive_data(json.dumps(audit_data['details']))

            logger.info(f"AUDIT: {json.dumps(audit_data)}")

        except Exception as e:
            logger.error(f"Error recording audit log: {str(e)}")


# 全局API密钥管理器实例
api_key_manager = APIKeyManager()


def get_api_key_manager() -> APIKeyManager:
    """获取API密钥管理器实例"""
    return api_key_manager


def require_permission(level: PermissionLevel, resource: str = None):
    """
    权限检查装饰器

    Args:
        level: 所需权限级别
        resource: 资源名称
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取用户ID（这里需要根据实际认证系统调整）
            user_id = getattr(g, 'user_id', 'anonymous')

            # 检查权限
            if not api_key_manager.check_permission(user_id, level, resource):
                logger.warning(f"Access denied for user {user_id} to {resource}")
                return {'error': 'Access denied'}, 403

            # 记录审计日志
            api_key_manager.audit_log(user_id, 'access', resource, {
                'function': func.__name__,
                'args': str(args)[:100],  # 限制长度
                'kwargs': str(kwargs)[:100]
            })

            return func(*args, **kwargs)
        return wrapper
    return decorator


def filter_sensitive_data_decorator(mask_fields: List[str] = None):
    """
    敏感数据过滤装饰器

    Args:
        mask_fields: 需要屏蔽的字段列表
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            try:
                if isinstance(result, dict):
                    result = api_key_manager.mask_sensitive_data(json.dumps(result))
                    result = json.loads(result)
                elif isinstance(result, str):
                    result = api_key_manager.mask_sensitive_data(result)
            except Exception as e:
                logger.error(f"Error filtering sensitive data: {str(e)}")

            return result
        return wrapper
    return decorator