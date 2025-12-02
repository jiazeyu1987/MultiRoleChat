from marshmallow import Schema, fields, validate
import json


class JSONStringField(fields.Field):
    """Custom field that converts JSON strings to dictionaries during serialization"""

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        if isinstance(value, dict):
            return json.dumps(value)
        return value


class SessionRoleSchema(Schema):
    """会话角色模式"""
    id = fields.Integer(dump_only=True)
    session_id = fields.Integer(dump_only=True)
    role_ref = fields.String(required=True, validate=validate.Length(min=1, max=50))
    role_id = fields.Integer(required=True)
    role_name = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class SessionSchema(Schema):
    """会话模式"""
    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    topic = fields.String(required=True, validate=validate.Length(min=1, max=200))
    flow_template_id = fields.Integer(required=True)
    status = fields.String(dump_only=True, validate=validate.OneOf([
        'not_started', 'running', 'paused', 'finished', 'failed'
    ]))
    current_step_id = fields.Integer(dump_only=True)
    current_round = fields.Integer(dump_only=True)
    executed_steps_count = fields.Integer(dump_only=True)
    error_reason = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    ended_at = fields.DateTime(dump_only=True)
    message_count = fields.Integer(dump_only=True)
    role_count = fields.Integer(dump_only=True)
    session_roles = fields.List(fields.Nested(SessionRoleSchema()), dump_only=True)
    flow_snapshot = JSONStringField(dump_only=True)
    roles_snapshot = JSONStringField(dump_only=True)


class CreateSessionSchema(Schema):
    """创建会话模式"""
    topic = fields.String(required=True, validate=validate.Length(min=1, max=200))
    flow_template_id = fields.Integer(required=True)
    role_mappings = fields.Dict(required=True)  # {"teacher": 1, "student": 2}


class SessionListSchema(Schema):
    """会话列表模式"""
    sessions = fields.List(fields.Nested(SessionSchema(exclude=('session_roles', 'flow_snapshot', 'roles_snapshot'))))
    total = fields.Integer()
    page = fields.Integer()
    page_size = fields.Integer()


class SessionExecutionSchema(Schema):
    """会话执行模式"""
    success = fields.Boolean()
    message = fields.String()
    step_executed = fields.Boolean()
    session_status = fields.String()
    generated_message = fields.Dict()  # 生成的消息信息