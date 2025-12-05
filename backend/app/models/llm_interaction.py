from datetime import datetime
from app import db
import json


class LLMInteraction(db.Model):
    """LLM交互记录模型"""
    __tablename__ = 'llm_interactions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('flow_steps.id'))  # 关联的流程步骤
    session_role_id = db.Column(db.Integer, db.ForeignKey('session_roles.id'))  # 发言角色

    # 性能索引定义
    __table_args__ = (
        db.Index('idx_llm_interactions_session_created', 'session_id', 'created_at'),
        db.Index('idx_llm_interactions_step_id', 'step_id'),
        db.Index('idx_llm_interactions_status', 'status'),
        db.Index('idx_llm_interactions_provider_model', 'provider', 'model'),
        db.Index('idx_llm_interactions_session_role', 'session_role_id'),
        db.Index('idx_llm_interactions_request_id', 'request_id'),
        db.Index('idx_llm_interactions_created_at', 'created_at'),
        db.Index('idx_llm_interactions_latency', 'latency_ms'),
        db.Index('idx_llm_interactions_session_status_created', 'session_id', 'status', 'created_at'),
    )

    # LLM调用信息
    provider = db.Column(db.String(50), default='openai')  # LLM提供商
    model = db.Column(db.String(100))  # 使用的模型
    request_id = db.Column(db.String(100))  # 请求ID，用于追踪

    # 输入信息
    system_prompt = db.Column(db.Text)  # 系统提示词
    user_prompt = db.Column(db.Text, nullable=False)  # 用户提示词
    full_prompt = db.Column(db.Text)  # 完整提示词（包含上下文）
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=1000)

    # 输出信息
    response_content = db.Column(db.Text)  # LLM响应内容
    raw_response = db.Column(db.Text)  # 原始响应（JSON格式）
    finish_reason = db.Column(db.String(50))  # 完成原因
    usage_input_tokens = db.Column(db.Integer)  # 输入token数
    usage_output_tokens = db.Column(db.Integer)  # 输出token数
    usage_total_tokens = db.Column(db.Integer)  # 总token数

    # 状态和时间
    status = db.Column(db.String(20), default='pending')  # pending/streaming/completed/failed/timeout
    error_message = db.Column(db.Text)  # 错误信息
    latency_ms = db.Column(db.Integer)  # 延迟（毫秒）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)  # 开始时间
    completed_at = db.Column(db.DateTime)  # 完成时间

    # 关系
    session = db.relationship('Session', backref='llm_interactions')
    step = db.relationship('FlowStep', backref='llm_interactions')
    session_role = db.relationship('SessionRole', backref='llm_interactions')

    @property
    def full_prompt_dict(self):
        """获取完整提示词字典"""
        if self.full_prompt:
            try:
                return json.loads(self.full_prompt)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @full_prompt_dict.setter
    def full_prompt_dict(self, value):
        """设置完整提示词"""
        if isinstance(value, dict):
            self.full_prompt = json.dumps(value, ensure_ascii=False)
        else:
            self.full_prompt = value

    @property
    def raw_response_dict(self):
        """获取原始响应字典"""
        if self.raw_response:
            try:
                return json.loads(self.raw_response)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @raw_response_dict.setter
    def raw_response_dict(self, value):
        """设置原始响应"""
        if isinstance(value, dict):
            self.raw_response = json.dumps(value, ensure_ascii=False)
        else:
            self.raw_response = value

    @property
    def duration_seconds(self):
        """获取执行时长（秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        elif self.started_at:
            delta = datetime.utcnow() - self.started_at
            return delta.total_seconds()
        return None

    def is_active(self):
        """判断是否正在进行中"""
        return self.status in ['pending', 'streaming']

    def is_successful(self):
        """判断是否成功完成"""
        return self.status == 'completed' and self.response_content is not None

    def to_dict(self, include_details=False):
        """转换为字典"""
        result = {
            'id': self.id,
            'session_id': self.session_id,
            'step_id': self.step_id,
            'session_role_id': self.session_role_id,
            'provider': self.provider,
            'model': self.model,
            'request_id': self.request_id,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'status': self.status,
            'error_message': self.error_message,
            'latency_ms': self.latency_ms,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

        # Token使用信息
        if self.usage_input_tokens or self.usage_output_tokens or self.usage_total_tokens:
            result['usage'] = {
                'input_tokens': self.usage_input_tokens,
                'output_tokens': self.usage_output_tokens,
                'total_tokens': self.usage_total_tokens
            }

        if include_details:
            # 包含详细内容
            result.update({
                'system_prompt': self.system_prompt,
                'user_prompt': self.user_prompt,
                'full_prompt': self.full_prompt_dict,
                'response_content': self.response_content,
                'raw_response': self.raw_response_dict,
                'finish_reason': self.finish_reason
            })

            # 关联信息
            if self.step:
                result['step_info'] = {
                    'id': self.step.id,
                    'name': self.step.name,
                    'type': self.step.step_type
                }

            if self.session_role and self.session_role.role:
                result['role_info'] = {
                    'id': self.session_role.id,
                    'name': self.session_role.role.name,
                    'role_ref': self.session_role.role_ref
                }

        return result

    def __repr__(self):
        return f'<LLMInteraction {self.id}:Session{self.session_id}-{self.status}>'