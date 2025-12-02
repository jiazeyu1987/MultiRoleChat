# 会话管理API模块（第四阶段实现）
from flask import request, current_app
from flask_restful import Resource
from app import db
from datetime import datetime
from app.services.session_service import SessionService, SessionError, SessionNotFoundError, InvalidSessionStateError
from app.services.flow_engine_service import FlowEngineService, FlowExecutionError
from app.schemas import SessionSchema, SessionListSchema, SessionRoleSchema
from app.schemas.session_request import (
    CreateSessionSchema, UpdateSessionSchema, SessionControlSchema,
    CreateBranchSessionSchema, SessionExecutionSchema
)
import json


class SessionList(Resource):
    """会话列表资源"""

    def get(self):
        """获取会话列表"""
        try:
            # 查询参数
            page = request.args.get('page', 1, type=int)
            page_size = min(request.args.get('page_size', current_app.config['DEFAULT_PAGE_SIZE'], type=int),
                           current_app.config['MAX_PAGE_SIZE'])
            search = request.args.get('search', '', type=str)
            status = request.args.get('status', '', type=str)
            user_id = request.args.get('user_id', type=int)

            # 调用服务层获取数据
            result = SessionService.get_sessions_list(
                page=page,
                page_size=page_size,
                search=search,
                status=status,
                user_id=user_id
            )

            # 序列化结果
            session_schema = SessionSchema(many=True, exclude=('session_roles', 'flow_snapshot', 'roles_snapshot'))
            sessions_data = session_schema.dump(result['sessions'])

            return {
                'success': True,
                'data': {
                    'sessions': sessions_data,
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'pages': result['pages']
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取会话列表失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取会话列表失败'
            }, 500

    def post(self):
        """创建新会话"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            create_schema = CreateSessionSchema()
            try:
                data = create_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 调用服务层创建会话
            session = SessionService.create_session(json_data)

            # 返回创建的会话信息
            session_schema = SessionSchema()
            result = session_schema.dump(session)

            return {
                'success': True,
                'data': result,
                'message': '会话创建成功'
            }, 201

        except SessionError as e:
            return {
                'success': False,
                'error_code': 'SESSION_ERROR',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"创建会话失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '创建会话失败'
            }, 500


class SessionDetail(Resource):
    """会话详情资源"""

    def get(self, session_id):
        """获取会话详情"""
        try:
            session = SessionService.get_session_by_id(session_id, include_roles=True)
            if not session:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '会话不存在'
                }, 404

            # 序列化结果
            session_schema = SessionSchema()
            result = session_schema.dump(session)

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            current_app.logger.error(f"获取会话详情失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取会话详情失败'
            }, 500

    def put(self, session_id):
        """更新会话"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            update_schema = UpdateSessionSchema()
            try:
                data = update_schema.load(json_data, partial=True)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 检查会话是否存在
            session = SessionService.get_session_by_id(session_id)
            if not session:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '会话不存在'
                }, 404

            # 更新会话
            for field in ['topic', 'status']:
                if field in json_data:
                    setattr(session, field, json_data[field])

            session.updated_at = datetime.utcnow()
            db.session.commit()

            # 返回更新后的会话信息
            session_schema = SessionSchema()
            result = session_schema.dump(session)

            return {
                'success': True,
                'data': result,
                'message': '会话更新成功'
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"更新会话失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '更新会话失败'
            }, 500

    def delete(self, session_id):
        """删除会话"""
        try:
            session = SessionService.get_session_by_id(session_id)
            if not session:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '会话不存在'
                }, 404

            # 检查会话状态，正在运行的会话不能删除
            if session.status == 'running':
                return {
                    'success': False,
                    'error_code': 'INVALID_STATE',
                    'message': '正在运行的会话不能删除，请先暂停或结束会话'
                }, 400

            db.session.delete(session)
            db.session.commit()

            return {
                'success': True,
                'message': '会话删除成功'
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"删除会话失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '删除会话失败'
            }, 500


