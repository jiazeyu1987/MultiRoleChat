from marshmallow import Schema, fields, validate, validates, ValidationError


class RoleSchema(Schema):
    """角色模式"""
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    type = fields.String(required=True, validate=validate.OneOf([
        'teacher', 'student', 'expert', 'reviewer', 'official', 'lawyer', 'other'
    ]))
    description = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    style = fields.String(validate=validate.Length(max=200))
    constraints = fields.String(validate=validate.Length(max=500))
    focus_points = fields.List(fields.String(), validate=validate.Length(max=10))
    is_builtin = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates('name')
    def validate_name(self, value):
        """验证角色名称唯一性"""
        from app.models import Role
        if self.context.get('role_id'):  # 更新场景
            if Role.query.filter(Role.name == value, Role.id != self.context['role_id']).first():
                raise ValidationError('角色名称已存在')
        else:  # 创建场景
            if Role.query.filter_by(name=value).first():
                raise ValidationError('角色名称已存在')


class RoleListSchema(Schema):
    """角色列表模式"""
    roles = fields.List(fields.Nested(RoleSchema()))
    total = fields.Integer()
    page = fields.Integer()
    page_size = fields.Integer()