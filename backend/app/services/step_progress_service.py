"""步骤进度服务

提供步骤执行进度的跟踪、查询和管理功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from sqlalchemy import and_, or_, desc, asc, func
from app import db
from app.models.session import Session
from app.models.flow import FlowStep
from app.models.step_execution_log import StepExecutionLog
from app.services.cache_service import get_step_progress_cache


class StepProgressService:
    """步骤进度服务类"""

    @staticmethod
    def create_step_log(
        session_id: int,
        step_id: int,
        execution_order: int,
        round_index: int = 1,
        loop_iteration: int = 0,
        attempt_count: int = 1,
        parent_log_id: Optional[int] = None,
        step_snapshot: Optional[Dict] = None,
        context_snapshot: Optional[Dict] = None
    ) -> StepExecutionLog:
        """创建步骤执行日志"""
        try:
            log = StepExecutionLog(
                session_id=session_id,
                step_id=step_id,
                parent_log_id=parent_log_id,
                execution_order=execution_order,
                round_index=round_index,
                loop_iteration=loop_iteration,
                attempt_count=attempt_count,
                status='pending',
                step_snapshot=step_snapshot,
                context_snapshot=context_snapshot,
                created_at=datetime.utcnow()
            )

            db.session.add(log)
            db.session.commit()

            current_app.logger.info(f"Created step execution log: {log.id} for session {session_id}, step {step_id}")
            return log

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create step log: {str(e)}")
            raise

    @staticmethod
    def start_step_execution(log_id: int) -> bool:
        """开始步骤执行"""
        try:
            log = StepExecutionLog.query.get(log_id)
            if not log:
                return False

            log.status = 'running'
            log.started_at = datetime.utcnow()

            db.session.commit()

            # 清除相关缓存
            try:
                step_progress_cache = get_step_progress_cache()
                step_progress_cache.invalidate_session_progress(log.session_id)
            except Exception as cache_error:
                current_app.logger.warning(f"Failed to invalidate cache for session {log.session_id}: {str(cache_error)}")

            current_app.logger.debug(f"Started step execution: {log_id}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to start step execution {log_id}: {str(e)}")
            return False

    @staticmethod
    def complete_step_execution(
        log_id: int,
        result_type: Optional[str] = None,
        result_data: Optional[Dict] = None,
        condition_evaluation: Optional[bool] = None,
        loop_check_result: Optional[bool] = None,
        duration_ms: Optional[int] = None,
        memory_usage_mb: Optional[float] = None
    ) -> bool:
        """完成步骤执行"""
        try:
            log = StepExecutionLog.query.get(log_id)
            if not log:
                return False

            log.status = 'completed'
            log.result_type = result_type
            log.result_data = result_data
            log.condition_evaluation = condition_evaluation
            log.loop_check_result = loop_check_result
            log.duration_ms = duration_ms
            log.memory_usage_mb = memory_usage_mb
            log.completed_at = datetime.utcnow()

            db.session.commit()

            # 清除相关缓存
            try:
                step_progress_cache = get_step_progress_cache()
                step_progress_cache.invalidate_session_progress(log.session_id)
            except Exception as cache_error:
                current_app.logger.warning(f"Failed to invalidate cache for session {log.session_id}: {str(cache_error)}")

            current_app.logger.debug(f"Completed step execution: {log_id} with result_type: {result_type}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to complete step execution {log_id}: {str(e)}")
            return False

    @staticmethod
    def fail_step_execution(
        log_id: int,
        error_message: str,
        result_data: Optional[Dict] = None,
        duration_ms: Optional[int] = None
    ) -> bool:
        """步骤执行失败"""
        try:
            log = StepExecutionLog.query.get(log_id)
            if not log:
                return False

            log.status = 'failed'
            log.error_message = error_message
            log.result_data = result_data
            log.duration_ms = duration_ms
            log.completed_at = datetime.utcnow()

            db.session.commit()

            # 清除相关缓存
            try:
                step_progress_cache = get_step_progress_cache()
                step_progress_cache.invalidate_session_progress(log.session_id)
            except Exception as cache_error:
                current_app.logger.warning(f"Failed to invalidate cache for session {log.session_id}: {str(cache_error)}")

            current_app.logger.warning(f"Failed step execution: {log_id} - {error_message}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to record step execution failure {log_id}: {str(e)}")
            return False

    @staticmethod
    def get_session_step_progress(
        session_id: int,
        include_details: bool = False,
        page: int = 1,
        per_page: int = 50,
        use_cache: bool = True
    ) -> Dict:
        """获取会话步骤进度"""
        try:
            # 尝试从缓存获取
            step_progress_cache = get_step_progress_cache()
            cache_key = f"session_{session_id}_page_{page}_perpage_{per_page}_details_{include_details}"

            if use_cache:
                cached_data = step_progress_cache.get_session_progress(session_id, include_details)
                if cached_data and cached_data.get('pagination', {}).get('page') == page:
                    current_app.logger.debug(f"Cache hit for session {session_id} step progress")
                    return cached_data

            # 获取分页的步骤日志
            pagination = StepExecutionLog.query.filter_by(session_id=session_id)\
                .order_by(StepExecutionLog.execution_order)\
                .paginate(page=page, per_page=per_page, error_out=False)

            logs = [log.to_dict(include_details=include_details) for log in pagination.items]

            # 获取进度摘要
            summary = StepExecutionLog.get_session_progress_summary(session_id)

            # 获取当前步骤信息
            current_step = None
            if summary['current_step'] and include_details:
                current_step = StepExecutionLog.query.get(summary['current_step']['id'])
                if current_step:
                    current_step = current_step.to_dict(include_details=True)

            result = {
                'logs': logs,
                'summary': summary,
                'current_step': current_step,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }

            # 存储到缓存
            if use_cache:
                try:
                    step_progress_cache.set_session_progress(session_id, result, ttl=600)
                except Exception as cache_error:
                    current_app.logger.warning(f"Failed to cache session progress for {session_id}: {str(cache_error)}")

            return result

        except Exception as e:
            current_app.logger.error(f"Failed to get session step progress {session_id}: {str(e)}")
            raise

    @staticmethod
    def get_session_flow_visualization(session_id: int, use_cache: bool = True) -> Dict:
        """获取会话流程可视化数据"""
        try:
            # 尝试从缓存获取
            step_progress_cache = get_step_progress_cache()
            if use_cache:
                cached_viz = step_progress_cache.get_flow_visualization(session_id)
                if cached_viz:
                    current_app.logger.debug(f"Cache hit for session {session_id} flow visualization")
                    return cached_viz

            # 获取会话信息
            session = Session.query.get(session_id)
            if not session:
                return {}

            # 获取所有步骤日志
            logs = StepExecutionLog.query.filter_by(session_id=session_id)\
                .order_by(StepExecutionLog.execution_order)\
                .all()

            # 获取流程模板步骤
            flow_steps = []
            if session.flow_template:
                flow_steps = session.flow_template.steps.order_by(FlowStep.order).all()

            # 构建可视化数据
            steps = []
            for step in flow_steps:
                # 查找相关的日志
                step_logs = [log for log in logs if log.step_id == step.id]

                step_data = {
                    'id': step.id,
                    'name': step.name,
                    'step_type': step.step_type,
                    'description': step.description,
                    'order': step.order,
                    'executions': []
                }

                for log in step_logs:
                    step_data['executions'].append({
                        'log_id': log.id,
                        'status': log.status,
                        'result_type': log.result_type,
                        'round_index': log.round_index,
                        'loop_iteration': log.loop_iteration,
                        'attempt_count': log.attempt_count,
                        'duration_ms': log.duration_ms,
                        'error_message': log.error_message,
                        'created_at': log.created_at.isoformat() if log.created_at else None,
                        'started_at': log.started_at.isoformat() if log.started_at else None,
                        'completed_at': log.completed_at.isoformat() if log.completed_at else None
                    })

                steps.append(step_data)

            # 确定当前步骤
            current_step_id = session.current_step_id

            result = {
                'session_id': session_id,
                'flow_template_id': session.flow_template_id,
                'current_step_id': current_step_id,
                'session_status': session.status,
                'total_steps': len(steps),
                'completed_steps': len([s for s in steps if any(e['status'] == 'completed' for e in s['executions'])]),
                'steps': steps
            }

            # 存储到缓存
            if use_cache:
                try:
                    step_progress_cache.set_flow_visualization(session_id, result, ttl=300)
                except Exception as cache_error:
                    current_app.logger.warning(f"Failed to cache flow visualization for session {session_id}: {str(cache_error)}")

            return result

        except Exception as e:
            current_app.logger.error(f"Failed to get session flow visualization {session_id}: {str(e)}")
            raise

    @staticmethod
    def get_step_execution_details(log_id: int) -> Optional[Dict]:
        """获取步骤执行详情"""
        try:
            log = StepExecutionLog.query.get(log_id)
            if not log:
                return None

            return log.to_dict(include_details=True)

        except Exception as e:
            current_app.logger.error(f"Failed to get step execution details {log_id}: {str(e)}")
            raise

    @staticmethod
    def get_session_execution_statistics(session_id: int) -> Dict:
        """获取会话执行统计信息"""
        try:
            # 基本统计
            total_logs = StepExecutionLog.query.filter_by(session_id=session_id).count()
            completed_logs = StepExecutionLog.query.filter_by(session_id=session_id, status='completed').count()
            failed_logs = StepExecutionLog.query.filter_by(session_id=session_id, status='failed').count()
            running_logs = StepExecutionLog.query.filter_by(session_id=session_id, status='running').count()

            # 平均执行时间
            avg_duration = db.session.query(func.avg(StepExecutionLog.duration_ms))\
                .filter_by(session_id=session_id, status='completed')\
                .scalar()

            # 总执行时间
            total_duration = db.session.query(func.sum(StepExecutionLog.duration_ms))\
                .filter_by(session_id=session_id, status='completed')\
                .scalar()

            # 最近执行记录
            recent_logs = StepExecutionLog.query.filter_by(session_id=session_id)\
                .order_by(desc(StepExecutionLog.created_at))\
                .limit(5).all()

            return {
                'session_id': session_id,
                'total_steps': total_logs,
                'completed_steps': completed_logs,
                'failed_steps': failed_logs,
                'running_steps': running_logs,
                'success_rate': (completed_logs / total_logs * 100) if total_logs > 0 else 0,
                'average_duration_ms': round(avg_duration, 2) if avg_duration else 0,
                'total_duration_ms': total_duration or 0,
                'recent_executions': [log.to_dict(include_details=False) for log in recent_logs]
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get session execution statistics {session_id}: {str(e)}")
            raise

    @staticmethod
    def get_active_sessions_progress() -> List[Dict]:
        """获取所有活跃会话的进度信息"""
        try:
            # 查找活跃会话
            active_sessions = Session.query.filter(
                or_(Session.status == 'running', Session.status == 'not_started')
            ).all()

            progress_list = []
            for session in active_sessions:
                summary = StepExecutionLog.get_session_progress_summary(session.id)

                progress_list.append({
                    'session_id': session.id,
                    'topic': session.topic,
                    'status': session.status,
                    'current_step_id': session.current_step_id,
                    'executed_steps_count': session.executed_steps_count,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                    'progress_summary': summary
                })

            return progress_list

        except Exception as e:
            current_app.logger.error(f"Failed to get active sessions progress: {str(e)}")
            raise

    @staticmethod
    def clean_old_logs(days_to_keep: int = 30) -> int:
        """清理旧的步骤日志"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            deleted_count = StepExecutionLog.query.filter(
                StepExecutionLog.created_at < cutoff_date,
                StepExecutionLog.status.in_(['completed', 'failed'])
            ).delete()

            db.session.commit()

            current_app.logger.info(f"Cleaned {deleted_count} old step execution logs")
            return deleted_count

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to clean old logs: {str(e)}")
            raise