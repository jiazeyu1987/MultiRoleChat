from datetime import datetime
from app import db
import json


class FlowTemplate(db.Model):
    """流程模板模型 - 与前端接口完全对齐"""
    __tablename__ = 'flow_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200), nullable=True)  # 与前端一致：可选字段
    type = db.Column(db.String(50), nullable=False)   # 严格匹配前端枚举
    description = db.Column(db.Text, nullable=True)   # 与前端一致：可选字段
    version = db.Column(db.String(20), nullable=True)  # 与前端一致：可选，无默认值
    is_active = db.Column(db.Boolean, nullable=True, default=None)  # 与前端一致：可选字段
    _termination_config = db.Column('termination_config', db.Text, nullable=True)  # 与前端一致：可选字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    steps = db.relationship('FlowStep', lazy='dynamic', order_by='FlowStep.order')

    @property
    def termination_config_dict(self) -> dict:
        """获取结束条件配置字典 - 直接返回字典，前端友好"""
        if self._termination_config:
            try:
                return json.loads(self._termination_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @termination_config_dict.setter
    def termination_config_dict(self, value):
        """设置结束条件配置 - 支持字典直接赋值"""
        if value is None:
            self._termination_config = None
        elif isinstance(value, dict):
            self._termination_config = json.dumps(value, ensure_ascii=False)
        else:
            self._termination_config = str(value)

    def to_dict(self, include_steps=False):
        """转换为字典 - 完全匹配前端接口"""
        result = {
            'id': self.id,
            'name': self.name,
            'topic': self.topic,
            'type': self.type,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'termination_config': self.termination_config_dict,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'step_count': self.steps.count()
        }

        if include_steps:
            result['steps'] = [step.to_dict() for step in self.steps]

        return result

    def __repr__(self):
        return f'<FlowTemplate {self.name}>'


class FlowStep(db.Model):
    """流程步骤模型 - 与前端接口完全对齐"""
    __tablename__ = 'flow_steps'

    id = db.Column(db.Integer, primary_key=True)
    flow_template_id = db.Column(db.Integer, db.ForeignKey('flow_templates.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    speaker_role_ref = db.Column(db.String(50), nullable=False)
    target_role_ref = db.Column(db.String(50), nullable=True)  # 与前端一致：可选字段
    task_type = db.Column(db.String(50), nullable=False)  # 严格匹配前端枚举
    _context_scope = db.Column('context_scope', db.Text, nullable=False)  # 支持字符串或数组格式
    _context_param = db.Column('context_param', db.Text, nullable=True)  # 与前端一致：可选字段
    _logic_config = db.Column('logic_config', db.Text, nullable=True)  # 与前端一致：可选字段
    next_step_id = db.Column(db.Integer, db.ForeignKey('flow_steps.id'), nullable=True)  # 与前端一致：可选字段
    description = db.Column(db.String(500), nullable=True)  # 与前端一致：可选字段

    # 关系
    next_step = db.relationship('FlowStep', remote_side=[id])

    @property
    def context_scope(self):
        """获取context_scope值 - 直接返回前端期望的格式"""
        if self._context_scope:
            try:
                # 尝试解析为JSON（数组格式）
                parsed = json.loads(self._context_scope)
                # 如果解析成功且是数组，直接返回数组
                if isinstance(parsed, (list, dict)):
                    return parsed
                # 如果解析成功但不是数组，返回原字符串
                return self._context_scope
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，直接返回字符串
                return self._context_scope
        return self._context_scope

    @context_scope.setter
    def context_scope(self, value):
        """设置context_scope值 - 支持字符串、数组或对象"""
        if value is None:
            self._context_scope = None
        elif isinstance(value, (list, dict)):
            # 如果是数组或对象，转换为JSON字符串存储
            self._context_scope = json.dumps(value, ensure_ascii=False)
        else:
            # 如果是字符串，直接存储
            self._context_scope = str(value)

    @property
    def context_param(self) -> dict:
        """获取上下文参数字典 - 直接返回字典"""
        if self._context_param:
            try:
                return json.loads(self._context_param)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @context_param.setter
    def context_param(self, value):
        """设置上下文参数 - 支持字典直接赋值"""
        if value is None:
            self._context_param = None
        elif isinstance(value, dict):
            self._context_param = json.dumps(value, ensure_ascii=False)
        else:
            self._context_param = str(value)

    @property
    def logic_config(self) -> dict:
        """获取逻辑配置字典 - 直接返回字典"""
        if self._logic_config:
            try:
                return json.loads(self._logic_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @logic_config.setter
    def logic_config(self, value):
        """设置逻辑配置 - 支持字典直接赋值"""
        if value is None:
            self._logic_config = None
        elif isinstance(value, dict):
            self._logic_config = json.dumps(value, ensure_ascii=False)
        else:
            self._logic_config = str(value)

    @property
    def loop_config_dict(self) -> dict:
        """获取循环配置字典 - logic_config的别名，保持向后兼容"""
        return self.logic_config

    @loop_config_dict.setter
    def loop_config_dict(self, value):
        """设置循环配置 - logic_config的别名，保持向后兼容"""
        self.logic_config = value

    def to_dict(self):
        """转换为字典 - 完全匹配前端接口"""
        result = {
            'id': self.id,
            'flow_template_id': self.flow_template_id,
            'order': self.order,
            'speaker_role_ref': self.speaker_role_ref,
            'target_role_ref': self.target_role_ref,
            'task_type': self.task_type,
            'context_scope': self.context_scope,  # 自动处理字符串/数组格式
            'context_param': self.context_param,
            'logic_config': self.logic_config,
            'next_step_id': self.next_step_id,
            'description': self.description
        }

        return result

    def __repr__(self):
        return f'<FlowStep {self.order}:{self.speaker_role_ref}>'
