# 消息管理API模块（第四阶段实现）
from flask import request, current_app, send_file, Response
from flask_restful import Resource
from app import db
from app.services.message_service import MessageService
from app.schemas import MessageSchema, MessageListSchema
import tempfile
import os


class MessageList(Resource):
    """消息列表资源"""

    def get(self, session_id):
        """获取会话消息列表"""
        try:
            # 查询参数
            page = request.args.get('page', 1, type=int)
            page_size = min(request.args.get('page_size', current_app.config['DEFAULT_PAGE_SIZE'], type=int),
                           current_app.config['MAX_PAGE_SIZE'])
            speaker_role_id = request.args.get('speaker_role_id', type=int)
            target_role_id = request.args.get('target_role_id', type=int)
            round_index = request.args.get('round_index', type=int)
            section = request.args.get('section', type=str)
            keyword = request.args.get('keyword', type=str)
            order_by = request.args.get('order_by', 'created_at', type=str)

            # 调用服务层获取数据
            result = MessageService.get_session_messages(
                session_id=session_id,
                page=page,
                page_size=page_size,
                speaker_role_id=speaker_role_id,
                target_role_id=target_role_id,
                round_index=round_index,
                section=section,
                keyword=keyword,
                order_by=order_by
            )

            # 序列化结果
            message_schema = MessageSchema(many=True)
            messages_data = message_schema.dump(result['messages'])

            return {
                'success': True,
                'data': {
                    'messages': messages_data,
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'pages': result['pages']
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取消息列表失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取消息列表失败'
            }, 500


class MessageDetail(Resource):
    """消息详情资源"""

    def get(self, session_id, message_id):
        """获取消息详情"""
        try:
            message = MessageService.get_message_by_id(message_id)
            if not message or message.session_id != session_id:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '消息不存在或不属于该会话'
                }, 404

            # 序列化结果
            message_schema = MessageSchema()
            result = message_schema.dump(message)

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            current_app.logger.error(f"获取消息详情失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取消息详情失败'
            }, 500

    def put(self, session_id, message_id):
        """更新消息内容"""
        try:
            json_data = request.get_json()
            if not json_data or 'content' not in json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体必须包含content字段'
                }, 400

            content = json_data['content']
            if not content or not content.strip():
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '消息内容不能为空'
                }, 400

            # 更新消息
            updated_message = MessageService.update_message(message_id, content)
            if not updated_message:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '消息不存在'
                }, 404

            # 验证消息属于该会话
            if updated_message.session_id != session_id:
                return {
                    'success': False,
                    'error_code': 'FORBIDDEN',
                    'message': '消息不属于该会话'
                }, 403

            # 序列化结果
            message_schema = MessageSchema()
            result = message_schema.dump(updated_message)

            return {
                'success': True,
                'data': result,
                'message': '消息更新成功'
            }

        except Exception as e:
            current_app.logger.error(f"更新消息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '更新消息失败'
            }, 500

    def delete(self, session_id, message_id):
        """删除消息"""
        try:
            message = MessageService.get_message_by_id(message_id)
            if not message or message.session_id != session_id:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '消息不存在或不属于该会话'
                }, 404

            # 软删除消息
            success = MessageService.delete_message(message_id, soft_delete=True)
            if success:
                return {
                    'success': True,
                    'message': '消息删除成功'
                }
            else:
                return {
                    'success': False,
                    'error_code': 'DELETE_FAILED',
                    'message': '删除消息失败'
                }, 500

        except Exception as e:
            current_app.logger.error(f"删除消息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '删除消息失败'
            }, 500


