import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import or_, and_
from flask import current_app
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
            # 直接使用前端数据，让数据库处理默认值
            template_info = {
                'name': template_data['name'],
                'type': template_data['type']
            }

            # 添加可选字段，如果存在则使用
            optional_fields = ['topic', 'description', 'version', 'is_active', 'termination_config']
            for field in optional_fields:
                if field in template_data:
                    if field == 'termination_config':
                        # 特殊处理termination_config
                        pass  # 在创建对象后设置
                    else:
                        template_info[field] = template_data[field]

            current_app.logger.info(f"模板基本信息: {json.dumps(template_info, ensure_ascii=False, indent=2)}")

            # 创建模板
            template = FlowTemplate(**template_info)

            # 设置termination_config
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
        创建模板步骤 - 简化版本，直接使用前端格式

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

        # 直接创建步骤对象，模型属性会自动处理JSON序列化
        steps = []
        for step_data in steps_data:
            step = FlowStep(
                flow_template_id=template_id,
                order=step_data['order'],
                speaker_role_ref=step_data['speaker_role_ref'],
                target_role_ref=step_data.get('target_role_ref'),
                task_type=step_data['task_type'],
                context_scope=step_data['context_scope'],  # 属性会自动处理JSON
                context_param=step_data.get('context_param'),   # 属性会自动处理JSON
                logic_config=step_data.get('logic_config'),     # 属性会自动处理JSON
                next_step_id=step_data.get('next_step_id'),
                description=step_data.get('description')
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
        valid_task_types = [
            'ask_question', 'answer_question', 'review_answer', 'question',
            'summarize', 'evaluate', 'suggest', 'challenge', 'support', 'conclude',
            # 兼容前端使用的 comment 类型（作为泛化“点评/评论”任务）
            'comment',
        ]
        # 引擎直接识别的基础上下文范围
        base_context_scopes = ['none', 'last_message', 'last_round', 'last_n_messages', 'all']
        # 系统级特殊上下文（例如只使用预设议题）
        system_context_scopes = ['__TOPIC__']

        for step in steps_data:
            # 检查必要字段
            for field in required_fields:
                if field not in step:
                    raise StepValidationError(f"步骤缺少必要字段: {field}")

            # 验证任务类型
            if step['task_type'] not in valid_task_types:
                raise StepValidationError(f"无效的任务类型: {step['task_type']}")

            # 验证上下文范围
            scope = step['context_scope']

            # 1) 基础枚举范围或系统特殊值，直接通过
            if scope in base_context_scopes or scope in system_context_scopes:
                pass
            else:
                # 2) 允许角色筛选上下文：
                #    - context_scope 为 JSON 字符串的角色名数组: '["RoleA","RoleB"]'
                #    - 或普通的非空字符串（单个角色名），具体角色是否存在由执行引擎在运行时判断
                is_valid_scope = False

                if isinstance(scope, str):
                    # 尝试解析为 JSON 数组（多角色）
                    try:
                        parsed = json.loads(scope)
                    except Exception:
                        parsed = None

                    if isinstance(parsed, list) and parsed:
                        # 要求数组元素都是非空字符串
                        if all(isinstance(name, str) and name.strip() for name in parsed):
                            is_valid_scope = True
                    else:
                        # 非 JSON 字符串时，只要是非空字符串即可视为单角色名
                        if scope.strip():
                            is_valid_scope = True
                elif isinstance(scope, list) and scope:
                    # 兼容直接传入数组的情况
                    if all(isinstance(name, str) and name.strip() for name in scope):
                        is_valid_scope = True

                if not is_valid_scope:
                    raise StepValidationError(f"无效的上下文范围: {scope}")

            # 验证上下文参数：last_n_messages 必须提供 context_param.n
            if scope == 'last_n_messages':
                ctx_param = step.get('context_param')
                if not isinstance(ctx_param, dict) or 'n' not in ctx_param:
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

    @staticmethod
    def clear_all_templates() -> Dict[str, int]:
        """
        删除所有流程模板和步骤

        Returns:
            Dict: 删除统计信息
        """
        # 获取当前数据统计
        template_count = FlowTemplate.query.count()
        step_count = FlowStep.query.count()

        if template_count == 0:
            return {
                'deleted_templates': 0,
                'deleted_steps': 0
            }

        try:
            # 先删除所有步骤（由于外键约束，必须先删除子表）
            deleted_steps = FlowStep.query.delete()

            # 再删除所有模板
            deleted_templates = FlowTemplate.query.delete()

            # 提交更改
            db.session.commit()

            current_app.logger.info(f"已删除 {deleted_templates} 个模板和 {deleted_steps} 个步骤")

            return {
                'deleted_templates': deleted_templates,
                'deleted_steps': deleted_steps
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"删除所有模板时发生错误: {str(e)}")
            raise
