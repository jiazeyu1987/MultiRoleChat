"""步骤进度API模块

提供步骤执行进度、可视化数据和相关统计信息的REST API
"""

from flask import request, current_app
from flask_restful import Resource
from app.services.step_progress_service import StepProgressService
from datetime import datetime


class SessionStepProgress(Resource):
    """会话步骤进度资源"""

    def get(self, session_id):
        """获取会话步骤进度"""
        try:
            # 查询参数
            include_details = request.args.get('include_details', 'false').lower() == 'true'
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 200)

            # 获取步骤进度
            result = StepProgressService.get_session_step_progress(
                session_id=session_id,
                include_details=include_details,
                page=page,
                per_page=per_page
            )

            return {
                'success': True,
                'data': result,
                'message': f'Successfully retrieved step progress for session {session_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get step progress for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class SessionFlowVisualization(Resource):
    """会话流程可视化资源"""

    def get(self, session_id):
        """获取会话流程可视化数据"""
        try:
            visualization_data = StepProgressService.get_session_flow_visualization(session_id)

            if not visualization_data:
                return {
                    'success': False,
                    'error': 'Session not found',
                    'message': f'Session {session_id} not found'
                }, 404

            return {
                'success': True,
                'data': visualization_data,
                'message': f'Successfully retrieved flow visualization for session {session_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get flow visualization for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class StepExecutionDetails(Resource):
    """步骤执行详情资源"""

    def get(self, log_id):
        """获取步骤执行详情"""
        try:
            details = StepProgressService.get_step_execution_details(log_id)

            if not details:
                return {
                    'success': False,
                    'error': 'Step execution log not found',
                    'message': f'Step execution log {log_id} not found'
                }, 404

            return {
                'success': True,
                'data': details,
                'message': f'Successfully retrieved step execution details for log {log_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get step execution details {log_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class SessionExecutionStatistics(Resource):
    """会话执行统计资源"""

    def get(self, session_id):
        """获取会话执行统计信息"""
        try:
            statistics = StepProgressService.get_session_execution_statistics(session_id)

            return {
                'success': True,
                'data': statistics,
                'message': f'Successfully retrieved execution statistics for session {session_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get execution statistics for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class ActiveSessionsProgress(Resource):
    """活跃会话进度资源"""

    def get(self):
        """获取所有活跃会话的进度信息"""
        try:
            progress_list = StepProgressService.get_active_sessions_progress()

            return {
                'success': True,
                'data': progress_list,
                'count': len(progress_list),
                'message': f'Successfully retrieved progress for {len(progress_list)} active sessions'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get active sessions progress: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class StepProgressCleanup(Resource):
    """步骤进度清理资源"""

    def post(self):
        """清理旧的步骤日志"""
        try:
            data = request.get_json()
            days_to_keep = data.get('days_to_keep', 30)

            if not isinstance(days_to_keep, int) or days_to_keep < 1:
                return {
                    'success': False,
                    'error': 'Invalid days_to_keep parameter',
                    'message': 'days_to_keep must be a positive integer'
                }, 400

            deleted_count = StepProgressService.clean_old_logs(days_to_keep)

            return {
                'success': True,
                'data': {
                    'deleted_count': deleted_count,
                    'days_kept': days_to_keep
                },
                'message': f'Successfully cleaned {deleted_count} old step logs'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to cleanup step logs: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class StepProgressMetrics(Resource):
    """步骤进度指标资源"""

    def get(self):
        """获取系统步骤进度指标"""
        try:
            from app.models.step_execution_log import StepExecutionLog
            from sqlalchemy import func, and_
            from datetime import timedelta

            # 最近24小时的指标
            yesterday = datetime.utcnow() - timedelta(days=1)

            # 基本统计
            total_logs = StepExecutionLog.query.filter(StepExecutionLog.created_at >= yesterday).count()
            completed_logs = StepExecutionLog.query.filter(
                and_(
                    StepExecutionLog.created_at >= yesterday,
                    StepExecutionLog.status == 'completed'
                )
            ).count()
            failed_logs = StepExecutionLog.query.filter(
                and_(
                    StepExecutionLog.created_at >= yesterday,
                    StepExecutionLog.status == 'failed'
                )
            ).count()

            # 平均执行时间
            avg_duration = StepExecutionLog.query.with_entities(
                func.avg(StepExecutionLog.duration_ms)
            ).filter(
                and_(
                    StepExecutionLog.created_at >= yesterday,
                    StepExecutionLog.status == 'completed',
                    StepExecutionLog.duration_ms.isnot(None)
                )
            ).scalar()

            metrics = {
                'period_hours': 24,
                'total_executions': total_logs,
                'completed_executions': completed_logs,
                'failed_executions': failed_logs,
                'success_rate': (completed_logs / total_logs * 100) if total_logs > 0 else 0,
                'average_duration_ms': round(avg_duration, 2) if avg_duration else 0
            }

            return {
                'success': True,
                'data': metrics,
                'generated_at': datetime.utcnow().isoformat(),
                'message': 'Successfully retrieved step progress metrics'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get step progress metrics: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


# API资源映射
api_resources = [
    (SessionStepProgress, '/api/sessions/<int:session_id>/step-progress'),
    (SessionFlowVisualization, '/api/sessions/<int:session_id>/flow-visualization'),
    (StepExecutionDetails, '/api/step-execution/<int:log_id>/details'),
    (SessionExecutionStatistics, '/api/sessions/<int:session_id>/execution-statistics'),
    (ActiveSessionsProgress, '/api/sessions/active-progress'),
    (StepProgressCleanup, '/api/step-progress/cleanup'),
    (StepProgressMetrics, '/api/step-progress/metrics')
]


def register_step_progress_api(api):
    """注册步骤进度API资源"""
    for resource, endpoint in api_resources:
        api.add_resource(resource, endpoint)