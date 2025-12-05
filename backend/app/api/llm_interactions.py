"""LLM交互API模块

提供LLM调用记录、统计信息和管理功能的REST API
"""

from flask import request, current_app
from flask_restful import Resource
from app.services.llm_interaction_service import LLMInteractionService
from datetime import datetime


class SessionLLMInteractions(Resource):
    """会话LLM交互记录资源"""

    def get(self, session_id):
        """获取会话的LLM交互记录"""
        try:
            # 查询参数
            include_details = request.args.get('include_details', 'false').lower() == 'true'
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 200)
            status_filter = request.args.get('status', None, type=str)

            # 验证状态过滤器
            if status_filter and status_filter not in ['pending', 'streaming', 'completed', 'failed', 'timeout']:
                return {
                    'success': False,
                    'error': 'Invalid status filter',
                    'message': 'Status must be one of: pending, streaming, completed, failed, timeout'
                }, 400

            # 获取LLM交互记录
            result = LLMInteractionService.get_session_llm_interactions(
                session_id=session_id,
                include_details=include_details,
                page=page,
                per_page=per_page,
                status_filter=status_filter
            )

            return {
                'success': True,
                'data': result,
                'message': f'Successfully retrieved LLM interactions for session {session_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM interactions for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMInteractionDetails(Resource):
    """LLM交互详情资源"""

    def get(self, interaction_id):
        """获取LLM交互详情"""
        try:
            details = LLMInteractionService.get_llm_interaction_details(interaction_id)

            if not details:
                return {
                    'success': False,
                    'error': 'LLM interaction not found',
                    'message': f'LLM interaction {interaction_id} not found'
                }, 404

            return {
                'success': True,
                'data': details,
                'message': f'Successfully retrieved LLM interaction details for {interaction_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM interaction details {interaction_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class SessionLLMStatistics(Resource):
    """会话LLM统计资源"""

    def get(self, session_id):
        """获取会话LLM使用统计"""
        try:
            # 查询参数
            days = min(max(request.args.get('days', 7, type=int), 1), 90)  # 限制在1-90天

            statistics = LLMInteractionService.get_session_llm_statistics(session_id, days)

            return {
                'success': True,
                'data': statistics,
                'message': f'Successfully retrieved LLM statistics for session {session_id}'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM statistics for session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class ActiveLLMInteractions(Resource):
    """活跃LLM交互资源"""

    def get(self):
        """获取所有活跃的LLM交互"""
        try:
            active_interactions = LLMInteractionService.get_active_llm_interactions()

            return {
                'success': True,
                'data': active_interactions,
                'count': len(active_interactions),
                'message': f'Successfully retrieved {len(active_interactions)} active LLM interactions'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get active LLM interactions: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMErrorLogs(Resource):
    """LLM错误日志资源"""

    def get(self):
        """获取最近的LLM错误记录"""
        try:
            # 查询参数
            limit = min(max(request.args.get('limit', 50, type=int), 1), 500)  # 限制在1-500条

            error_logs = LLMInteractionService.get_recent_llm_errors(limit)

            return {
                'success': True,
                'data': error_logs,
                'count': len(error_logs),
                'message': f'Successfully retrieved {len(error_logs)} LLM error logs'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM error logs: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMInteractionCleanup(Resource):
    """LLM交互清理资源"""

    def post(self):
        """清理旧的LLM交互记录"""
        try:
            data = request.get_json()
            days_to_keep = data.get('days_to_keep', 90)

            if not isinstance(days_to_keep, int) or days_to_keep < 1:
                return {
                    'success': False,
                    'error': 'Invalid days_to_keep parameter',
                    'message': 'days_to_keep must be a positive integer'
                }, 400

            deleted_count = LLMInteractionService.cleanup_old_interactions(days_to_keep)

            return {
                'success': True,
                'data': {
                    'deleted_count': deleted_count,
                    'days_kept': days_to_keep
                },
                'message': f'Successfully cleaned {deleted_count} old LLM interactions'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to cleanup LLM interactions: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMUsageTrends(Resource):
    """LLM使用趋势资源"""

    def get(self):
        """获取LLM使用趋势"""
        try:
            # 查询参数
            days = min(max(request.args.get('days', 30, type=int), 1), 365)  # 限制在1-365天

            trends = LLMInteractionService.get_llm_usage_trends(days)

            return {
                'success': True,
                'data': trends,
                'message': f'Successfully retrieved LLM usage trends for {days} days'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM usage trends: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMSystemMetrics(Resource):
    """LLM系统指标资源"""

    def get(self):
        """获取系统LLM指标"""
        try:
            from app.models.llm_interaction import LLMInteraction
            from sqlalchemy import func, and_
            from datetime import timedelta

            # 最近24小时的指标
            yesterday = datetime.utcnow() - timedelta(days=1)

            # 基本统计
            total_interactions = LLMInteraction.query.filter(
                LLMInteraction.created_at >= yesterday
            ).count()

            completed_interactions = LLMInteraction.query.filter(
                and_(
                    LLMInteraction.created_at >= yesterday,
                    LLMInteraction.status == 'completed'
                )
            ).count()

            failed_interactions = LLMInteraction.query.filter(
                and_(
                    LLMInteraction.created_at >= yesterday,
                    LLMInteraction.status == 'failed'
                )
            ).count()

            # Token使用统计
            token_stats = LLMInteraction.query.with_entities(
                func.sum(LLMInteraction.usage_input_tokens),
                func.sum(LLMInteraction.usage_output_tokens),
                func.sum(LLMInteraction.usage_total_tokens)
            ).filter(
                and_(
                    LLMInteraction.created_at >= yesterday,
                    LLMInteraction.status == 'completed'
                )
            ).first()

            # 延迟统计
            latency_stats = LLMInteraction.query.with_entities(
                func.avg(LLMInteraction.latency_ms),
                func.min(LLMInteraction.latency_ms),
                func.max(LLMInteraction.latency_ms)
            ).filter(
                and_(
                    LLMInteraction.created_at >= yesterday,
                    LLMInteraction.status == 'completed',
                    LLMInteraction.latency_ms.isnot(None)
                )
            ).first()

            # 按提供商统计
            provider_stats = LLMInteraction.query.with_entities(
                LLMInteraction.provider,
                func.count(LLMInteraction.id),
                func.sum(LLMInteraction.usage_total_tokens)
            ).filter(
                and_(
                    LLMInteraction.created_at >= yesterday,
                    LLMInteraction.status == 'completed'
                )
            ).group_by(LLMInteraction.provider).all()

            metrics = {
                'period_hours': 24,
                'total_interactions': total_interactions,
                'completed_interactions': completed_interactions,
                'failed_interactions': failed_interactions,
                'success_rate': (completed_interactions / total_interactions * 100) if total_interactions > 0 else 0,
                'token_usage': {
                    'total_input_tokens': token_stats[0] or 0,
                    'total_output_tokens': token_stats[1] or 0,
                    'total_tokens': token_stats[2] or 0
                },
                'latency': {
                    'average_ms': round(latency_stats[0], 2) if latency_stats[0] else 0,
                    'min_ms': latency_stats[1] or 0,
                    'max_ms': latency_stats[2] or 0
                },
                'by_provider': [
                    {
                        'provider': provider,
                        'count': count,
                        'total_tokens': total_tokens or 0
                    }
                    for provider, count, total_tokens in provider_stats
                ]
            }

            return {
                'success': True,
                'data': metrics,
                'generated_at': datetime.utcnow().isoformat(),
                'message': 'Successfully retrieved LLM system metrics'
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get LLM system metrics: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


class LLMInteractionControl(Resource):
    """LLM交互控制资源"""

    def post(self, interaction_id, action):
        """控制LLM交互（超时等操作）"""
        try:
            if action == 'timeout':
                data = request.get_json() or {}
                timeout_seconds = data.get('timeout_seconds', 30)

                success = LLMInteractionService.timeout_llm_interaction(
                    interaction_id, timeout_seconds
                )

                if success:
                    return {
                        'success': True,
                        'message': f'Successfully timeout LLM interaction {interaction_id}'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Interaction not found',
                        'message': f'LLM interaction {interaction_id} not found'
                    }, 404
            else:
                return {
                    'success': False,
                    'error': 'Invalid action',
                    'message': f'Action {action} is not supported'
                }, 400

        except Exception as e:
            current_app.logger.error(f"Failed to control LLM interaction {interaction_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500


# API资源映射
api_resources = [
    (SessionLLMInteractions, '/api/sessions/<int:session_id>/llm-interactions'),
    (LLMInteractionDetails, '/api/llm-interactions/<int:interaction_id>/details'),
    (SessionLLMStatistics, '/api/sessions/<int:session_id>/llm-statistics'),
    (ActiveLLMInteractions, '/api/llm-interactions/active'),
    (LLMErrorLogs, '/api/llm-interactions/errors'),
    (LLMInteractionCleanup, '/api/llm-interactions/cleanup'),
    (LLMUsageTrends, '/api/llm-interactions/trends'),
    (LLMSystemMetrics, '/api/llm-interactions/metrics'),
    (LLMInteractionControl, '/api/llm-interactions/<int:interaction_id>/control/<string:action>')
]


def register_llm_interaction_api(api):
    """注册LLM交互API资源"""
    for resource, endpoint in api_resources:
        api.add_resource(resource, endpoint)