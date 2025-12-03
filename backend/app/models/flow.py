from datetime import datetime
from app import db
import json


class FlowTemplate(db.Model):
    """流程模板模型"""
    __tablename__ = 'flow_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200))  # 前端topic字段，支持议题/预设主题
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
            'topic': self.topic,  # 添加topic字段支持前端
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
    task_type = db.Column(db.String(50), nullable=False)  # ask_question/answer_question等，扩展支持前端类型
    context_scope = db.Column(db.Text, nullable=False)  # 支持字符串或JSON数组格式，适配前端
    context_param = db.Column(db.Text)  # 上下文参数，JSON格式
    logic_config = db.Column(db.Text)  # 统一的逻辑配置，JSON格式，适配前端logic_config
    # 保留旧字段以兼容现有数据
    loop_config = db.Column(db.Text)  # 循环配置，JSON格式 (保留兼容性)
    condition_config = db.Column(db.Text)  # 条件配置，JSON格式 (保留兼容性)
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
                value = json.loads(self.loop_config)
                # 只接受字典类型，其他类型一律视为无效配置
                return value if isinstance(value, dict) else {}
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
                value = json.loads(self.condition_config)
                # 只接受字典类型，其他类型一律视为无效配置
                return value if isinstance(value, dict) else {}
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

    @property
    def logic_config_dict(self):
        """获取统一逻辑配置字典"""
        if self.logic_config:
            try:
                value = json.loads(self.logic_config)
                # 如果存储的是合法的字典 JSON，则直接返回
                if isinstance(value, dict):
                    return value
                # 其他类型一律视为无效配置，回退到旧字段合并逻辑
            except (json.JSONDecodeError, TypeError):
                # 解析失败则回退到旧字段合并逻辑
                pass

        # 如果没有新的logic_config，尝试从旧字段合并
        config = {}
        loop_cfg = self.loop_config_dict
        if isinstance(loop_cfg, dict) and loop_cfg:
            config.update(loop_cfg)
        cond_cfg = self.condition_config_dict
        if isinstance(cond_cfg, dict) and cond_cfg:
            config.update(cond_cfg)
        return config

    @logic_config_dict.setter
    def logic_config_dict(self, value):
        """设置统一逻辑配置"""
        if isinstance(value, dict):
            self.logic_config = json.dumps(value, ensure_ascii=False)
        else:
            self.logic_config = value

    @property
    def context_scope_value(self):
        """获取context_scope值，支持字符串或数组格式"""
        if self.context_scope:
            try:
                # 尝试解析为JSON数组
                parsed = json.loads(self.context_scope)
                return parsed
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，直接返回字符串
                return self.context_scope
        return self.context_scope

    @context_scope_value.setter
    def context_scope_value(self, value):
        """设置context_scope值，支持字符串或数组"""
        if isinstance(value, (list, dict)):
            # 如果是数组或对象，转换为JSON字符串
            self.context_scope = json.dumps(value, ensure_ascii=False)
        else:
            # 如果是字符串，直接存储
            self.context_scope = str(value) if value is not None else None

    def to_dict(self):
        """转换为字典，适配前端数据结构"""
        result = {
            'id': self.id,
            'flow_template_id': self.flow_template_id,
            'order': self.order,
            'speaker_role_ref': self.speaker_role_ref,
            'target_role_ref': self.target_role_ref,
            'task_type': self.task_type,
            'context_scope': self.context_scope_value,  # 支持字符串或数组格式
            'context_param': self.context_param_dict,
            'logic_config': self.logic_config_dict,  # 使用统一的logic_config
            'next_step_id': self.next_step_id,
            'description': self.description
        }

        # 保留旧字段以兼容可能的使用场景
        # if self.loop_config_dict:
        #     result['loop_config'] = self.loop_config_dict
        # if self.condition_config_dict:
        #     result['condition_config'] = self.condition_config_dict

        return result

    def __repr__(self):
        return f'<FlowStep {self.order}:{self.speaker_role_ref}>'