class SessionExecution(Resource):
    """会话执行资源"""

    def post(self, session_id):
        """执行会话下一步骤"""
        try:
            json_data = request.get_json() or {}

            # 数据验证
            execution_schema = SessionExecutionSchema()
            try:
                data = execution_schema.load(json_data, partial=True)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 检查会话是否可执行
            if not SessionService.is_session_executable(session_id):
                return {
                    'success': False,
                    'error_code': 'NOT_EXECUTABLE',
                    'message': '会话当前状态不允许执行步骤'
                }, 400

            # 执行下一步骤
            message, execution_info = FlowEngineService.execute_next_step(session_id)

            # 序列化结果
            from app.schemas import MessageSchema
            message_schema = MessageSchema()
            message_data = message_schema.dump(message)

            return {
                'success': True,
                'data': {
                    'message': message_data,
                    'execution_info': execution_info
                },
                'message': '步骤执行成功'
            }

        except SessionNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except FlowExecutionError as e:
            return {
                'success': False,
                'error_code': 'FLOW_EXECUTION_ERROR',
                'message': str(e)
            }, 400

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"执行会话步骤失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '执行会话步骤失败'
            }, 500


class SessionControl(Resource):
    """会话控制资源"""

    def post(self, session_id):
        """控制会话状态（开始、暂停、恢复、结束）"""
        try:
            json_data = request.get_json()
            if not json_data or 'action' not in json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体必须包含action字段'
                }, 400

            # 数据验证
            control_schema = SessionControlSchema()
            try:
                data = control_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            action = data['action']
            reason = data.get('reason')

            # 执行相应的控制操作
            if action == 'start':
                session = SessionService.start_session(session_id)
                message = '会话开始成功'

            elif action == 'pause':
                session = SessionService.pause_session(session_id)
                message = '会话暂停成功'

            elif action == 'resume':
                session = SessionService.resume_session(session_id)
                message = '会话恢复成功'

            elif action == 'finish':
                session = SessionService.finish_session(session_id, reason)
                message = '会话结束成功'

            else:
                return {
                    'success': False,
                    'error_code': 'INVALID_ACTION',
                    'message': f'不支持的操作: {action}'
                }, 400

            # 返回更新后的会话信息
            session_schema = SessionSchema()
            result = session_schema.dump(session)

            return {
                'success': True,
                'data': result,
                'message': message
            }

        except SessionNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except InvalidSessionStateError as e:
            return {
                'success': False,
                'error_code': 'INVALID_STATE',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"控制会话失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '控制会话失败'
            }, 500


class SessionBranch(Resource):
    """会话分支资源"""

    def post(self, session_id):
        """创建分支会话"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 数据验证
            branch_schema = CreateBranchSessionSchema()
            try:
                data = branch_schema.load(json_data)
            except Exception as e:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'message': '数据验证失败',
                    'details': str(e)
                }, 400

            # 创建分支会话
            branch_session = SessionService.create_branch_session(
                session_id,
                data['branch_point_message_id'],
                data.get('new_topic')
            )

            # 返回分支会话信息
            session_schema = SessionSchema()
            result = session_schema.dump(branch_session)

            return {
                'success': True,
                'data': result,
                'message': '分支会话创建成功'
            }, 201

        except SessionNotFoundError as e:
            return {
                'success': False,
                'error_code': 'NOT_FOUND',
                'message': str(e)
            }, 404

        except Exception as e:
            current_app.logger.error(f"创建分支会话失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '创建分支会话失败'
            }, 500


class SessionStatistics(Resource):
    """会话统计资源"""

    def get(self):
        """获取会话统计信息"""
        try:
            stats = SessionService.get_session_statistics()

            return {
                'success': True,
                'data': stats
            }

        except Exception as e:
            current_app.logger.error(f"获取会话统计失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取会话统计失败'
            }, 500