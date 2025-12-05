from datetime import datetime
from app import db
import json


class Session(db.Model):
    """会话模型"""
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)  # 用户ID，暂未实现用户系统
    topic = db.Column(db.String(200), nullable=False)  # 会话主题
    flow_template_id = db.Column(db.Integer, db.ForeignKey('flow_templates.id'), nullable=False)

    # 性能索引定义
    __table_args__ = (
        db.Index('idx_sessions_user_id', 'user_id'),
        db.Index('idx_sessions_status_created', 'status', 'created_at'),
        db.Index('idx_sessions_flow_template', 'flow_template_id'),
        db.Index('idx_sessions_updated_at', 'updated_at'),
        db.Index('idx_sessions_status_updated_composite', 'status', 'updated_at', 'id'),
    )
    flow_snapshot = db.Column(db.Text)  # 流程模板快照，JSON格式
    roles_snapshot = db.Column(db.Text)  # 参与角色快照，JSON格式
    status = db.Column(db.String(20), default='not_started')  # not_started/running/paused/finished/failed
    current_step_id = db.Column(db.Integer)  # 当前步骤ID
    current_round = db.Column(db.Integer, default=0)  # 当前轮次
    executed_steps_count = db.Column(db.Integer, default=0)  # 已执行步骤数
    error_reason = db.Column(db.String(500))  # 错误原因
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    # 关系
    flow_template = db.relationship('FlowTemplate', backref='sessions')
    session_roles = db.relationship('SessionRole', backref='session', lazy='dynamic')
    messages = db.relationship('Message', backref='session', lazy='dynamic',
                              order_by='Message.created_at')

    @property
    def flow_snapshot_dict(self):
        """获取流程快照字典"""
        if self.flow_snapshot:
            try:
                return json.loads(self.flow_snapshot)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @flow_snapshot_dict.setter
    def flow_snapshot_dict(self, value):
        """设置流程快照"""
        if isinstance(value, dict):
            self.flow_snapshot = json.dumps(value, ensure_ascii=False)
        else:
            self.flow_snapshot = value

    @property
    def roles_snapshot_dict(self):
        """获取角色快照字典"""
        if self.roles_snapshot:
            try:
                return json.loads(self.roles_snapshot)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @roles_snapshot_dict.setter
    def roles_snapshot_dict(self, value):
        """设置角色快照"""
        if isinstance(value, dict):
            self.roles_snapshot = json.dumps(value, ensure_ascii=False)
        else:
            self.roles_snapshot = value

    def is_active(self):
        """判断会话是否处于活跃状态"""
        return self.status in ['not_started', 'running']

    def can_execute_step(self):
        """判断是否可以执行下一步骤"""
        return self.status == 'running' and self.current_step_id is not None

    def get_role_mapping(self):
        """获取角色映射"""
        return {sr.role_ref: sr.role_id for sr in self.session_roles}

    def to_dict(self, include_messages=False, include_roles=False):
        """转换为字典"""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'topic': self.topic,
            'flow_template_id': self.flow_template_id,
            'status': self.status,
            'current_step_id': self.current_step_id,
            'current_round': self.current_round,
            'executed_steps_count': self.executed_steps_count,
            'error_reason': self.error_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'message_count': self.messages.count(),
            'role_count': self.session_roles.count()
        }

        if include_messages:
            result['messages'] = [msg.to_dict() for msg in self.messages]

        if include_roles:
            result['session_roles'] = [sr.to_dict() for sr in self.session_roles]
            result['flow_snapshot'] = self.flow_snapshot_dict
            result['roles_snapshot'] = self.roles_snapshot_dict

        return result

    def __repr__(self):
        return f'<Session {self.id}:{self.topic}>'


class SessionRole(db.Model):
    """会话角色模型"""
    __tablename__ = 'session_roles'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    role_ref = db.Column(db.String(50), nullable=False)  # 模板内角色引用
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)  # 实际角色ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    role = db.relationship('Role')
    sent_messages = db.relationship('Message', foreign_keys='Message.speaker_session_role_id')
    target_messages = db.relationship('Message', foreign_keys='Message.target_session_role_id')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role_ref': self.role_ref,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<SessionRole {self.role_ref}:{self.role_id}>'