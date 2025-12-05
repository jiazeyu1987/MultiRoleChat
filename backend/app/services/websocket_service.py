"""WebSocket服务

提供实时通信支持，用于步骤进度和LLM交互的实时更新
"""

import json
import threading
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from flask import current_app
from collections import defaultdict


class WebSocketService:
    """WebSocket服务类"""

    def __init__(self):
        self._connections: Dict[str, Set] = defaultdict(set)  # 按房间分组连接
        self._session_subscribers: Dict[int, Set] = defaultdict(set)  # 会话订阅者
        self._lock = threading.Lock()

    def add_connection(self, connection_id: str, session_id: Optional[int] = None):
        """添加连接"""
        with self._lock:
            self._connections['global'].add(connection_id)
            if session_id:
                self._session_subscribers[session_id].add(connection_id)
                current_app.logger.info(f"Added connection {connection_id} to session {session_id}")

    def remove_connection(self, connection_id: str, session_id: Optional[int] = None):
        """移除连接"""
        with self._lock:
            self._connections['global'].discard(connection_id)
            if session_id and session_id in self._session_subscribers:
                self._session_subscribers[session_id].discard(connection_id)
                if not self._session_subscribers[session_id]:
                    del self._session_subscribers[session_id]
                current_app.logger.info(f"Removed connection {connection_id} from session {session_id}")

    def get_connection_count(self, session_id: Optional[int] = None) -> int:
        """获取连接数"""
        with self._lock:
            if session_id:
                return len(self._session_subscribers.get(session_id, set()))
            return len(self._connections.get('global', set()))

    def broadcast_to_session(self, session_id: int, event_type: str, data: Dict[str, Any]):
        """向特定会话广播消息"""
        message = {
            'event': event_type,
            'session_id': session_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }

        with self._lock:
            connections = self._session_subscribers.get(session_id, set())
            message_json = json.dumps(message)

            for connection_id in connections:
                try:
                    # 这里需要根据实际WebSocket实现来发送消息
                    # 例如：socketio.emit(event_type, data, room=f"session_{session_id}")
                    current_app.logger.debug(f"Sending message to {connection_id}: {event_type}")
                except Exception as e:
                    current_app.logger.error(f"Failed to send message to {connection_id}: {str(e)}")

    def broadcast_to_all(self, event_type: str, data: Dict[str, Any]):
        """向所有连接广播消息"""
        message = {
            'event': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }

        with self._lock:
            connections = self._connections.get('global', set())
            message_json = json.dumps(message)

            for connection_id in connections:
                try:
                    # 这里需要根据实际WebSocket实现来发送消息
                    current_app.logger.debug(f"Broadcasting to {connection_id}: {event_type}")
                except Exception as e:
                    current_app.logger.error(f"Failed to broadcast to {connection_id}: {str(e)}")

    # 步骤进度相关事件
    def notify_step_started(self, session_id: int, log_id: int, step_info: Dict):
        """通知步骤开始执行"""
        self.broadcast_to_session(session_id, 'step_started', {
            'log_id': log_id,
            'step_info': step_info,
            'status': 'running'
        })

    def notify_step_completed(self, session_id: int, log_id: int, step_info: Dict, result: Dict):
        """通知步骤执行完成"""
        self.broadcast_to_session(session_id, 'step_completed', {
            'log_id': log_id,
            'step_info': step_info,
            'result': result,
            'status': 'completed'
        })

    def notify_step_failed(self, session_id: int, log_id: int, step_info: Dict, error: str):
        """通知步骤执行失败"""
        self.broadcast_to_session(session_id, 'step_failed', {
            'log_id': log_id,
            'step_info': step_info,
            'error': error,
            'status': 'failed'
        })

    def notify_session_progress_updated(self, session_id: int, progress_data: Dict):
        """通知会话进度更新"""
        self.broadcast_to_session(session_id, 'session_progress_updated', progress_data)

    # LLM交互相关事件
    def notify_llm_request_started(self, session_id: int, interaction_id: int, request_info: Dict):
        """通知LLM请求开始"""
        self.broadcast_to_session(session_id, 'llm_request_started', {
            'interaction_id': interaction_id,
            'request_info': request_info,
            'status': 'pending'
        })

    def notify_llm_response_streaming(self, session_id: int, interaction_id: int, content_chunk: str):
        """通知LLM响应流式输出"""
        self.broadcast_to_session(session_id, 'llm_response_streaming', {
            'interaction_id': interaction_id,
            'content_chunk': content_chunk,
            'status': 'streaming'
        })

    def notify_llm_response_completed(self, session_id: int, interaction_id: int, response_info: Dict):
        """通知LLM响应完成"""
        self.broadcast_to_session(session_id, 'llm_response_completed', {
            'interaction_id': interaction_id,
            'response_info': response_info,
            'status': 'completed'
        })

    def notify_llm_request_failed(self, session_id: int, interaction_id: int, error: str):
        """通知LLM请求失败"""
        self.broadcast_to_session(session_id, 'llm_request_failed', {
            'interaction_id': interaction_id,
            'error': error,
            'status': 'failed'
        })

    def notify_llm_request_timeout(self, session_id: int, interaction_id: int):
        """通知LLM请求超时"""
        self.broadcast_to_session(session_id, 'llm_request_timeout', {
            'interaction_id': interaction_id,
            'status': 'timeout'
        })

    # 会话状态相关事件
    def notify_session_status_changed(self, session_id: int, old_status: str, new_status: str):
        """通知会话状态变化"""
        self.broadcast_to_session(session_id, 'session_status_changed', {
            'old_status': old_status,
            'new_status': new_status
        })

    def notify_session_created(self, session_id: int, session_info: Dict):
        """通知新会话创建"""
        self.broadcast_to_all('session_created', {
            'session_id': session_id,
            'session_info': session_info
        })

    # 系统事件
    def notify_system_status_update(self, status_data: Dict):
        """通知系统状态更新"""
        self.broadcast_to_all('system_status_updated', status_data)

    def notify_error_occurred(self, session_id: Optional[int], error_info: Dict):
        """通知错误发生"""
        if session_id:
            self.broadcast_to_session(session_id, 'error_occurred', error_info)
        else:
            self.broadcast_to_all('error_occurred', error_info)


