import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """健康检查结果数据类"""
    component: str
    status: str  # healthy, degraded, unhealthy
    message: str
    details: Dict[str, Any] = None
    timestamp: datetime = None
    response_time: float = 0.0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


@dataclass
class SystemHealthStatus:
    """系统健康状态数据类"""
    overall_status: str
    health_score: int
    checks: List[HealthCheckResult]
    timestamp: datetime
    uptime: str

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HealthCheckService:
    """系统健康检查服务"""

    def __init__(self):
        self.check_history = []
        self.max_history_size = 100

    async def check_database_health(self) -> HealthCheckResult:
        """检查数据库连接健康状态"""
        start_time = datetime.now()
        try:
            from app import db
            from app.models import Role, Session, FlowTemplate

            # 测试数据库连接
            db.session.execute('SELECT 1')

            # 检查关键表的数据
            role_count = Role.query.count()
            session_count = Session.query.count()
            template_count = FlowTemplate.query.count()

            response_time = (datetime.now() - start_time).total_seconds()

            details = {
                'connection': 'ok',
                'role_count': role_count,
                'session_count': session_count,
                'template_count': template_count,
                'response_time_ms': response_time * 1000
            }

            # 根据响应时间确定状态
            if response_time > 5:
                status = 'degraded'
                message = f"数据库响应缓慢 ({response_time:.2f}s)"
            else:
                status = 'healthy'
                message = "数据库连接正常"

            return HealthCheckResult(
                component='database',
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"数据库健康检查失败: {str(e)}")
            return HealthCheckResult(
                component='database',
                status='unhealthy',
                message=f"数据库连接失败: {str(e)}",
                details={'error': str(e), 'response_time_ms': response_time * 1000},
                response_time=response_time
            )

    async def check_llm_health(self) -> HealthCheckResult:
        """检查LLM服务健康状态"""
        start_time = datetime.now()
        try:
            from app.services.llm.manager import llm_manager

            # 获取所有可用的LLM服务
            available_providers = []
            failed_providers = []

            for provider_name in ['openai']:  # 可以扩展更多提供商
                try:
                    service = llm_manager.get_service(provider_name)
                    if service and service.validate_config():
                        # 测试简单的API调用
                        from app.services.llm.base import LLMMessage, LLMRole
                        test_messages = [
                            LLMMessage(
                                role=LLMRole.USER,
                                content="Hello, this is a health check test."
                            )
                        ]

                        # 异步调用，但设置较短的超时时间
                        try:
                            await asyncio.wait_for(
                                service.generate_response(test_messages),
                                timeout=10
                            )
                            available_providers.append(provider_name)
                        except asyncio.TimeoutError:
                            failed_providers.append(f"{provider_name} (timeout)")
                        except Exception as e:
                            failed_providers.append(f"{provider_name} ({str(e)})")
                    else:
                        failed_providers.append(f"{provider_name} (invalid config)")
                except Exception as e:
                    failed_providers.append(f"{provider_name} ({str(e)})")

            response_time = (datetime.now() - start_time).total_seconds()

            details = {
                'available_providers': available_providers,
                'failed_providers': failed_providers,
                'response_time_ms': response_time * 1000
            }

            if not available_providers:
                status = 'unhealthy'
                message = "没有可用的LLM服务"
            elif len(available_providers) < len(['openai']):  # 预期提供商数量
                status = 'degraded'
                message = f"部分LLM服务不可用: {', '.join(failed_providers)}"
            else:
                status = 'healthy'
                message = "所有LLM服务正常"

            return HealthCheckResult(
                component='llm_service',
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"LLM健康检查失败: {str(e)}")
            return HealthCheckResult(
                component='llm_service',
                status='unhealthy',
                message=f"LLM服务检查失败: {str(e)}",
                details={'error': str(e), 'response_time_ms': response_time * 1000},
                response_time=response_time
            )

    async def check_system_resources(self) -> HealthCheckResult:
        """检查系统资源健康状态"""
        start_time = datetime.now()
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_memory_mb = memory.available / (1024 * 1024)

            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            free_disk_gb = disk.free / (1024 * 1024 * 1024)

            response_time = (datetime.now() - start_time).total_seconds()

            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'available_memory_mb': available_memory_mb,
                'disk_percent': disk_percent,
                'free_disk_gb': free_disk_gb,
                'response_time_ms': response_time * 1000
            }

            # 评估整体状态
            issues = []
            if cpu_percent > 90:
                issues.append("CPU使用率过高")
            if memory_percent > 90:
                issues.append("内存使用率过高")
            if disk_percent > 95:
                issues.append("磁盘空间不足")
            if available_memory_mb < 512:  # 小于512MB
                issues.append("可用内存不足")

            if issues:
                if len(issues) >= 2 or cpu_percent > 95 or memory_percent > 95:
                    status = 'unhealthy'
                else:
                    status = 'degraded'
                message = f"系统资源问题: {', '.join(issues)}"
            else:
                status = 'healthy'
                message = "系统资源正常"

            return HealthCheckResult(
                component='system_resources',
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"系统资源健康检查失败: {str(e)}")
            return HealthCheckResult(
                component='system_resources',
                status='unhealthy',
                message=f"系统资源检查失败: {str(e)}",
                details={'error': str(e), 'response_time_ms': response_time * 1000},
                response_time=response_time
            )

    async def check_application_health(self) -> HealthCheckResult:
        """检查应用程序健康状态"""
        start_time = datetime.now()
        try:
            from app.services.session_service import SessionService
            from app.services.role_service import RoleService

            # 测试关键服务功能
            session_count = SessionService.get_active_sessions_count()
            role_count = RoleService.get_roles_count()

            # 测试服务方法
            try:
                # 尝试获取一些数据来验证服务正常工作
                recent_sessions = SessionService.get_recent_sessions(limit=1)
                services_ok = True
            except Exception:
                services_ok = False

            response_time = (datetime.now() - start_time).total_seconds()

            details = {
                'active_sessions': session_count,
                'total_roles': role_count,
                'services_operational': services_ok,
                'response_time_ms': response_time * 1000
            }

            if not services_ok:
                status = 'unhealthy'
                message = "应用程序服务异常"
            elif response_time > 3:
                status = 'degraded'
                message = f"应用程序响应缓慢 ({response_time:.2f}s)"
            else:
                status = 'healthy'
                message = "应用程序运行正常"

            return HealthCheckResult(
                component='application',
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"应用程序健康检查失败: {str(e)}")
            return HealthCheckResult(
                component='application',
                status='unhealthy',
                message=f"应用程序检查失败: {str(e)}",
                details={'error': str(e), 'response_time_ms': response_time * 1000},
                response_time=response_time
            )

    async def check_external_dependencies(self) -> HealthCheckResult:
        """检查外部依赖健康状态"""
        start_time = datetime.now()
        try:
            # 这里可以添加对外部API、缓存等服务的检查
            # 目前先返回健康状态

            response_time = (datetime.now() - start_time).total_seconds()

            details = {
                'external_apis': 'not_configured',
                'cache_service': 'not_configured',
                'response_time_ms': response_time * 1000
            }

            return HealthCheckResult(
                component='external_dependencies',
                status='healthy',
                message="外部依赖检查完成（未配置外部服务）",
                details=details,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"外部依赖健康检查失败: {str(e)}")
            return HealthCheckResult(
                component='external_dependencies',
                status='unhealthy',
                message=f"外部依赖检查失败: {str(e)}",
                details={'error': str(e), 'response_time_ms': response_time * 1000},
                response_time=response_time
            )

    async def perform_full_health_check(self) -> SystemHealthStatus:
        """执行完整的健康检查"""
        start_time = datetime.now()

        # 并行执行所有健康检查
        check_tasks = [
            self.check_database_health(),
            self.check_llm_health(),
            self.check_system_resources(),
            self.check_application_health(),
            self.check_external_dependencies()
        ]

        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # 处理异常结果
        checks = []
        for result in check_results:
            if isinstance(result, Exception):
                checks.append(HealthCheckResult(
                    component='unknown',
                    status='unhealthy',
                    message=f"健康检查异常: {str(result)}"
                ))
            else:
                checks.append(result)

        # 计算整体健康状态
        overall_status, health_score = self._calculate_overall_health(checks)

        # 计算运行时间
        uptime = self._get_system_uptime()

        system_health = SystemHealthStatus(
            overall_status=overall_status,
            health_score=health_score,
            checks=checks,
            timestamp=datetime.now(),
            uptime=uptime
        )

        # 保存到历史记录
        self._save_to_history(system_health)

        return system_health

    def _calculate_overall_health(self, checks: List[HealthCheckResult]) -> Tuple[str, int]:
        """计算整体健康状态和得分"""
        if not checks:
            return 'unknown', 0

        # 状态权重
        status_weights = {
            'healthy': 100,
            'degraded': 50,
            'unhealthy': 0,
            'unknown': 25
        }

        # 计算加权平均分
        total_weight = 0
        total_score = 0

        for check in checks:
            weight = 1.0  # 默认权重
            # 关键组件有更高的权重
            if check.component in ['database', 'application']:
                weight = 2.0

            score = status_weights.get(check.status, 25)
            total_weight += weight
            total_score += score * weight

        health_score = int(total_score / total_weight) if total_weight > 0 else 0

        # 确定整体状态
        if health_score >= 90:
            overall_status = 'healthy'
        elif health_score >= 60:
            overall_status = 'degraded'
        elif health_score >= 30:
            overall_status = 'unhealthy'
        else:
            overall_status = 'critical'

        return overall_status, health_score

    def _get_system_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            import psutil
            import time

            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            return f"{days}天 {hours}小时 {minutes}分钟"
        except Exception:
            return "未知"

    def _save_to_history(self, health_status: SystemHealthStatus):
        """保存健康检查结果到历史记录"""
        try:
            self.check_history.append(health_status)
            if len(self.check_history) > self.max_history_size:
                self.check_history.pop(0)
        except Exception as e:
            logger.error(f"保存健康检查历史失败: {str(e)}")

    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取健康检查历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_history = [
            {
                'timestamp': status.timestamp.isoformat(),
                'overall_status': status.overall_status,
                'health_score': status.health_score,
                'uptime': status.uptime
            }
            for status in self.check_history
            if status.timestamp >= cutoff_time
        ]

        return filtered_history

    def get_component_health_trend(self, component: str, hours: int = 24) -> Dict[str, Any]:
        """获取特定组件的健康趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        component_checks = []
        for status in self.check_history:
            if status.timestamp >= cutoff_time:
                for check in status.checks:
                    if check.component == component:
                        component_checks.append({
                            'timestamp': check.timestamp.isoformat(),
                            'status': check.status,
                            'message': check.message,
                            'response_time': check.response_time
                        })

        # 计算趋势统计
        if not component_checks:
            return {'status': 'no_data', 'checks': []}

        status_counts = {'healthy': 0, 'degraded': 0, 'unhealthy': 0, 'unknown': 0}
        avg_response_time = 0

        for check in component_checks:
            status_counts[check['status']] += 1
            avg_response_time += check['response_time']

        avg_response_time /= len(component_checks)

        # 确定趋势
        recent_checks = component_checks[-10:] if len(component_checks) >= 10 else component_checks
        recent_healthy = sum(1 for check in recent_checks if check['status'] == 'healthy')
        trend = 'improving' if recent_healthy > len(recent_checks) * 0.7 else 'stable'

        return {
            'component': component,
            'trend': trend,
            'status_distribution': status_counts,
            'avg_response_time': avg_response_time,
            'total_checks': len(component_checks),
            'checks': component_checks[-20:]  # 最近20条检查记录
        }


# 全局健康检查服务实例
health_check_service = HealthCheckService()