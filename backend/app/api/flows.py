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
            current_app.logger.info("=== 创建流程模板开始 ===")

            json_data = request.get_json()
            current_app.logger.info(f"原始请求数据: {json.dumps(json_data, ensure_ascii=False, indent=2)}")

            if not json_data:
                current_app.logger.error("请求体为空")
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            create_schema = FlowTemplateCreateSchema()
            try:
                data = create_schema.load(json_data)
                current_app.logger.info(f"Schema验证后数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except Exception as e:
                current_app.logger.error(f"数据验证失败: {str(e)}")
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 调用服务层创建模板
            current_app.logger.info(f"调用服务层创建模板: FlowTemplateService.create_template()")
            template = FlowTemplateService.create_template(data)  # 使用验证后的数据

            # 直接返回模板数据，移除包装层
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(template)
            current_app.logger.info(f"服务层返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

            current_app.logger.info("=== 创建流程模板完成 ===")
            return {
                'success': True,
                'data': result,
                'message': '流程模板创建成功'
            }, 201

        except DuplicateTemplateNameError as e:
            current_app.logger.error(f"创建流程模板失败: {str(e)}")
            return {'error': str(e)}, 400

        except StepValidationError as e:
            current_app.logger.error(f"创建流程模板失败: {str(e)}")
            return {'error': str(e)}, 400

        except Exception as e:
            current_app.logger.error(f"创建流程模板失败: {str(e)}")
            return {'error': '创建流程模板失败'}, 500


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
            current_app.logger.info("FlowDetail response data: %s", json.dumps(result, ensure_ascii=False))

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
            current_app.logger.info(f"=== 更新流程模板开始 (ID: {flow_id}) ===")

            json_data = request.get_json()
            current_app.logger.info(f"原始请求数据: {json.dumps(json_data, ensure_ascii=False, indent=2)}")

            if not json_data:
                current_app.logger.error("请求体为空")
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            update_schema = FlowTemplateUpdateSchema(context={'flow_template_id': flow_id})
            try:
                data = update_schema.load(json_data, partial=True)
                current_app.logger.info(f"Schema验证后数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except Exception as e:
                current_app.logger.error(f"数据验证失败: {str(e)}")
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 调用服务层更新模板
            current_app.logger.info(f"调用服务层更新模板: FlowTemplateService.update_template()")
            template = FlowTemplateService.update_template(flow_id, data)  # 使用验证后的数据

            # 返回更新后的模板信息
            flow_schema = FlowTemplateSchema()
            result = flow_schema.dump(template)
            current_app.logger.info(f"服务层返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

            current_app.logger.info("=== 更新流程模板完成 ===")
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


class FlowClearAll(Resource):
    """删除所有流程模板资源"""

    def delete(self):
        """删除所有流程模板和步骤"""
        try:
            # 调用服务层删除所有模板
            result = FlowTemplateService.clear_all_templates()

            current_app.logger.info(f"已删除 {result['deleted_templates']} 个模板和 {result['deleted_steps']} 个步骤")

            return {
                'success': True,
                'message': f'成功删除 {result["deleted_templates"]} 个模板和 {result["deleted_steps"]} 个步骤',
                'data': {
                    'deleted_templates': result['deleted_templates'],
                    'deleted_steps': result['deleted_steps']
                }
            }

        except Exception as e:
            current_app.logger.error(f"删除所有流程模板失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '删除所有流程模板失败'
            }, 500
