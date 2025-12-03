from marshmallow import Schema, fields, validate, validates, ValidationError
from .flow import FlowStepSchema


class FlowTemplateCreateSchema(Schema):
    """流程模板创建模式，完全适配前端FlowTemplateRequest结构"""
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    topic = fields.String(validate=validate.Length(max=200))  # 添加topic字段支持前端
    type = fields.String(required=True, validate=validate.OneOf([
        'teaching', 'review', 'debate', 'discussion', 'interview', 'other'
    ]))
    description = fields.String(validate=validate.Length(max=1000))
    version = fields.String(validate=validate.Length(max=20))
    is_active = fields.Boolean()
    termination_config = fields.Dict()  # 结束条件配置
    steps = fields.List(fields.Nested(FlowStepSchema()), required=False)  # 步骤列表，前端允许为空

    @validates('name')
    def validate_name(self, value):
        """验证模板名称唯一性"""
        from app.models import FlowTemplate
        if FlowTemplate.query.filter_by(name=value).first():
            raise ValidationError('流程模板名称已存在')


class FlowTemplateUpdateSchema(Schema):
    """流程模板更新模式，完全适配前端FlowTemplateRequest结构"""
    name = fields.String(validate=validate.Length(min=1, max=200))
    topic = fields.String(validate=validate.Length(max=200))  # 添加topic字段支持前端
    type = fields.String(validate=validate.OneOf([
        'teaching', 'review', 'debate', 'discussion', 'interview', 'other'
    ]))
    description = fields.String(validate=validate.Length(max=1000))
    version = fields.String(validate=validate.Length(max=20))
    is_active = fields.Boolean()
    termination_config = fields.Dict()  # 结束条件配置
    steps = fields.List(fields.Nested(FlowStepSchema()))  # 步骤列表，更新时可选

    @validates('name')
    def validate_name(self, value):
        """验证模板名称唯一性（更新时）"""
        from app.models import FlowTemplate
        flow_template_id = self.context.get('flow_template_id')
        if flow_template_id:
            if FlowTemplate.query.filter(
                FlowTemplate.name == value,
                FlowTemplate.id != flow_template_id
            ).first():
                raise ValidationError('流程模板名称已存在')
        else:
            if FlowTemplate.query.filter_by(name=value).first():
                raise ValidationError('流程模板名称已存在')


class FlowCopySchema(Schema):
    """流程模板复制模式"""
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(validate=validate.Length(max=1000))

    @validates('name')
    def validate_name(self, value):
        """验证新模板名称唯一性"""
        from app.models import FlowTemplate
        if FlowTemplate.query.filter_by(name=value).first():
            raise ValidationError('模板名称已存在')