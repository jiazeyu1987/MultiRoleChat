# 监控和健康检查API模块
from flask import request, current_app
from flask_restful import Resource
import asyncio
import logging
from datetime import datetime, timedelta

from app.services.monitoring_service import performance_monitor
from app.services.health_service import health_check_service
from app.utils.monitoring import get_system_info, monitor_request

logger = logging.getLogger(__name__)


class SystemHealth(Resource):
    """系统健康检查资源"""

    @monitor_request
    def get(self):
        """获取系统健康状态"""
        try:
            # 异步执行健康检查
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_status = loop.run_until_complete(
                    health_check_service.perform_full_health_check()
                )
            finally:
                loop.close()

            # 格式化返回数据
            result = {
                'overall_status': health_status.overall_status,
                'health_score': health_status.health_score,
                'timestamp': health_status.timestamp.isoformat(),
                'uptime': health_status.uptime,
                'checks': []
            }

            for check in health_status.checks:
                check_data = {
                    'component': check.component,
                    'status': check.status,
                    'message': check.message,
                    'response_time_ms': check.response_time * 1000,
                    'timestamp': check.timestamp.isoformat()
                }

                if check.details:
                    check_data['details'] = check.details

                result['checks'].append(check_data)

            # 根据健康状态设置HTTP状态码
            status_code = 200
            if health_status.overall_status == 'unhealthy':
                status_code = 503
            elif health_status.overall_status == 'degraded':
                status_code = 200  # 仍然返回200，但在状态中说明降级

            return {
                'success': True,
                'data': result
            }, status_code

        except Exception as e:
            logger.error(f"获取系统健康状态失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'HEALTH_CHECK_ERROR',
                'message': '系统健康检查失败',
                'details': str(e)
            }, 500


class PerformanceMetrics(Resource):
    """性能指标资源"""

    @monitor_request
    def get(self):
        """获取当前性能指标"""
        try:
            metrics = performance_monitor.get_current_metrics()

            return {
                'success': True,
                'data': metrics,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取性能指标失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'METRICS_ERROR',
                'message': '获取性能指标失败'
            }, 500


class PerformanceHistory(Resource):
    """性能历史数据资源"""

    @monitor_request
    def get(self):
        """获取性能历史数据"""
        try:
            # 查询参数
            hours = request.args.get('hours', 24, type=int)
            hours = min(max(hours, 1), 168)  # 限制在1小时到7天之间

            history = performance_monitor.get_metrics_history(hours)

            return {
                'success': True,
                'data': {
                    'history': history,
                    'hours_requested': hours,
                    'total_records': len(history)
                }
            }

        except Exception as e:
            logger.error(f"获取性能历史数据失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'HISTORY_ERROR',
                'message': '获取性能历史数据失败'
            }, 500


class PerformanceSummary(Resource):
    """性能摘要资源"""

    @monitor_request
    def get(self):
        """获取性能摘要"""
        try:
            summary = performance_monitor.get_performance_summary()

            return {
                'success': True,
                'data': summary,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取性能摘要失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'SUMMARY_ERROR',
                'message': '获取性能摘要失败'
            }, 500


class HealthHistory(Resource):
    """健康检查历史资源"""

    @monitor_request
    def get(self):
        """获取健康检查历史"""
        try:
            # 查询参数
            hours = request.args.get('hours', 24, type=int)
            hours = min(max(hours, 1), 168)  # 限制在1小时到7天之间

            history = health_check_service.get_health_history(hours)

            return {
                'success': True,
                'data': {
                    'history': history,
                    'hours_requested': hours,
                    'total_records': len(history)
                }
            }

        except Exception as e:
            logger.error(f"获取健康检查历史失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'HEALTH_HISTORY_ERROR',
                'message': '获取健康检查历史失败'
            }, 500


class ComponentHealthTrend(Resource):
    """组件健康趋势资源"""

    @monitor_request
    def get(self, component):
        """获取特定组件的健康趋势"""
        try:
            # 查询参数
            hours = request.args.get('hours', 24, type=int)
            hours = min(max(hours, 1), 168)  # 限制在1小时到7天之间

            trend = health_check_service.get_component_health_trend(component, hours)

            return {
                'success': True,
                'data': trend
            }

        except Exception as e:
            logger.error(f"获取组件健康趋势失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'TREND_ERROR',
                'message': '获取组件健康趋势失败'
            }, 500


class SystemInfo(Resource):
    """系统信息资源"""

    @monitor_request
    def get(self):
        """获取系统信息"""
        try:
            system_info = get_system_info()

            return {
                'success': True,
                'data': system_info,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'SYSTEM_INFO_ERROR',
                'message': '获取系统信息失败'
            }, 500