class MessageExport(Resource):
    """消息导出资源"""

    def get(self, session_id):
        """导出会话消息"""
        try:
            # 获取导出格式
            export_format = request.args.get('format', 'json')
            if export_format not in ['json', 'markdown', 'text']:
                return {
                    'success': False,
                    'error_code': 'INVALID_FORMAT',
                    'message': '不支持的导出格式，支持的格式：json, markdown, text'
                }, 400

            # 导出对话记录
            export_result = MessageService.export_conversation(session_id, export_format)

            if export_format == 'json':
                # JSON格式直接返回
                return {
                    'success': True,
                    'data': export_result
                }
            else:
                # 文本和Markdown格式作为文件下载
                filename = export_result['filename']
                content = export_result['content']

                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w', delete=False,
                                              suffix=os.path.splitext(filename)[1],
                                              encoding='utf-8') as tmp_file:
                    tmp_file.write(content)
                    tmp_file_path = tmp_file.name

                return send_file(
                    tmp_file_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='text/plain' if export_format == 'text' else 'text/markdown'
                )

        except ValueError as e:
            return {
                'success': False,
                'error_code': 'EXPORT_ERROR',
                'message': str(e)
            }, 400

        except Exception as e:
            current_app.logger.error(f"导出消息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '导出消息失败'
            }, 500


class MessageReplies(Resource):
    """消息回复资源"""

    def get(self, session_id, message_id):
        """获取消息的回复"""
        try:
            # 验证原消息存在且属于该会话
            original_message = MessageService.get_message_by_id(message_id)
            if not original_message or original_message.session_id != session_id:
                return {
                    'success': False,
                    'error_code': 'NOT_FOUND',
                    'message': '原消息不存在或不属于该会话'
                }, 404

            # 获取回复消息
            replies = MessageService.get_message_replies(message_id)

            # 序列化结果
            message_schema = MessageSchema(many=True)
            replies_data = message_schema.dump(replies)

            return {
                'success': True,
                'data': {
                    'original_message_id': message_id,
                    'replies': replies_data,
                    'reply_count': len(replies)
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取消息回复失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取消息回复失败'
            }, 500


class MessageStatistics(Resource):
    """消息统计资源"""

    def get(self, session_id=None):
        """获取消息统计信息"""
        try:
            stats = MessageService.get_message_statistics(session_id)

            return {
                'success': True,
                'data': stats
            }

        except Exception as e:
            current_app.logger.error(f"获取消息统计失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取消息统计失败'
            }, 500


class MessageFlow(Resource):
    """对话流程资源"""

    def get(self, session_id):
        """获取会话的对话流程"""
        try:
            flow = MessageService.get_session_conversation_flow(session_id)

            return {
                'success': True,
                'data': {
                    'session_id': session_id,
                    'flow': flow,
                    'message_count': len(flow)
                }
            }

        except Exception as e:
            current_app.logger.error(f"获取对话流程失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取对话流程失败'
            }, 500


class MessageSearch(Resource):
    """消息搜索资源"""

    def get(self):
        """搜索消息"""
        try:
            # 查询参数
            query_params = {
                'session_id': request.args.get('session_id', type=int),
                'speaker_role_id': request.args.get('speaker_role_id', type=int),
                'keyword': request.args.get('keyword', type=str),
                'start_date': request.args.get('start_date', type=str),
                'end_date': request.args.get('end_date', type=str),
                'order_by': request.args.get('order_by', 'created_at', type=str),
                'page': request.args.get('page', 1, type=int),
                'page_size': min(request.args.get('page_size', 20, type=int), 100)
            }

            # 搜索消息
            result = MessageService.search_messages(query_params)

            # 序列化结果
            message_schema = MessageSchema(many=True)
            messages_data = message_schema.dump(result['messages'])

            return {
                'success': True,
                'data': {
                    'messages': messages_data,
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'pages': result['pages']
                }
            }

        except Exception as e:
            current_app.logger.error(f"搜索消息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '搜索消息失败'
            }, 500


class SessionMessageStatistics(Resource):
    """会话内消息统计资源"""

    def get(self, session_id):
        """获取指定会话的消息统计信息"""
        try:
            stats = MessageService.get_message_statistics(session_id)

            return {
                'success': True,
                'data': stats
            }

        except Exception as e:
            current_app.logger.error(f"获取会话消息统计失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '获取会话消息统计失败'
            }, 500