# 流程模板API模块（第三阶段实现）
from flask import request, current_app
from flask_restful import Resource
from app import db
from app.services.flow_service import FlowTemplateService, FlowTemplateError, TemplateNotFoundError, DuplicateTemplateNameError, StepValidationError
from app.schemas import FlowTemplateSchema, FlowTemplateListSchema, FlowStepSchema
from app.schemas.flow_request import FlowTemplateCreateSchema, FlowTemplateUpdateSchema, FlowCopySchema
import json


class FlowList(Resource):
    """流程模板列表资源"""

    def get(self):
        """获取流程模板列表"""
        try:
            # 查询参数
            page = request.args.get('page', 1, type=int)
            page_size = min(request.args.get('page_size', current_app.config['DEFAULT_PAGE_SIZE'], type=int),
                           current_app.config['MAX_PAGE_SIZE'])
            search = request.args.get('search', '', type=str)
            template_type = request.args.get('type', '', type=str)
            is_active = request.args.get('is_active', '', type=str)

            # 处理布尔值参数
            is_active_filter = None
            if is_active.lower() == 'true':
                is_active_filter = True
            elif is_active.lower() == 'false':
                is_active_filter = False

            # 调用服务层获取数据
            result = FlowTemplateService.get_templates_list(
                page=page,
                page_size=page_size,
                search=search,
                template_type=template_type,
                is_active=is_active_filter
            )

            # 序列化结果
            flow_schema = FlowTemplateSchema(many=True, exclude=('steps',))
            flows_data = flow_schema.dump(result['templates'])

            return {
                'success': True,
                'data': {
                    'flows': flows_data,
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'pages': result['pages']
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取流程模板列表失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取流程模板列表失败'
            }, 500

    def post(self):
        """创建新的流程模板"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            create_schema = FlowTemplateCreateSchema()
            try:
                data = create_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 调用服务层创建模板
            template = FlowTemplateService.create_template(json_data)

            # 返回创建的模板信息
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(template)
            return {
                'success': True,
                'data': result,
                'message': '流程模板创建成功'
            }, 201

        except DuplicateTemplateNameError as e:
            return {
                'success': False,
                'error_code': 'DUPLICATE_NAME',
                'message': str(e)
            }, 400

        except StepValidationError as e:
            return {
                'success': False,
                'error_code': 'STEP_VALIDATION_ERROR',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"创建流程模板失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '创建流程模板失败'
            }, 500


class FlowDetail(Resource):
    """流程模板详情资源"""

    def get(self, flow_id):
        """获取流程模板详情"""
        try:
            template = FlowTemplateService.get_template_by_id(flow_id, include_steps=True)
            if not template:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '流程模板不存在'
                }, 404

            # 序列化结果，包含步骤信息
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(template)

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            current_app.logger.error(f"获取流程模板详情失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取流程模板详情失败'
            }, 500

    def put(self, flow_id):
        """更新流程模板"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            update_schema = FlowTemplateUpdateSchema(context={'flow_template_id': flow_id})
            try:
                data = update_schema.load(json_data, partial=True)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 调用服务层更新模板
            template = FlowTemplateService.update_template(flow_id, json_data)

            # 返回更新后的模板信息
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(template)
            return {
                'success': True,
                'data': result,
                'message': '流程模板更新成功'
            }

        except TemplateNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except DuplicateTemplateNameError as e:
            return {
                'success': False,
                'error_code': 'DUPLICATE_NAME',
                'message': str(e)
            }, 400

        except StepValidationError as e:
            return {
                'success': False,
                'error_code': 'STEP_VALIDATION_ERROR',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"更新流程模板失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '更新流程模板失败'
            }, 500

    def delete(self, flow_id):
        """删除流程模板"""
        try:
            FlowTemplateService.delete_template(flow_id, soft_delete=True)

            return {
                'success': True,
                'message': '流程模板删除成功'
            }

        except TemplateNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except Exception as e:
            current_app.logger.error(f"删除流程模板失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '删除流程模板失败'
            }, 500


class FlowCopy(Resource):
    """流程模板复制资源"""

    def post(self, flow_id):
        """复制流程模板"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            copy_schema = FlowCopySchema()
            try:
                data = copy_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            new_name = json_data['name']
            description = json_data.get('description')

            # 调用服务层复制模板
            new_template = FlowTemplateService.duplicate_template(flow_id, new_name, description)

            # 返回复制后的模板信息
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(new_template)

            return {
                'success': True,
                'data': result,
                'message': '流程模板复制成功'
            }, 201

        except TemplateNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except DuplicateTemplateNameError as e:
            return {
                'success': False,
                'error_code': 'DUPLICATE_NAME',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"复制流程模板失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '复制流程模板失败'
            }, 500


class FlowStatistics(Resource):
    """流程模板统计资源"""

    def get(self):
        """获取流程模板统计信息"""
        try:
            stats = FlowTemplateService.get_template_statistics()

            return {
                'success': True,
                'data': stats
            }

        except Exception as e:
            current_app.logger.error(f"获取流程模板统计失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取流程模板统计失败'
            }, 500