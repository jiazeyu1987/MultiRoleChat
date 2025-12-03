import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import or_, and_
from app import db
from app.models import FlowTemplate, FlowStep, Role


class FlowTemplateError(Exception):
    """流程模板相关错误的基类"""
    pass


class StepValidationError(FlowTemplateError):
    """步骤验证错误"""
    pass


class TemplateNotFoundError(FlowTemplateError):
    """模板不存在错误"""
    pass


class DuplicateTemplateNameError(FlowTemplateError):
    """模板名称重复错误"""
    pass


class FlowTemplateService:
    """流程模板服务类"""

    @staticmethod
    def create_template(template_data: Dict[str, Any], user_id: Optional[int] = None) -> FlowTemplate:
        """
        创建新的流程模板，完全适配前端数据结构

        Args:
            template_data: 模板数据，包含基本信息和步骤列表（前端FlowTemplateRequest格式）
            user_id: 创建者ID（暂未实现用户系统）

        Returns:
            FlowTemplate: 创建的模板对象

        Raises:
            DuplicateTemplateNameError: 模板名称已存在
            StepValidationError: 步骤验证失败
        """
        from flask import current_app
        import json

        current_app.logger.info(f"create_template() - 开始处理模板: {template_data.get('name')}")

        # 检查模板名称是否已存在
        existing_template = FlowTemplate.query.filter_by(name=template_data['name']).first()
        if existing_template:
            current_app.logger.error(f"模板名称已存在: {template_data['name']}")
            raise DuplicateTemplateNameError(f"模板名称 '{template_data['name']}' 已存在")

        try:
            # 提取模板基本信息
            template_info = {
                'name': template_data['name'],
                'type': template_data['type'],
                'description': template_data.get('description', ''),
                'version': template_data.get('version', '1.0.0'),
                'is_active': template_data.get('is_active', True)
            }

            # 添加topic字段支持前端
            if 'topic' in template_data:
                template_info['topic'] = template_data['topic']

            current_app.logger.info(f"模板基本信息: {json.dumps(template_info, ensure_ascii=False, indent=2)}")

            # 创建模板
            template = FlowTemplate(**template_info)

            # 设置结束条件配置
            if 'termination_config' in template_data:
                template.termination_config_dict = template_data['termination_config']

            db.session.add(template)
            db.session.flush()  # 获取模板ID

            current_app.logger.info(f"数据库插入成功 - 模板ID: {template.id}")

            # 创建步骤（如果有）
            steps_data = template_data.get('steps', [])
            if steps_data:
                current_app.logger.info(f"步骤数据: {json.dumps(steps_data, ensure_ascii=False, indent=2)}")
                FlowTemplateService._create_template_steps(template.id, steps_data)

            db.session.commit()
            current_app.logger.info("模板创建完成")
            return template

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"创建模板失败: {str(e)}")
            if isinstance(e, FlowTemplateError):
                raise
            raise FlowTemplateError(f"创建模板失败: {str(e)}")

    @staticmethod
    def _create_template_steps(template_id: int, steps_data: List[Dict[str, Any]]) -> None:
        """
        创建模板步骤，完全适配前端数据结构

        Args:
            template_id: 模板ID
            steps_data: 步骤数据列表（前端FlowStep格式）

        Raises:
            StepValidationError: 步骤验证失败
        """
        from flask import current_app

        current_app.logger.info(f"_create_template_steps() - 开始创建步骤，模板ID: {template_id}")

        # 验证步骤数据
        FlowTemplateService._validate_steps_data(steps_data)

        steps = []
        for index, step_data in enumerate(steps_data):
            current_app.logger.info(f"处理步骤 {index + 1}: {step_data.get('speaker_role_ref')}")

            # 处理context_scope字段：支持字符串或数组格式
            context_scope = step_data.get('context_scope')
            if isinstance(context_scope, (list, dict)):
                # 如果是数组或对象，转换为JSON字符串存储
                context_scope = json.dumps(context_scope, ensure_ascii=False)
            else:
                # 如果是字符串，直接使用
                context_scope = str(context_scope) if context_scope is not None else ''

            # 处理logic_config字段：适配前端logic_config，并确保为字典
            logic_config = step_data.get('logic_config') or {}
            if not isinstance(logic_config, dict):
                # 如果是字符串或其他可解析为JSON的格式，尝试解析一次
                try:
                    if isinstance(logic_config, str):
                        parsed = json.loads(logic_config)
                        logic_config = parsed if isinstance(parsed, dict) else {}
                    else:
                        # 尝试从(key, value)序列构造，失败则忽略
                        logic_config = dict(logic_config)  # type: ignore[arg-type]
                except Exception:
                    logic_config = {}

            step = FlowStep(
                flow_template_id=template_id,
                order=step_data['order'],
                speaker_role_ref=step_data['speaker_role_ref'],
                target_role_ref=step_data.get('target_role_ref'),
                task_type=step_data['task_type'],  # 扩展支持前端所有类型
                context_scope=context_scope,  # 存储处理后的格式
                context_param_dict=step_data.get('context_param', {}),
                logic_config_dict=logic_config,  # 使用统一的logic_config
                # 保留旧字段以兼容现有数据
                loop_config_dict=step_data.get('loop_config', {}),
                condition_config_dict=step_data.get('condition_config', {}),
                next_step_id=step_data.get('next_step_id'),
                description=step_data.get('description', '')
            )
            steps.append(step)

        current_app.logger.info(f"创建 {len(steps)} 个步骤对象")

        db.session.add_all(steps)

    @staticmethod
    def _validate_steps_data(steps_data: List[Dict[str, Any]]) -> None:
        """
        验证步骤数据

        Args:
            steps_data: 步骤数据列表

        Raises:
            StepValidationError: 步骤验证失败
        """
        if not steps_data:
            raise StepValidationError("步骤列表不能为空")

        # 检查步骤序号是否连续且唯一
        orders = [step['order'] for step in steps_data]
        if len(orders) != len(set(orders)):
            raise StepValidationError("步骤序号不能重复")

        sorted_orders = sorted(orders)
        if sorted_orders != list(range(1, len(sorted_orders) + 1)):
            raise StepValidationError("步骤序号必须从1开始连续递增")

        # 验证每个步骤的必要字段
        required_fields = ['order', 'speaker_role_ref', 'task_type', 'context_scope']
        valid_task_types = ['ask_question', 'answer_question', 'review_answer', 'question',
                           'summarize', 'evaluate', 'suggest', 'challenge', 'support', 'conclude']
        valid_context_scopes = ['none', 'last_message', 'last_round', 'last_n_messages', 'all']

        for step in steps_data:
            # 检查必要字段
            for field in required_fields:
                if field not in step:
                    raise StepValidationError(f"步骤缺少必要字段: {field}")

            # 验证任务类型
            if step['task_type'] not in valid_task_types:
                raise StepValidationError(f"无效的任务类型: {step['task_type']}")

            # 验证上下文范围
            if step['context_scope'] not in valid_context_scopes:
                raise StepValidationError(f"无效的上下文范围: {step['context_scope']}")

            # 验证上下文参数
            if step['context_scope'] == 'last_n_messages' and 'context_param' not in step:
                raise StepValidationError("使用'last_n_messages'时必须提供context_param参数")

    @staticmethod
    def get_template_by_id(template_id: int, include_steps: bool = True) -> Optional[FlowTemplate]:
        """
        根据ID获取模板

        Args:
            template_id: 模板ID
            include_steps: 是否包含步骤信息

        Returns:
            Optional[FlowTemplate]: 模板对象，如果不存在则返回None
        """
        template = FlowTemplate.query.get(template_id)
        if template and include_steps:
            # 预加载步骤信息
            template.steps  # 触发延迟加载
        return template

    @staticmethod
    def get_templates_list(page: int = 1, page_size: int = 20, search: str = '',
                          template_type: str = '', is_active: Optional[bool] = None) -> Dict[str, Any]:
        """
        获取模板列表

        Args:
            page: 页码
            page_size: 每页大小
            search: 搜索关键词
            template_type: 模板类型筛选
            is_active: 是否激活筛选

        Returns:
            Dict: 包含模板列表和分页信息的字典
        """
        query = FlowTemplate.query

        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    FlowTemplate.name.contains(search),
                    FlowTemplate.description.contains(search)
                )
            )

        # 类型过滤
        if template_type:
            query = query.filter(FlowTemplate.type == template_type)

        # 激活状态过滤
        if is_active is not None:
            query = query.filter(FlowTemplate.is_active == is_active)

        # 分页查询
        pagination = query.order_by(FlowTemplate.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'templates': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def update_template(template_id: int, update_data: Dict[str, Any]) -> FlowTemplate:
        """
        更新模板

        Args:
            template_id: 模板ID
            update_data: 更新数据

        Returns:
            FlowTemplate: 更新后的模板对象

        Raises:
            TemplateNotFoundError: 模板不存在
            DuplicateTemplateNameError: 模板名称重复
        """
        template = FlowTemplate.query.get(template_id)
        if not template:
            raise TemplateNotFoundError(f"模板ID {template_id} 不存在")

        try:
            # 检查名称冲突
            if 'name' in update_data and update_data['name'] != template.name:
                if FlowTemplate.query.filter_by(name=update_data['name']).first():
                    raise DuplicateTemplateNameError(f"模板名称 '{update_data['name']}' 已存在")

            # 更新基本信息
            for field in ['name', 'type', 'description', 'version', 'is_active']:
                if field in update_data:
                    setattr(template, field, update_data[field])

            # 更新结束条件配置
            if 'termination_config' in update_data:
                template.termination_config_dict = update_data['termination_config']

            # 更新步骤
            if 'steps' in update_data:
                # 删除现有步骤
                FlowStep.query.filter_by(flow_template_id=template_id).delete()
                # 创建新步骤
                FlowTemplateService._create_template_steps(template_id, update_data['steps'])

            template.updated_at = datetime.utcnow()
            db.session.commit()
            return template

        except Exception as e:
            db.session.rollback()
            if isinstance(e, FlowTemplateError):
                raise
            raise FlowTemplateError(f"更新模板失败: {str(e)}")

    @staticmethod
    def delete_template(template_id: int, soft_delete: bool = True) -> bool:
        """
        删除模板

        Args:
            template_id: 模板ID
            soft_delete: 是否软删除

        Returns:
            bool: 删除是否成功

        Raises:
            TemplateNotFoundError: 模板不存在
        """
        template = FlowTemplate.query.get(template_id)
        if not template:
            raise TemplateNotFoundError(f"模板ID {template_id} 不存在")

        try:
            if soft_delete:
                template.is_active = False
                template.updated_at = datetime.utcnow()
                db.session.commit()
            else:
                # 硬删除：先删除步骤，再删除模板
                FlowStep.query.filter_by(flow_template_id=template_id).delete()
                db.session.delete(template)
                db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            raise FlowTemplateError(f"删除模板失败: {str(e)}")

    @staticmethod
    def duplicate_template(template_id: int, new_name: str, description: str = None) -> FlowTemplate:
        """
        复制模板

        Args:
            template_id: 源模板ID
            new_name: 新模板名称
            description: 新模板描述

        Returns:
            FlowTemplate: 复制的新模板对象

        Raises:
            TemplateNotFoundError: 源模板不存在
            DuplicateTemplateNameError: 新模板名称已存在
        """
        source_template = FlowTemplate.query.get(template_id)
        if not source_template:
            raise TemplateNotFoundError(f"模板ID {template_id} 不存在")

        if FlowTemplate.query.filter_by(name=new_name).first():
            raise DuplicateTemplateNameError(f"模板名称 '{new_name}' 已存在")

        try:
            # 创建新模板
            new_template = FlowTemplate(
                name=new_name,
                type=source_template.type,
                description=description or f"{source_template.description} (副本)",
                version='1.0.0',  # 复制的模板版本重置为1.0.0
                is_active=True,
                termination_config_dict=source_template.termination_config_dict
            )

            db.session.add(new_template)
            db.session.flush()  # 获取新模板ID

            # 复制步骤
            source_steps = FlowStep.query.filter_by(flow_template_id=template_id).all()
            for source_step in source_steps:
                new_step = FlowStep(
                    flow_template_id=new_template.id,
                    order=source_step.order,
                    speaker_role_ref=source_step.speaker_role_ref,
                    target_role_ref=source_step.target_role_ref,
                    task_type=source_step.task_type,
                    context_scope=source_step.context_scope,
                    context_param_dict=source_step.context_param_dict,
                    loop_config_dict=source_step.loop_config_dict,
                    condition_config_dict=source_step.condition_config_dict,
                    next_step_id=source_step.next_step_id,
                    description=source_step.description
                )
                db.session.add(new_step)

            db.session.commit()
            return new_template

        except Exception as e:
            db.session.rollback()
            raise FlowTemplateError(f"复制模板失败: {str(e)}")

    @staticmethod
    def get_template_statistics() -> Dict[str, Any]:
        """
        获取模板统计信息

        Returns:
            Dict: 统计信息字典
        """
        total_templates = FlowTemplate.query.count()
        active_templates = FlowTemplate.query.filter_by(is_active=True).count()

        # 按类型统计
        type_stats = db.session.query(
            FlowTemplate.type,
            db.func.count(FlowTemplate.id).label('count')
        ).group_by(FlowTemplate.type).all()

        type_distribution = {stat.type: stat.count for stat in type_stats}

        return {
            'total_templates': total_templates,
            'active_templates': active_templates,
            'inactive_templates': total_templates - active_templates,
            'type_distribution': type_distribution
        }
