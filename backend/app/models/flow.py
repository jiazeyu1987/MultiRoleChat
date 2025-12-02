from datetime import datetime
from app import db
import json


class FlowTemplate(db.Model):
    """流程模板模型"""
    __tablename__ = 'flow_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # teaching/review/debate等
    description = db.Column(db.Text)
    version = db.Column(db.String(20), default='1.0.0')
    is_active = db.Column(db.Boolean, default=True)
    termination_config = db.Column(db.Text)  # 结束条件配置，JSON格式
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    steps = db.relationship('FlowStep', lazy='dynamic', order_by='FlowStep.order')

    @property
    def termination_config_dict(self):
        """获取结束条件配置字典"""
        if self.termination_config:
            try:
                return json.loads(self.termination_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @termination_config_dict.setter
    def termination_config_dict(self, value):
        """设置结束条件配置"""
        if isinstance(value, dict):
            self.termination_config = json.dumps(value, ensure_ascii=False)
        else:
            self.termination_config = value

    def to_dict(self, include_steps=False):
        """转换为字典"""
        result = {
            'id': self.id,
            'name': self.name,
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
    """流程步骤模型"""
    __tablename__ = 'flow_steps'

    id = db.Column(db.Integer, primary_key=True)
    flow_template_id = db.Column(db.Integer, db.ForeignKey('flow_templates.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    speaker_role_ref = db.Column(db.String(50), nullable=False)  # 模板内角色引用
    target_role_ref = db.Column(db.String(50))  # 目标角色引用
    task_type = db.Column(db.String(50), nullable=False)  # ask_question/answer_question等
    context_scope = db.Column(db.String(50), nullable=False)  # last_n_messages/last_round/all等
    context_param = db.Column(db.Text)  # 上下文参数，JSON格式
    loop_config = db.Column(db.Text)  # 循环配置，JSON格式
    condition_config = db.Column(db.Text)  # 条件配置，JSON格式
    next_step_id = db.Column(db.Integer, db.ForeignKey('flow_steps.id'))  # 下一步骤ID
    description = db.Column(db.String(500))

    # 关系
    next_step = db.relationship('FlowStep', remote_side=[id])

    @property
    def context_param_dict(self):
        """获取上下文参数字典"""
        if self.context_param:
            try:
                return json.loads(self.context_param)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @context_param_dict.setter
    def context_param_dict(self, value):
        """设置上下文参数"""
        if isinstance(value, dict):
            self.context_param = json.dumps(value, ensure_ascii=False)
        else:
            self.context_param = value

    @property
    def loop_config_dict(self):
        """获取循环配置字典"""
        if self.loop_config:
            try:
                return json.loads(self.loop_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @loop_config_dict.setter
    def loop_config_dict(self, value):
        """设置循环配置"""
        if isinstance(value, dict):
            self.loop_config = json.dumps(value, ensure_ascii=False)
        else:
            self.loop_config = value

    @property
    def condition_config_dict(self):
        """获取条件配置字典"""
        if self.condition_config:
            try:
                return json.loads(self.condition_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @condition_config_dict.setter
    def condition_config_dict(self, value):
        """设置条件配置"""
        if isinstance(value, dict):
            self.condition_config = json.dumps(value, ensure_ascii=False)
        else:
            self.condition_config = value

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'flow_template_id': self.flow_template_id,
            'order': self.order,
            'speaker_role_ref': self.speaker_role_ref,
            'target_role_ref': self.target_role_ref,
            'task_type': self.task_type,
            'context_scope': self.context_scope,
            'context_param': self.context_param_dict,
            'loop_config': self.loop_config_dict,
            'condition_config': self.condition_config_dict,
            'next_step_id': self.next_step_id,
            'description': self.description
        }

    def __repr__(self):
        return f'<FlowStep {self.order}:{self.speaker_role_ref}>'