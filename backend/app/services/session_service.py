import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import or_, and_
from app import db
from app.models import Session, SessionRole, Message, FlowTemplate, FlowStep, Role


class SessionError(Exception):
    """会话相关错误的基类"""
    pass


class SessionNotFoundError(SessionError):
    """会话不存在错误"""
    pass


class InvalidSessionStateError(SessionError):
    """会话状态无效错误"""
    pass


class FlowExecutionError(SessionError):
    """流程执行错误"""
    pass


class RoleMappingError(SessionError):
    """角色映射错误"""
    pass


class SessionService:
    """会话服务类"""

    @staticmethod
    def create_session(session_data: Dict[str, Any]) -> Session:
        """
        创建新的会话

        Args:
            session_data: 会话数据，包含topic, flow_template_id, role_mappings等

        Returns:
            Session: 创建的会话对象

        Raises:
            RoleMappingError: 角色映射错误
        """
        try:
            # 验证流程模板是否存在
            flow_template = FlowTemplate.query.get(session_data['flow_template_id'])
            if not flow_template:
                raise SessionNotFoundError(f"流程模板ID {session_data['flow_template_id']} 不存在")

            # 获取角色映射（可选）
            role_mappings = session_data.get('role_mappings')

            # 如果提供了角色映射，进行验证
            if role_mappings is not None:
                SessionService._validate_role_mappings(flow_template, role_mappings)

            # 创建会话
            session = Session(
                user_id=session_data.get('user_id'),
                topic=session_data['topic'],
                flow_template_id=session_data['flow_template_id'],
                status='not_started',
                current_round=0,
                executed_steps_count=0
            )

            # 保存流程模板快照
            session.flow_snapshot_dict = flow_template.to_dict(include_steps=True)

            db.session.add(session)
            db.session.flush()  # 获取会话ID

            # 创建会话角色映射（如果提供了角色映射）
            if role_mappings is not None:
                SessionService._create_session_roles(session.id, role_mappings)
                # 保存角色快照
                session.roles_snapshot_dict = SessionService._create_roles_snapshot(role_mappings)
            else:
                # 无角色映射模式下，创建空的角色快照
                session.roles_snapshot_dict = {}

            db.session.commit()
            return session

        except Exception as e:
            db.session.rollback()
            if isinstance(e, SessionError):
                raise
            raise SessionError(f"创建会话失败: {str(e)}")

    @staticmethod
    def _validate_role_mappings(flow_template: FlowTemplate, role_mappings: Dict[str, int]) -> None:
        """
        验证角色映射

        Args:
            flow_template: 流程模板
            role_mappings: 角色映射字典

        Raises:
            RoleMappingError: 角色映射错误
        """
        # 获取流程中使用的所有角色引用
        template_roles = set()
        for step in flow_template.steps:
            template_roles.add(step.speaker_role_ref)
            if step.target_role_ref:
                template_roles.add(step.target_role_ref)

        # 检查角色映射完整性
        missing_roles = template_roles - set(role_mappings.keys())
        if missing_roles:
            raise RoleMappingError(f"缺少角色映射: {', '.join(missing_roles)}")

        # 检查角色是否存在
        for role_ref, role_id in role_mappings.items():
            role = Role.query.get(role_id)
            if not role:
                raise RoleMappingError(f"角色ID {role_id} 不存在")

    @staticmethod
    def _create_session_roles(session_id: int, role_mappings: Dict[str, int]) -> None:
        """
        创建会话角色映射

        Args:
            session_id: 会话ID
            role_mappings: 角色映射字典
        """
        session_roles = []
        for role_ref, role_id in role_mappings.items():
            session_role = SessionRole(
                session_id=session_id,
                role_ref=role_ref,
                role_id=role_id
            )
            session_roles.append(session_role)

        db.session.add_all(session_roles)

    @staticmethod
    def _create_roles_snapshot(role_mappings: Dict[str, int]) -> Dict[str, Any]:
        """
        创建角色快照

        Args:
            role_mappings: 角色映射字典

        Returns:
            Dict: 角色快照字典
        """
        snapshot = {}
        for role_ref, role_id in role_mappings.items():
            role = Role.query.get(role_id)
            if role:
                snapshot[role_ref] = role.to_dict()
        return snapshot

    @staticmethod
    def get_session_by_id(session_id: int, include_roles: bool = True, include_messages: bool = False) -> Optional[Session]:
        """
        根据ID获取会话

        Args:
            session_id: 会话ID
            include_roles: 是否包含角色信息
            include_messages: 是否包含消息信息

        Returns:
            Optional[Session]: 会话对象，如果不存在则返回None
        """
        session = Session.query.get(session_id)
        if session and include_roles:
            # 预加载角色信息
            session.session_roles
        if session and include_messages:
            # 预加载消息信息
            session.messages
        return session

    @staticmethod
    def get_sessions_list(page: int = 1, page_size: int = 20, search: str = '',
                         status: str = '', user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取会话列表

        Args:
            page: 页码
            page_size: 每页大小
            search: 搜索关键词
            status: 状态筛选
            user_id: 用户ID筛选

        Returns:
            Dict: 包含会话列表和分页信息的字典
        """
        query = Session.query

        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    Session.topic.contains(search),
                    Session.error_reason.contains(search)
                )
            )

        # 状态过滤
        if status:
            query = query.filter(Session.status == status)

        # 用户过滤
        if user_id is not None:
            query = query.filter(Session.user_id == user_id)

        # 分页查询
        pagination = query.order_by(Session.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'sessions': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def start_session(session_id: int) -> Session:
        """
        开始会话执行

        Args:
            session_id: 会话ID

        Returns:
            Session: 更新后的会话对象

        Raises:
            SessionNotFoundError: 会话不存在
            InvalidSessionStateError: 会话状态无效
        """
        session = Session.query.get(session_id)
        if not session:
            raise SessionNotFoundError(f"会话ID {session_id} 不存在")

        if session.status != 'not_started':
            raise InvalidSessionStateError(f"会话状态为 {session.status}，无法开始执行")

        try:
            # 获取流程模板的步骤
            flow_template = FlowTemplate.query.get(session.flow_template_id)
            if not flow_template:
                raise SessionNotFoundError(f"流程模板ID {session.flow_template_id} 不存在")

            # 获取第一个步骤
            first_step = flow_template.steps.order_by(FlowStep.order).first()
            if not first_step:
                raise FlowExecutionError("流程模板中没有定义步骤")

            # 更新会话状态
            session.status = 'running'
            session.current_step_id = first_step.id
            session.current_round = 1
            session.updated_at = datetime.utcnow()

            db.session.commit()
            return session

        except Exception as e:
            db.session.rollback()
            if isinstance(e, SessionError):
                raise
            raise SessionError(f"开始会话失败: {str(e)}")

    @staticmethod
    def pause_session(session_id: int) -> Session:
        """
        暂停会话

        Args:
            session_id: 会话ID

        Returns:
            Session: 更新后的会话对象

        Raises:
            SessionNotFoundError: 会话不存在
            InvalidSessionStateError: 会话状态无效
        """
        session = Session.query.get(session_id)
        if not session:
            raise SessionNotFoundError(f"会话ID {session_id} 不存在")

        if session.status != 'running':
            raise InvalidSessionStateError(f"会话状态为 {session.status}，无法暂停")

        try:
            session.status = 'paused'
            session.updated_at = datetime.utcnow()
            db.session.commit()
            return session

        except Exception as e:
            db.session.rollback()
            raise SessionError(f"暂停会话失败: {str(e)}")

    @staticmethod
    def resume_session(session_id: int) -> Session:
        """
        恢复会话

        Args:
            session_id: 会话ID

        Returns:
            Session: 更新后的会话对象

        Raises:
            SessionNotFoundError: 会话不存在
            InvalidSessionStateError: 会话状态无效
        """
        session = Session.query.get(session_id)
        if not session:
            raise SessionNotFoundError(f"会话ID {session_id} 不存在")

        if session.status != 'paused':
            raise InvalidSessionStateError(f"会话状态为 {session.status}，无法恢复")

        try:
            session.status = 'running'
            session.updated_at = datetime.utcnow()
            db.session.commit()
            return session

        except Exception as e:
            db.session.rollback()
            raise SessionError(f"恢复会话失败: {str(e)}")

    @staticmethod
    def finish_session(session_id: int, reason: str = None) -> Session:
        """
        结束会话

        Args:
            session_id: 会话ID
            reason: 结束原因

        Returns:
            Session: 更新后的会话对象

        Raises:
            SessionNotFoundError: 会话不存在
        """
        session = Session.query.get(session_id)
        if not session:
            raise SessionNotFoundError(f"会话ID {session_id} 不存在")

        try:
            session.status = 'finished'
            session.ended_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            if reason:
                session.error_reason = reason

            db.session.commit()
            return session

        except Exception as e:
            db.session.rollback()
            raise SessionError(f"结束会话失败: {str(e)}")

    @staticmethod
    def get_session_statistics() -> Dict[str, Any]:
        """
        获取会话统计信息

        Returns:
            Dict: 统计信息字典
        """
        total_sessions = Session.query.count()

        # 按状态统计
        status_stats = db.session.query(
            Session.status,
            db.func.count(Session.id).label('count')
        ).group_by(Session.status).all()

        status_distribution = {stat.status: stat.count for stat in status_stats}

        # 按模板类型统计
        template_type_stats = db.session.query(
            FlowTemplate.type,
            db.func.count(Session.id).label('count')
        ).join(FlowTemplate).group_by(FlowTemplate.type).all()

        template_type_distribution = {stat.type: stat.count for stat in template_type_stats}

        # 消息统计
        total_messages = Message.query.count()
        avg_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0

        return {
            'total_sessions': total_sessions,
            'status_distribution': status_distribution,
            'template_type_distribution': template_type_distribution,
            'total_messages': total_messages,
            'avg_messages_per_session': round(avg_messages_per_session, 2)
        }

    @staticmethod
    def get_role_mapping(session_id: int) -> Dict[str, int]:
        """
        获取会话的角色映射

        Args:
            session_id: 会话ID

        Returns:
            Dict: 角色映射字典 {role_ref: role_id}
        """
        session_roles = SessionRole.query.filter_by(session_id=session_id).all()
        return {sr.role_ref: sr.role_id for sr in session_roles}

    @staticmethod
    def get_session_role_by_ref(session_id: int, role_ref: str) -> Optional[SessionRole]:
        """
        根据角色引用获取会话角色

        Args:
            session_id: 会话ID
            role_ref: 角色引用

        Returns:
            Optional[SessionRole]: 会话角色对象
        """
        return SessionRole.query.filter_by(
            session_id=session_id,
            role_ref=role_ref
        ).first()

    @staticmethod
    def get_role_for_execution(session_id: int, role_ref: str) -> Optional[Role]:
        """
        获取执行步骤时需要的角色对象
        支持有角色映射和无角色映射两种模式

        Args:
            session_id: 会话ID
            role_ref: 角色引用

        Returns:
            Optional[Role]: 角色对象
        """
        # 首先尝试从会话角色映射中获取
        session_role = SessionService.get_session_role_by_ref(session_id, role_ref)
        if session_role and session_role.role:
            return session_role.role

        # 如果没有映射，尝试直接通过角色名称查找
        role = Role.query.filter_by(name=role_ref).first()
        if role:
            return role

        # 如果还是找不到，尝试模糊匹配
        role = Role.query.filter(Role.name.contains(role_ref)).first()
        return role

    @staticmethod
    def is_session_executable(session_id: int) -> bool:
        """
        判断会话是否可以执行下一步骤

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否可执行
        """
        session = Session.query.get(session_id)
        if not session:
            return False

        return session.status == 'running' and session.current_step_id is not None

    @staticmethod
    def create_branch_session(session_id: int, branch_point_message_id: int,
                             new_topic: str = None) -> Session:
        """
        创建分支会话

        Args:
            session_id: 原会话ID
            branch_point_message_id: 分支点消息ID
            new_topic: 新会话主题

        Returns:
            Session: 分支会话对象

        Raises:
            SessionNotFoundError: 原会话不存在
        """
        original_session = Session.query.get(session_id)
        if not original_session:
            raise SessionNotFoundError(f"原会话ID {session_id} 不存在")

        try:
            # 获取分支点之前的消息
            branch_point_message = Message.query.get(branch_point_message_id)
            if not branch_point_message or branch_point_message.session_id != session_id:
                raise SessionNotFoundError(f"分支点消息ID {branch_point_message_id} 不存在或不属于该会话")

            # 创建新会话
            new_session = Session(
                user_id=original_session.user_id,
                topic=new_topic or f"{original_session.topic} (分支)",
                flow_template_id=original_session.flow_template_id,
                flow_snapshot_dict=original_session.flow_snapshot_dict,
                roles_snapshot_dict=original_session.roles_snapshot_dict,
                status='not_started',
                current_round=0,
                executed_steps_count=0
            )

            db.session.add(new_session)
            db.session.flush()  # 获取新会话ID

            # 复制角色映射
            original_roles = SessionRole.query.filter_by(session_id=session_id).all()
            new_roles = []
            for original_role in original_roles:
                new_role = SessionRole(
                    session_id=new_session.id,
                    role_ref=original_role.role_ref,
                    role_id=original_role.role_id
                )
                new_roles.append(new_role)
            db.session.add_all(new_roles)

            # 复制分支点之前的消息
            messages_to_copy = Message.query.filter(
                and_(
                    Message.session_id == session_id,
                    Message.id <= branch_point_message_id
                )
            ).order_by(Message.created_at).all()

            new_messages = []
            for original_message in messages_to_copy:
                # 创建原始消息到新会话角色的映射
                original_session_role = SessionRole.query.get(original_message.speaker_session_role_id)
                new_session_role = SessionRole.query.filter_by(
                    session_id=new_session.id,
                    role_ref=original_session_role.role_ref
                ).first()

                new_message = Message(
                    session_id=new_session.id,
                    speaker_session_role_id=new_session_role.id,
                    target_session_role_id=original_message.target_session_role_id,
                    reply_to_message_id=original_message.reply_to_message_id,
                    content=original_message.content,
                    content_summary=original_message.content_summary,
                    round_index=original_message.round_index,
                    section=original_message.section
                )
                new_messages.append(new_message)
            db.session.add_all(new_messages)

            db.session.commit()
            return new_session

        except Exception as e:
            db.session.rollback()
            raise SessionError(f"创建分支会话失败: {str(e)}")

    @staticmethod
    def get_active_sessions_count() -> int:
        """
        获取活跃会话数量

        Returns:
            int: 活跃会话数量
        """
        try:
            # 活跃会话定义：状态为running的会话
            active_count = Session.query.filter_by(status='running').count()
            return active_count
        except Exception as e:
            # 如果查询失败，返回0
            return 0

    @staticmethod
    def get_recent_sessions(limit: int = 5) -> List[Session]:
        """
        获取最近的会话列表

        Args:
            limit: 返回的最大数量

        Returns:
            List[Session]: 最近会话列表
        """
        try:
            recent_sessions = Session.query.order_by(Session.created_at.desc()).limit(limit).all()
            return recent_sessions
        except Exception:
            # 如果查询失败，返回空列表
            return []