"""LLM交互服务

提供LLM调用记录的跟踪、查询和管理功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from sqlalchemy import and_, or_, desc, asc, func
from app import db
from app.models.session import Session
from app.models.llm_interaction import LLMInteraction
from app.models.step_execution_log import StepExecutionLog


class LLMInteractionService:
    """LLM交互服务类"""

    @staticmethod
    def create_llm_interaction(
        session_id: int,
        user_prompt: str,
        step_id: Optional[int] = None,
        session_role_id: Optional[int] = None,
        provider: str = 'openai',
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        full_prompt: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        request_id: Optional[str] = None
    ) -> LLMInteraction:
        """创建LLM交互记录"""
        try:
            interaction = LLMInteraction(
                session_id=session_id,
                step_id=step_id,
                session_role_id=session_role_id,
                provider=provider,
                model=model,
                request_id=request_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                full_prompt=full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                status='pending',
                created_at=datetime.utcnow()
            )

            db.session.add(interaction)
            db.session.commit()

            current_app.logger.info(f"Created LLM interaction: {interaction.id} for session {session_id}")
            return interaction

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create LLM interaction: {str(e)}")
            raise

    @staticmethod
    def start_llm_request(interaction_id: int) -> bool:
        """开始LLM请求"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return False

            interaction.status = 'streaming'
            interaction.started_at = datetime.utcnow()

            db.session.commit()

            current_app.logger.debug(f"Started LLM request: {interaction_id}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to start LLM request {interaction_id}: {str(e)}")
            return False

    @staticmethod
    def update_llm_response(
        interaction_id: int,
        response_content: str,
        raw_response: Optional[Dict] = None,
        finish_reason: Optional[str] = None,
        usage_input_tokens: Optional[int] = None,
        usage_output_tokens: Optional[int] = None,
        usage_total_tokens: Optional[int] = None
    ) -> bool:
        """更新LLM响应"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return False

            interaction.response_content = response_content
            interaction.raw_response = raw_response
            interaction.finish_reason = finish_reason
            interaction.usage_input_tokens = usage_input_tokens
            interaction.usage_output_tokens = usage_output_tokens
            interaction.usage_total_tokens = usage_total_tokens

            db.session.commit()

            current_app.logger.debug(f"Updated LLM response: {interaction_id}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update LLM response {interaction_id}: {str(e)}")
            return False

    @staticmethod
    def complete_llm_interaction(
        interaction_id: int,
        response_content: str,
        raw_response: Optional[Dict] = None,
        finish_reason: Optional[str] = None,
        usage_input_tokens: Optional[int] = None,
        usage_output_tokens: Optional[int] = None,
        usage_total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None
    ) -> bool:
        """完成LLM交互"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return False

            interaction.status = 'completed'
            interaction.response_content = response_content
            interaction.raw_response = raw_response
            interaction.finish_reason = finish_reason
            interaction.usage_input_tokens = usage_input_tokens
            interaction.usage_output_tokens = usage_output_tokens
            interaction.usage_total_tokens = usage_total_tokens
            interaction.latency_ms = latency_ms
            interaction.completed_at = datetime.utcnow()

            db.session.commit()

            current_app.logger.debug(f"Completed LLM interaction: {interaction_id} with {len(response_content)} chars")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to complete LLM interaction {interaction_id}: {str(e)}")
            return False

    @staticmethod
    def fail_llm_interaction(
        interaction_id: int,
        error_message: str,
        latency_ms: Optional[int] = None
    ) -> bool:
        """LLM交互失败"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return False

            interaction.status = 'failed'
            interaction.error_message = error_message
            interaction.latency_ms = latency_ms
            interaction.completed_at = datetime.utcnow()

            db.session.commit()

            current_app.logger.warning(f"Failed LLM interaction: {interaction_id} - {error_message}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to record LLM interaction failure {interaction_id}: {str(e)}")
            return False

    @staticmethod
    def timeout_llm_interaction(interaction_id: int, timeout_seconds: int = 30) -> bool:
        """LLM交互超时"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return False

            interaction.status = 'timeout'
            interaction.error_message = f"Request timeout after {timeout_seconds} seconds"
            interaction.completed_at = datetime.utcnow()

            # 计算延迟
            if interaction.started_at:
                delta = datetime.utcnow() - interaction.started_at
                interaction.latency_ms = int(delta.total_seconds() * 1000)

            db.session.commit()

            current_app.logger.warning(f"Timeout LLM interaction: {interaction_id}")
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to timeout LLM interaction {interaction_id}: {str(e)}")
            return False

    @staticmethod
    def get_session_llm_interactions(
        session_id: int,
        include_details: bool = False,
        page: int = 1,
        per_page: int = 50,
        status_filter: Optional[str] = None
    ) -> Dict:
        """获取会话的LLM交互记录"""
        try:
            # 构建查询
            query = LLMInteraction.query.filter_by(session_id=session_id)

            if status_filter:
                query = query.filter_by(status=status_filter)

            # 分页查询
            pagination = query.order_by(desc(LLMInteraction.created_at))\
                .paginate(page=page, per_page=per_page, error_out=False)

            interactions = [interaction.to_dict(include_details=include_details) for interaction in pagination.items]

            # 统计信息
            total_interactions = LLMInteraction.query.filter_by(session_id=session_id).count()
            completed_interactions = LLMInteraction.query.filter_by(session_id=session_id, status='completed').count()
            failed_interactions = LLMInteraction.query.filter_by(session_id=session_id, status='failed').count()
            active_interactions = LLMInteraction.query.filter_by(session_id=session_id)\
                .filter(LLMInteraction.status.in_(['pending', 'streaming'])).count()

            # Token使用统计
            token_stats = db.session.query(
                func.sum(LLMInteraction.usage_input_tokens),
                func.sum(LLMInteraction.usage_output_tokens),
                func.sum(LLMInteraction.usage_total_tokens),
                func.avg(LLMInteraction.latency_ms)
            ).filter_by(session_id=session_id, status='completed').first()

            return {
                'interactions': interactions,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                },
                'statistics': {
                    'total_interactions': total_interactions,
                    'completed_interactions': completed_interactions,
                    'failed_interactions': failed_interactions,
                    'active_interactions': active_interactions,
                    'success_rate': (completed_interactions / total_interactions * 100) if total_interactions > 0 else 0,
                    'total_input_tokens': token_stats[0] or 0,
                    'total_output_tokens': token_stats[1] or 0,
                    'total_tokens': token_stats[2] or 0,
                    'average_latency_ms': round(token_stats[3], 2) if token_stats[3] else 0
                }
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get session LLM interactions {session_id}: {str(e)}")
            raise

    @staticmethod
    def get_llm_interaction_details(interaction_id: int) -> Optional[Dict]:
        """获取LLM交互详情"""
        try:
            interaction = LLMInteraction.query.get(interaction_id)
            if not interaction:
                return None

            return interaction.to_dict(include_details=True)

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM interaction details {interaction_id}: {str(e)}")
            raise

    @staticmethod
    def get_session_llm_statistics(session_id: int, days: int = 7) -> Dict:
        """获取会话LLM使用统计"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # 基本统计
            total_interactions = LLMInteraction.query.filter_by(session_id=session_id)\
                .filter(LLMInteraction.created_at >= cutoff_date).count()

            completed_interactions = LLMInteraction.query.filter_by(session_id=session_id, status='completed')\
                .filter(LLMInteraction.created_at >= cutoff_date).count()

            # Token使用统计
            token_stats = db.session.query(
                func.sum(LLMInteraction.usage_input_tokens),
                func.sum(LLMInteraction.usage_output_tokens),
                func.sum(LLMInteraction.usage_total_tokens),
                func.avg(LLMInteraction.latency_ms),
                func.min(LLMInteraction.latency_ms),
                func.max(LLMInteraction.latency_ms)
            ).filter_by(session_id=session_id, status='completed')\
                .filter(LLMInteraction.created_at >= cutoff_date).first()

            # 按模型统计
            model_stats = db.session.query(
                LLMInteraction.model,
                func.count(LLMInteraction.id),
                func.sum(LLMInteraction.usage_total_tokens),
                func.avg(LLMInteraction.latency_ms)
            ).filter_by(session_id=session_id, status='completed')\
                .filter(LLMInteraction.created_at >= cutoff_date)\
                .group_by(LLMInteraction.model).all()

            # 按状态统计
            status_stats = db.session.query(
                LLMInteraction.status,
                func.count(LLMInteraction.id)
            ).filter_by(session_id=session_id)\
                .filter(LLMInteraction.created_at >= cutoff_date)\
                .group_by(LLMInteraction.status).all()

            return {
                'session_id': session_id,
                'period_days': days,
                'total_interactions': total_interactions,
                'completed_interactions': completed_interactions,
                'success_rate': (completed_interactions / total_interactions * 100) if total_interactions > 0 else 0,
                'token_usage': {
                    'total_input_tokens': token_stats[0] or 0,
                    'total_output_tokens': token_stats[1] or 0,
                    'total_tokens': token_stats[2] or 0
                },
                'performance': {
                    'average_latency_ms': round(token_stats[3], 2) if token_stats[3] else 0,
                    'min_latency_ms': token_stats[4] or 0,
                    'max_latency_ms': token_stats[5] or 0
                },
                'by_model': [
                    {
                        'model': model,
                        'count': count,
                        'total_tokens': total_tokens or 0,
                        'average_latency_ms': round(avg_latency, 2) if avg_latency else 0
                    }
                    for model, count, total_tokens, avg_latency in model_stats
                ],
                'by_status': [
                    {
                        'status': status,
                        'count': count
                    }
                    for status, count in status_stats
                ]
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get session LLM statistics {session_id}: {str(e)}")
            raise

    @staticmethod
    def get_active_llm_interactions() -> List[Dict]:
        """获取所有活跃的LLM交互"""
        try:
            active_interactions = LLMInteraction.query.filter(
                LLMInteraction.status.in_(['pending', 'streaming'])
            ).order_by(desc(LLMInteraction.created_at)).all()

            return [interaction.to_dict(include_details=False) for interaction in active_interactions]

        except Exception as e:
            current_app.logger.error(f"Failed to get active LLM interactions: {str(e)}")
            raise

    @staticmethod
    def get_recent_llm_errors(limit: int = 50) -> List[Dict]:
        """获取最近的LLM错误记录"""
        try:
            error_interactions = LLMInteraction.query.filter(
                LLMInteraction.status.in_(['failed', 'timeout'])
            ).order_by(desc(LLMInteraction.created_at)).limit(limit).all()

            return [interaction.to_dict(include_details=True) for interaction in error_interactions]

        except Exception as e:
            current_app.logger.error(f"Failed to get recent LLM errors: {str(e)}")
            raise

    @staticmethod
    def cleanup_old_interactions(days_to_keep: int = 90) -> int:
        """清理旧的LLM交互记录"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            deleted_count = LLMInteraction.query.filter(
                LLMInteraction.created_at < cutoff_date,
                LLMInteraction.status.in_(['completed', 'failed', 'timeout'])
            ).delete()

            db.session.commit()

            current_app.logger.info(f"Cleaned {deleted_count} old LLM interactions")
            return deleted_count

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to cleanup old LLM interactions: {str(e)}")
            raise

    @staticmethod
    def get_llm_usage_trends(days: int = 30) -> Dict:
        """获取LLM使用趋势"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # 按日期统计
            daily_stats = db.session.query(
                func.date(LLMInteraction.created_at).label('date'),
                func.count(LLMInteraction.id).label('total_requests'),
                func.sum(LLMInteraction.usage_total_tokens).label('total_tokens'),
                func.avg(LLMInteraction.latency_ms).label('avg_latency')
            ).filter(LLMInteraction.created_at >= cutoff_date)\
                .filter(LLMInteraction.status == 'completed')\
                .group_by(func.date(LLMInteraction.created_at))\
                .order_by(func.date(LLMInteraction.created_at)).all()

            return {
                'period_days': days,
                'daily_trends': [
                    {
                        'date': str(date),
                        'total_requests': total_requests,
                        'total_tokens': total_tokens or 0,
                        'average_latency_ms': round(avg_latency, 2) if avg_latency else 0
                    }
                    for date, total_requests, total_tokens, avg_latency in daily_stats
                ]
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM usage trends: {str(e)}")
            raise