from marshmallow import Schema, fields, validate, validates, ValidationError


class CreateSessionSchema(Schema):
    """创建会话模式"""
    topic = fields.String(required=True, validate=validate.Length(min=1, max=200))
    flow_template_id = fields.Integer(required=True, validate=validate.Range(min=1))
    role_mappings = fields.Dict(required=True)  # {"teacher": 1, "student": 2}
    user_id = fields.Integer()

    @validates('flow_template_id')
    def validate_flow_template_id(self, value):
        """验证流程模板是否存在"""
        from app.models import FlowTemplate
        if not FlowTemplate.query.get(value):
            raise ValidationError('流程模板不存在')

    @validates('role_mappings')
    def validate_role_mappings(self, value):
        """验证角色映射"""
        if not value:
            raise ValidationError('角色映射不能为空')

        from app.models import Role
        for role_ref, role_id in value.items():
            if not isinstance(role_ref, str) or not role_ref.strip():
                raise ValidationError('角色引用必须是有效的字符串')
            if not isinstance(role_id, int) or role_id <= 0:
                raise ValidationError('角色ID必须是正整数')
            if not Role.query.get(role_id):
                raise ValidationError(f'角色ID {role_id} 不存在')


class UpdateSessionSchema(Schema):
    """更新会话模式"""
    topic = fields.String(validate=validate.Length(min=1, max=200))
    status = fields.String(validate=validate.OneOf(['not_started', 'running', 'paused', 'finished']))


class SessionExecutionSchema(Schema):
    """会话执行模式"""
    force_execute = fields.Boolean()  # 是否强制执行


class SessionControlSchema(Schema):
    """会话控制模式"""
    action = fields.String(required=True, validate=validate.OneOf([
        'start', 'pause', 'resume', 'finish'
    ]))
    reason = fields.String()  # 结束会话时的原因


class CreateBranchSessionSchema(Schema):
    """创建分支会话模式"""
    branch_point_message_id = fields.Integer(required=True, validate=validate.Range(min=1))
    new_topic = fields.String(validate=validate.Length(min=1, max=200))

    @validates('branch_point_message_id')
    def validate_branch_point_message_id(self, value):
        """验证分支点消息是否存在"""
        from app.models import Message
        if not Message.query.get(value):
            raise ValidationError('分支点消息不存在')