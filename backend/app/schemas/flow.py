from marshmallow import Schema, fields, validate, validates, ValidationError
import json


class FlowStepSchema(Schema):
    """流程步骤 Schema - 完全匹配前端接口"""

    id = fields.Integer(dump_only=True)
    flow_template_id = fields.Integer(dump_only=True)
    order = fields.Integer(required=True, validate=validate.Range(min=1))
    speaker_role_ref = fields.String(required=True, validate=validate.Length(min=1, max=50))
    target_role_ref = fields.String(allow_none=True, validate=validate.Length(max=50))

    # 严格匹配前端枚举
    task_type = fields.String(
        required=True,
        validate=validate.OneOf([
            'ask_question', 'answer_question', 'review_answer', 'question',
            'summarize', 'evaluate', 'suggest', 'challenge', 'support', 'conclude'
        ])
    )

    # 支持字符串或数组格式的上下文范围 - 与前端接口一致
    context_scope = fields.Raw(required=True, validate=lambda x: x is not None)

    # 直接使用前端格式，模型属性会自动处理JSON序列化
    context_param = fields.Dict(allow_none=True)
    logic_config = fields.Dict(allow_none=True)
    next_step_id = fields.Integer(allow_none=True)
    description = fields.String(allow_none=True, validate=validate.Length(max=500))

    def load(self, data, **kwargs):
        """简化的load方法 - 直接处理前端格式"""
        try:
            if isinstance(data, dict):
                # 自动处理context_scope的JSON序列化
                if 'context_scope' in data:
                    context_scope = data['context_scope']
                    if isinstance(context_scope, (list, dict)):
                        # 数组或对象转换为JSON字符串存储
                        data['context_scope'] = json.dumps(context_scope, ensure_ascii=False)
                    else:
                        # 字符串直接存储
                        data['context_scope'] = str(context_scope) if context_scope is not None else 'all'

            return super().load(data, **kwargs)
        except Exception as e:
            import logging
            logging.error(f"FlowStepSchema.load() 处理数据时发生错误: {e}")
            logging.error(f"输入数据: {data}")
            raise ValidationError(f"数据处理失败: {str(e)}")

    @validates('context_param')
    def validate_context_param(self, value):
        """验证上下文参数必须为字典或None"""
        if value is not None and not isinstance(value, dict):
            raise ValidationError('上下文参数必须是字典格式')


class FlowTemplateSchema(Schema):
    """流程模板 Schema - 完全匹配前端接口"""

    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    topic = fields.String(allow_none=True, validate=validate.Length(max=200))
    type = fields.String(
        required=True,
        validate=validate.OneOf(['teaching', 'review', 'debate', 'discussion', 'interview', 'other'])
    )
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    version = fields.String(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Boolean(allow_none=True)

    # 终止条件配置 - 使用属性映射自动处理JSON序列化
    termination_config = fields.Dict(attribute='termination_config_dict', allow_none=True)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # 步骤列表只在输出时返回
    steps = fields.List(fields.Nested(FlowStepSchema()), dump_only=True)
    step_count = fields.Integer(dump_only=True)

    @validates('name')
    def validate_name(self, value):
        """验证模板名称唯一性（创建和更新场景）"""
        from app.models import FlowTemplate

        # 更新场景：上下文中带有 flow_template_id
        if self.context.get('flow_template_id'):
            tpl_id = self.context['flow_template_id']
            if FlowTemplate.query.filter(
                FlowTemplate.name == value,
                FlowTemplate.id != tpl_id
            ).first():
                raise ValidationError('流程模板名称已存在')
        else:
            # 创建场景：直接检查是否已存在
            if FlowTemplate.query.filter_by(name=value).first():
                raise ValidationError('流程模板名称已存在')


class FlowTemplateListSchema(Schema):
    """流程模板列表 Schema"""

    flows = fields.List(fields.Nested(FlowTemplateSchema(exclude=('steps',))))
    total = fields.Integer()
    page = fields.Integer()
    page_size = fields.Integer()
