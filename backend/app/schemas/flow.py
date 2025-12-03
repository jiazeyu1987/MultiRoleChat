from marshmallow import Schema, fields, validate, validates, ValidationError
import json


class FlowStepSchema(Schema):
    """流程步骤 Schema，适配前端数据结构与后端模型"""

    id = fields.Integer(dump_only=True)
    flow_template_id = fields.Integer(dump_only=True)
    order = fields.Integer(required=True, validate=validate.Range(min=1))
    speaker_role_ref = fields.String(required=True, validate=validate.Length(min=1, max=50))
    target_role_ref = fields.String(validate=validate.Length(max=50))

    # 任务类型（前端已做校验，这里不再限制具体枚举，统一走服务层验证）
    task_type = fields.String(required=True)

    # 支持字符串或数组格式的上下文范围
    context_scope = fields.Raw(required=True)

    # 下列字段在数据库中以 JSON 字符串存储，通过属性映射为字典，避免 Dict 字段直接处理字符串
    context_param = fields.Dict(attribute='context_param_dict')
    logic_config = fields.Dict(attribute='logic_config_dict')
    loop_config = fields.Dict(attribute='loop_config_dict')
    condition_config = fields.Dict(attribute='condition_config_dict')

    next_step_id = fields.Integer(allow_none=True)
    description = fields.String(validate=validate.Length(max=500))

    def load(self, data, **kwargs):
        """重写 load，用于适配前端数据格式（主要处理 context_scope 及旧字段合并逻辑）"""
        try:
            if isinstance(data, dict):
                # 处理 context_scope 字段：支持字符串 / 数组 / 对象
                if 'context_scope' in data:
                    context_scope = data['context_scope']
                    if isinstance(context_scope, (list, dict)):
                        # 前端传数组或对象时，序列化为 JSON 字符串存库
                        data['context_scope'] = json.dumps(context_scope, ensure_ascii=False)
                    else:
                        # 其它情况统一转成字符串
                        data['context_scope'] = str(context_scope) if context_scope is not None else None

                # 如果只有旧字段 loop_config / condition_config 而没有 logic_config，则合并到 logic_config
                if 'logic_config' not in data and ('loop_config' in data or 'condition_config' in data):
                    logic_config: dict = {}

                    loop_cfg = data.get('loop_config')
                    if isinstance(loop_cfg, dict):
                        logic_config.update(loop_cfg)

                    cond_cfg = data.get('condition_config')
                    if isinstance(cond_cfg, dict):
                        logic_config.update(cond_cfg)

                    data['logic_config'] = logic_config

            return super().load(data, **kwargs)
        except Exception as e:
            # 记录详细错误信息，便于排查
            import logging
            logging.error(f"FlowStepSchema.load() 处理数据时发生错误: {e}")
            logging.error(f"输入数据: {data}")
            logging.error(f"错误类型: {type(e)}")
            raise ValidationError(f"数据处理失败: {str(e)}")

    @validates('context_param')
    def validate_context_param(self, value):
        """验证上下文参数必须为字典"""
        if value and not isinstance(value, dict):
            raise ValidationError('上下文参数必须是字典格式')


class FlowTemplateSchema(Schema):
    """流程模板 Schema，适配前端数据结构与后端模型"""

    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    topic = fields.String(validate=validate.Length(max=200))
    type = fields.String(
        required=True,
        validate=validate.OneOf(['teaching', 'review', 'debate', 'discussion', 'interview', 'other'])
    )
    description = fields.String(validate=validate.Length(max=1000))
    version = fields.String(validate=validate.Length(max=20))
    is_active = fields.Boolean()

    # 终止条件配置，同样在数据库中以 JSON 字符串存储，这里映射为字典
    termination_config = fields.Dict(attribute='termination_config_dict')

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