class MonitoringAlerts(Resource):
    """监控告警资源"""

    @monitor_request
    def get(self):
        """获取监控告警配置"""
        try:
            alerts_config = {
                'thresholds': performance_monitor.alert_thresholds,
                'monitoring_status': 'running' if performance_monitor.is_running else 'stopped',
                'history_size': len(performance_monitor.metrics_history),
                'max_history_size': performance_monitor.max_history_size
            }

            return {
                'success': True,
                'data': alerts_config
            }

        except Exception as e:
            logger.error(f"获取告警配置失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'ALERTS_CONFIG_ERROR',
                'message': '获取告警配置失败'
            }, 500

    @monitor_request
    def put(self):
        """更新监控告警配置"""
        try:
            json_data = request.get_json()
            if not json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }, 400

            # 更新告警阈值
            if 'thresholds' in json_data:
                thresholds = json_data['thresholds']
                for metric_type, threshold in thresholds.items():
                    if metric_type in performance_monitor.alert_thresholds:
                        performance_monitor.set_alert_threshold(metric_type, float(threshold))

            return {
                'success': True,
                'message': '告警配置更新成功',
                'data': {
                    'thresholds': performance_monitor.alert_thresholds
                }
            }

        except Exception as e:
            logger.error(f"更新告警配置失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'UPDATE_ALERTS_ERROR',
                'message': '更新告警配置失败'
            }, 500


class MonitoringControl(Resource):
    """监控控制资源"""

    @monitor_request
    def post(self):
        """控制监控服务"""
        try:
            json_data = request.get_json()
            if not json_data or 'action' not in json_data:
                return {
                    'success': False,
                    'error_code': 'INVALID_REQUEST',
                    'message': '请求体必须包含action字段'
                }, 400

            action = json_data['action']
            interval = json_data.get('interval', 30)

            if action == 'start':
                if performance_monitor.is_running:
                    return {
                        'success': False,
                        'error_code': 'ALREADY_RUNNING',
                        'message': '监控服务已在运行中'
                    }, 400

                performance_monitor.start_monitoring(interval)
                message = '监控服务已启动'

            elif action == 'stop':
                if not performance_monitor.is_running:
                    return {
                        'success': False,
                        'error_code': 'NOT_RUNNING',
                        'message': '监控服务未在运行'
                    }, 400

                performance_monitor.stop_monitoring()
                message = '监控服务已停止'

            elif action == 'clear':
                performance_monitor.clear_history()
                message = '监控历史数据已清空'

            else:
                return {
                    'success': False,
                    'error_code': 'INVALID_ACTION',
                    'message': f'不支持的操作: {action}'
                }, 400

            return {
                'success': True,
                'message': message,
                'data': {
                    'monitoring_status': 'running' if performance_monitor.is_running else 'stopped',
                    'action': action
                }
            }

        except Exception as e:
            logger.error(f"控制监控服务失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'CONTROL_ERROR',
                'message': '控制监控服务失败'
            }, 500


class MonitoringDashboard(Resource):
    """监控仪表板数据资源"""

    @monitor_request
    def get(self):
        """获取监控仪表板数据"""
        try:
            # 获取各种监控数据
            current_metrics = performance_monitor.get_current_metrics()
            performance_summary = performance_monitor.get_performance_summary()

            # 异步获取健康状态
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_status = loop.run_until_complete(
                    health_check_service.perform_full_health_check()
                )
            finally:
                loop.close()

            system_info = get_system_info()

            # 组合仪表板数据
            dashboard_data = {
                'overview': {
                    'health_score': health_status.health_score,
                    'health_status': health_status.overall_status,
                    'uptime': health_status.uptime,
                    'timestamp': datetime.now().isoformat()
                },
                'performance': {
                    'current_metrics': current_metrics.get('system', {}),
                    'performance_summary': performance_summary,
                    'requests_per_minute': current_metrics.get('requests_per_minute', 0),
                    'total_requests': current_metrics.get('total_requests', 0)
                },
                'health_checks': [
                    {
                        'component': check.component,
                        'status': check.status,
                        'message': check.message,
                        'response_time_ms': check.response_time * 1000
                    }
                    for check in health_status.checks
                ],
                'system_info': system_info
            }

            return {
                'success': True,
                'data': dashboard_data
            }

        except Exception as e:
            logger.error(f"获取监控仪表板数据失败: {str(e)}")
            return {
                'success': False,
                'error_code': 'DASHBOARD_ERROR',
                'message': '获取监控仪表板数据失败'
            }, 500