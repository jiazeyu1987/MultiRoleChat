from marshmallow import Schema, fields, validate, validates, ValidationError


class FlowStepSchema(Schema):
    """流程步骤模式"""
    id = fields.Integer(dump_only=True)
    flow_template_id = fields.Integer(dump_only=True)
    order = fields.Integer(required=True, validate=validate.Range(min=1))
    speaker_role_ref = fields.String(required=True, validate=validate.Length(min=1, max=50))
    target_role_ref = fields.String(validate=validate.Length(max=50))
    task_type = fields.String(required=True, validate=validate.OneOf([
        'ask_question', 'answer_question', 'review_answer', 'question', 'summarize',
        'evaluate', 'suggest', 'challenge', 'support', 'conclude'
    ]))
    context_scope = fields.String(required=True)
    context_param = fields.Dict()  # 上下文参数，如 {"n": 5} for last_n_messages
    loop_config = fields.Dict()  # 循环配置
    condition_config = fields.Dict()  # 条件配置
    next_step_id = fields.Integer(allow_none=True)
    description = fields.String(validate=validate.Length(max=500))

    @validates('context_param')
    def validate_context_param(self, value):
        """验证上下文参数"""
        if value and not isinstance(value, dict):
            raise ValidationError('上下文参数必须是字典格式')


class FlowTemplateSchema(Schema):
    """流程模板模式"""
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    type = fields.String(required=True, validate=validate.OneOf([
        'teaching', 'review', 'debate', 'discussion', 'interview', 'other'
    ]))
    description = fields.String(validate=validate.Length(max=1000))
    version = fields.String(validate=validate.Length(max=20))
    is_active = fields.Boolean()
    termination_config = fields.Dict()  # 结束条件配置
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    steps = fields.List(fields.Nested(FlowStepSchema()), dump_only=True)
    step_count = fields.Integer(dump_only=True)

    @validates('name')
    def validate_name(self, value):
        """验证模板名称唯一性"""
        from app.models import FlowTemplate
        if self.context.get('flow_template_id'):  # 更新场景
            if FlowTemplate.query.filter(
                FlowTemplate.name == value,
                FlowTemplate.id != self.context['flow_template_id']
            ).first():
                raise ValidationError('流程模板名称已存在')
        else:  # 创建场景
            if FlowTemplate.query.filter_by(name=value).first():
                raise ValidationError('流程模板名称已存在')


class FlowTemplateListSchema(Schema):
    """流程模板列表模式"""
    flows = fields.List(fields.Nested(FlowTemplateSchema(exclude=('steps',))))
    total = fields.Integer()
    page = fields.Integer()
    page_size = fields.Integer()