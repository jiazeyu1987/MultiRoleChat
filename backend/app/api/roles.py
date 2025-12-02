from flask import request, current_app
from flask_restful import Resource
from app import db
from app.models import Role
from app.schemas import RoleSchema, RoleListSchema
from sqlalchemy import or_


class RoleList(Resource):
    """角色列表资源"""

    def get(self):
        """获取角色列表"""
        try:
            # 查询参数
            page = request.args.get('page', 1, type=int)
            page_size = min(request.args.get('page_size', current_app.config['DEFAULT_PAGE_SIZE'], type=int),
                           current_app.config['MAX_PAGE_SIZE'])
            search = request.args.get('search', '', type=str)

            # 构建查询
            query = Role.query

            # 搜索过滤
            if search:
                query = query.filter(
                    or_(Role.name.contains(search),
                        Role.prompt.contains(search))
                )

        
            # 分页查询
            pagination = query.order_by(Role.created_at.desc()).paginate(
                page=page, per_page=page_size, error_out=False
            )

            # 序列化结果
            role_schema = RoleSchema(many=True)
            roles_data = role_schema.dump(pagination.items)

            return {
                'success': True,
                'data': {
                    'roles': roles_data,
                    'total': pagination.total,
                    'page': page,
                    'page_size': page_size,
                    'pages': pagination.pages
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取角色列表失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取角色列表失败'
            }, 500

    def post(self):
        """创建新角色"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            role_schema = RoleSchema()
            try:
                data = role_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 检查角色名称是否已存在
            if Role.query.filter_by(name=data['name']).first():
                return {
                    'success': False,
                    'error_code': 'DUPLICATE_NAME',
                    'message': '角色名称已存在'
                }, 400

            # 创建角色
            role = Role(
                name=data['name'],
                prompt=data['prompt']
            )

            db.session.add(role)
            db.session.commit()

            # 返回创建的角色信息
            result = role_schema.dump(role)
            return {
                'success': True,
                'data': result,
                'message': '角色创建成功'
            }, 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"创建角色失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '创建角色失败'
            }, 500


class RoleDetail(Resource):
    """角色详情资源"""

    def get(self, role_id):
        """获取角色详情"""
        try:
            role = Role.query.get(role_id)
            if not role:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '角色不存在'
                }, 404

            role_schema = RoleSchema()
            result = role_schema.dump(role)

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            current_app.logger.error(f"获取角色详情失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取角色详情失败'
            }, 500

    def put(self, role_id):
        """更新角色"""
        try:
            role = Role.query.get(role_id)
            if not role:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '角色不存在'
                }, 404

          
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            role_schema = RoleSchema(context={'role_id': role_id})
            try:
                data = role_schema.load(json_data, partial=True)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 更新角色信息
            for field in ['name', 'prompt']:
                if field in data:
                    setattr(role, field, data[field])

            db.session.commit()

            # 返回更新后的角色信息
            result = role_schema.dump(role)
            return {
                'success': True,
                'data': result,
                'message': '角色更新成功'
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"更新角色失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '更新角色失败'
            }, 500

    def delete(self, role_id):
        """删除角色"""
        try:
            role = Role.query.get(role_id)
            if not role:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '角色不存在'
                }, 404

            
            # 检查角色是否被会话使用
            from app.models import SessionRole
            if SessionRole.query.filter_by(role_id=role_id).first():
                return {
                    'success': False,
                    'error_code': 'IN_USE',
                    'message': '角色正在被会话使用，无法删除'
                }, 400

            db.session.delete(role)
            db.session.commit()

            return {
                'success': True,
                'message': '角色删除成功'
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"删除角色失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '删除角色失败'
            }, 500