# 全局WebSocket服务实例
websocket_service = WebSocketService()


# 集成到服务的装饰器函数
def on_step_execution_start(session_id: int, log_id: int, step_info: Dict):
    """步骤执行开始时的回调"""
    try:
        websocket_service.notify_step_started(session_id, log_id, step_info)
    except Exception as e:
        current_app.logger.error(f"Failed to notify step start: {str(e)}")


def on_step_execution_complete(session_id: int, log_id: int, step_info: Dict, result: Dict):
    """步骤执行完成时的回调"""
    try:
        websocket_service.notify_step_completed(session_id, log_id, step_info, result)
        # 更新会话进度
        from app.services.step_progress_service import StepProgressService
        progress_data = StepProgressService.get_session_step_progress(session_id, include_details=False)
        websocket_service.notify_session_progress_updated(session_id, progress_data)
    except Exception as e:
        current_app.logger.error(f"Failed to notify step completion: {str(e)}")


def on_step_execution_fail(session_id: int, log_id: int, step_info: Dict, error: str):
    """步骤执行失败时的回调"""
    try:
        websocket_service.notify_step_failed(session_id, log_id, step_info, error)
        # 更新会话进度
        from app.services.step_progress_service import StepProgressService
        progress_data = StepProgressService.get_session_step_progress(session_id, include_details=False)
        websocket_service.notify_session_progress_updated(session_id, progress_data)
    except Exception as e:
        current_app.logger.error(f"Failed to notify step failure: {str(e)}")


def on_llm_request_start(session_id: int, interaction_id: int, request_info: Dict):
    """LLM请求开始时的回调"""
    try:
        websocket_service.notify_llm_request_started(session_id, interaction_id, request_info)
    except Exception as e:
        current_app.logger.error(f"Failed to notify LLM request start: {str(e)}")


def on_llm_response_stream(session_id: int, interaction_id: int, content_chunk: str):
    """LLM响应流式输出时的回调"""
    try:
        websocket_service.notify_llm_response_streaming(session_id, interaction_id, content_chunk)
    except Exception as e:
        current_app.logger.error(f"Failed to notify LLM response stream: {str(e)}")


def on_llm_response_complete(session_id: int, interaction_id: int, response_info: Dict):
    """LLM响应完成时的回调"""
    try:
        websocket_service.notify_llm_response_completed(session_id, interaction_id, response_info)
    except Exception as e:
        current_app.logger.error(f"Failed to notify LLM response completion: {str(e)}")


def on_llm_request_fail(session_id: int, interaction_id: int, error: str):
    """LLM请求失败时的回调"""
    try:
        websocket_service.notify_llm_request_failed(session_id, interaction_id, error)
    except Exception as e:
        current_app.logger.error(f"Failed to notify LLM request failure: {str(e)}")


def on_llm_request_timeout(session_id: int, interaction_id: int):
    """LLM请求超时时的回调"""
    try:
        websocket_service.notify_llm_request_timeout(session_id, interaction_id)
    except Exception as e:
        current_app.logger.error(f"Failed to notify LLM request timeout: {str(e)}")


def on_session_status_change(session_id: int, old_status: str, new_status: str):
    """会话状态变化时的回调"""
    try:
        websocket_service.notify_session_status_changed(session_id, old_status, new_status)
    except Exception as e:
        current_app.logger.error(f"Failed to notify session status change: {str(e)}")


def on_session_created(session_id: int, session_info: Dict):
    """会话创建时的回调"""
    try:
        websocket_service.notify_session_created(session_id, session_info)
    except Exception as e:
        current_app.logger.error(f"Failed to notify session creation: {str(e)}")


def get_websocket_stats() -> Dict:
    """获取WebSocket连接统计"""
    return {
        'global_connections': websocket_service.get_connection_count(),
        'session_connections': {
            str(session_id): count
            for session_id, count in [
                (sid, websocket_service.get_connection_count(sid))
                for sid in websocket_service._session_subscribers.keys()
            ]
        }
    }