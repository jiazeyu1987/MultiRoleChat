"""实时通信API模块

提供Server-Sent Events (SSE) 实现实时更新，无需额外WebSocket依赖
"""

import json
import time
import threading
from datetime import datetime
from flask import Response, request, current_app
from flask_restful import Resource
from queue import Queue, Empty
from app.services.websocket_service import websocket_service
from typing import Dict, List, Any


class SessionRealtimeUpdates(Resource):
    """会话实时更新资源 (SSE)"""

    def get(self, session_id):
        """提供会话的实时更新流"""
        def generate():
            # 创建消息队列
            message_queue = Queue()
            connection_id = f"session_{session_id}_{int(time.time())}"

            # 添加连接
            websocket_service.add_connection(connection_id, session_id)

            try:
                # 发送初始连接确认
                initial_data = {
                    'event': 'connected',
                    'session_id': session_id,
                    'connection_id': connection_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(initial_data)}\n\n"

                # 发送当前状态
                try:
                    from app.services.step_progress_service import StepProgressService
                    current_progress = StepProgressService.get_session_step_progress(session_id, include_details=False)

                    status_data = {
                        'event': 'initial_status',
                        'session_id': session_id,
                        'data': current_progress,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(status_data)}\n\n"
                except Exception as e:
                    current_app.logger.error(f"Failed to get initial status for session {session_id}: {str(e)}")

                # 保持连接活跃
                while True:
                    try:
                        # 等待消息或超时
                        message = message_queue.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except Empty:
                        # 发送心跳包
                        heartbeat = {
                            'event': 'heartbeat',
                            'session_id': session_id,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        yield f"data: {json.dumps(heartbeat)}\n\n"

            except GeneratorExit:
                # 客户端断开连接
                pass
            finally:
                # 清理连接
                websocket_service.remove_connection(connection_id, session_id)
                current_app.logger.info(f"SSE connection {connection_id} closed for session {session_id}")

        # 设置SSE响应头
        response = Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control',
                'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
            }
        )

        return response

    def post(self, session_id):
        """向会话发送控制消息"""
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'No data provided'
                }, 400

            action = data.get('action')

            if action == 'subscribe_to_llm':
                # 订阅LLM更新（通过SSE流传递）
                return {
                    'success': True,
                    'message': f'Subscribed to LLM updates for session {session_id}',
                    'data': {
                        'session_id': session_id,
                        'subscription': 'llm_updates'
                    }
                }
            elif action == 'subscribe_to_steps':
                # 订阅步骤更新（通过SSE流传递）
                return {
                    'success': True,
                    'message': f'Subscribed to step updates for session {session_id}',
                    'data': {
                        'session_id': session_id,
                        'subscription': 'step_updates'
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f'Unknown action: {action}'
                }, 400

        except Exception as e:
            current_app.logger.error(f"Failed to handle control message for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class SystemRealtimeUpdates(Resource):
    """系统实时更新资源 (SSE)"""

    def get(self):
        """提供系统的实时更新流"""
        def generate():
            connection_id = f"system_{int(time.time())}"

            # 添加全局连接
            websocket_service.add_connection(connection_id)

            try:
                # 发送初始连接确认
                initial_data = {
                    'event': 'connected',
                    'connection_id': connection_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(initial_data)}\n\n"

                # 发送系统状态
                try:
                    stats = websocket_service.get_websocket_stats()
                    system_status = {
                        'event': 'system_status',
                        'data': stats,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(system_status)}\n\n"
                except Exception as e:
                    current_app.logger.error(f"Failed to get system status: {str(e)}")

                # 保持连接活跃
                while True:
                    try:
                        # 发送定期系统状态更新
                        time.sleep(60)  # 每分钟更新一次

                        try:
                            stats = websocket_service.get_websocket_stats()
                            system_status = {
                                'event': 'system_status',
                                'data': stats,
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(system_status)}\n\n"
                        except Exception as e:
                            current_app.logger.error(f"Failed to get system status: {str(e)}")

                    except GeneratorExit:
                        break

            except GeneratorExit:
                # 客户端断开连接
                pass
            finally:
                # 清理连接
                websocket_service.remove_connection(connection_id)
                current_app.logger.info(f"System SSE connection {connection_id} closed")

        # 设置SSE响应头
        response = Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control',
                'X-Accel-Buffering': 'no'
            }
        )

        return response


class RealtimeStats(Resource):
    """实时统计资源"""

    def get(self):
        """获取实时连接统计"""
        try:
            stats = websocket_service.get_websocket_stats()

            # 添加额外统计信息
            from datetime import timedelta
            from app.models.session import Session

            # 活跃会话数
            active_sessions = Session.query.filter(
                Session.status.in_(['running', 'not_started'])
            ).count()

            # 总会话数
            total_sessions = Session.query.count()

            stats.update({
                'active_sessions': active_sessions,
                'total_sessions': total_sessions,
                'generated_at': datetime.utcnow().isoformat()
            })

            return {
                'success': True,
                'data': stats,
                'message': 'Successfully retrieved real-time statistics'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get real-time stats: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class TestRealtimeEvent(Resource):
    """测试实时事件资源"""

    def post(self):
        """发送测试事件"""
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'No data provided'
                }, 400

            event_type = data.get('event_type', 'test_event')
            session_id = data.get('session_id')
            test_data = data.get('data', {'message': 'This is a test event'})

            if session_id:
                websocket_service.broadcast_to_session(session_id, event_type, test_data)
                message = f"Test event '{event_type}' sent to session {session_id}"
            else:
                websocket_service.broadcast_to_all(event_type, test_data)
                message = f"Test event '{event_type}' broadcast to all connections"

            return {
                'success': True,
                'message': message,
                'data': {
                    'event_type': event_type,
                    'session_id': session_id,
                    'test_data': test_data
                }
            }

        except Exception as e:
            current_app.logger.error(f"Failed to send test event: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


# 消息缓冲器，用于临时存储实时消息
class MessageBuffer:
    def __init__(self):
        self._buffer: Dict[str, Queue] = {}
        self._lock = threading.Lock()

    def add_message(self, session_id: str, message: Dict):
        """添加消息到缓冲区"""
        with self._lock:
            if session_id not in self._buffer:
                self._buffer[session_id] = Queue(maxsize=100)  # 限制缓冲区大小
            try:
                self._buffer[session_id].put_nowait(message)
            except:
                # 缓冲区满时丢弃旧消息
                try:
                    self._buffer[session_id].get_nowait()
                    self._buffer[session_id].put_nowait(message)
                except:
                    pass

    def get_messages(self, session_id: str, timeout: float = 1.0) -> List[Dict]:
        """获取缓冲区的消息"""
        messages = []
        with self._lock:
            if session_id in self._buffer:
                try:
                    while True:
                        messages.append(self._buffer[session_id].get_nowait())
                except Empty:
                    pass
        return messages


# 全局消息缓冲器
message_buffer = MessageBuffer()


# API资源映射
api_resources = [
    (SessionRealtimeUpdates, '/api/sessions/<int:session_id>/live'),
    (SystemRealtimeUpdates, '/api/system/live'),
    (RealtimeStats, '/api/realtime/stats'),
    (TestRealtimeEvent, '/api/realtime/test')
]


def register_realtime_api(api):
    """注册实时通信API资源"""
    for resource, endpoint in api_resources:
        api.add_resource(resource, endpoint)