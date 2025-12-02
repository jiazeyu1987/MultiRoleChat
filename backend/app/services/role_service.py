from typing import List, Dict, Optional, Any
from app import db
from app.models import Role


class RoleService:
    """角色服务类"""

    @staticmethod
    def get_roles_count() -> int:
        """
        获取角色总数

        Returns:
            int: 角色总数
        """
        try:
            return Role.query.count()
        except Exception:
            # 如果查询失败，返回0
            return 0

    @staticmethod
    def get_all_roles() -> List[Role]:
        """
        获取所有角色

        Returns:
            List[Role]: 角色列表
        """
        try:
            return Role.query.all()
        except Exception:
            # 如果查询失败，返回空列表
            return []

    @staticmethod
    def get_active_roles() -> List[Role]:
        """
        获取活跃角色

        Returns:
            List[Role]: 活跃角色列表
        """
        try:
            return Role.query.filter_by(is_active=True).all()
        except Exception:
            # 如果查询失败，返回空列表
            return []

    @staticmethod
    def get_role_by_id(role_id: int) -> Optional[Role]:
        """
        根据ID获取角色

        Args:
            role_id: 角色ID

        Returns:
            Optional[Role]: 角色对象或None
        """
        try:
            return Role.query.get(role_id)
        except Exception:
            return None

    @staticmethod
    def get_builtin_roles() -> List[Role]:
        """
        获取内置角色

        Returns:
            List[Role]: 内置角色列表
        """
        try:
            return Role.query.filter_by(is_builtin=True).all()
        except Exception:
            # 如果查询失败，返回空列表
            return []

    @staticmethod
    def get_roles_by_type(role_type: str) -> List[Role]:
        """
        根据类型获取角色

        Args:
            role_type: 角色类型

        Returns:
            List[Role]: 指定类型的角色列表
        """
        try:
            return Role.query.filter_by(type=role_type).all()
        except Exception:
            # 如果查询失败，返回空列表
            return []