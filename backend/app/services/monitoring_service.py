import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_usage_mb: float
    disk_usage_percent: float
    active_sessions: int
    total_requests: int
    avg_response_time: float
    error_rate: float
    llm_requests: int
    llm_success_rate: float


@dataclass
class RequestMetric:
    """请求指标数据类"""
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    response_time: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class LLMMetric:
    """LLM调用指标数据类"""
    timestamp: datetime
    provider: str
    model: str
    tokens_used: int
    response_time: float
    success: bool
    error_message: Optional[str] = None


class PerformanceMonitor:
    """性能监控服务"""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.is_running = False
        self.monitor_thread = None
        self.metrics_history = deque(maxlen=max_history_size)
        self.request_history = deque(maxlen=max_history_size * 10)
        self.llm_metrics = deque(maxlen=max_history_size)

        # 实时统计数据
        self.stats = {
            'total_requests': 0,
            'requests_per_minute': 0,
            'error_count': 0,
            'last_minute_requests': deque(maxlen=100),
            'endpoint_stats': defaultdict(lambda: {
                'count': 0,
                'avg_response_time': 0,
                'error_count': 0
            }),
            'llm_stats': defaultdict(lambda: {
                'total_calls': 0,
                'success_calls': 0,
                'total_tokens': 0,
                'avg_response_time': 0
            })
        }

        # 系统基准数据
        self.baseline_metrics = None

        # 告警阈值
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'error_rate': 5.0,
            'avg_response_time': 2.0,
            'llm_error_rate': 10.0
        }

        # 告警回调列表
        self.alert_callbacks = []

        logger.info("性能监控服务初始化完成")

    def start_monitoring(self, interval: int = 30):
        """启动监控"""
        if self.is_running:
            logger.warning("性能监控已在运行中")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"性能监控已启动，监控间隔: {interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("性能监控已停止")

    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.is_running:
            try:
                metric = self._collect_system_metrics()
                self.metrics_history.append(metric)

                # 检查告警条件
                self._check_alerts(metric)

                # 更新统计数据
                self._update_stats()

                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控循环异常: {str(e)}")
                time.sleep(interval)

    def _collect_system_metrics(self) -> PerformanceMetric:
        """收集系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_usage_mb = memory.used / (1024 * 1024)

            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent

            # 计算请求数据
            current_time = datetime.now()
            last_minute_time = current_time - timedelta(minutes=1)

            # 最近一分钟的请求
            recent_requests = [
                req for req in self.request_history
                if req.timestamp >= last_minute_time
            ]

            # 计算错误率
            total_requests = len(recent_requests)
            error_requests = len([req for req in recent_requests if req.status_code >= 400])
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0

            # 计算平均响应时间
            avg_response_time = sum(req.response_time for req in recent_requests) / total_requests if total_requests > 0 else 0

            # LLM统计数据
            llm_requests = len([llm for llm in self.llm_metrics if llm.timestamp >= last_minute_time])
            llm_success_requests = len([llm for llm in self.llm_metrics if llm.timestamp >= last_minute_time and llm.success])
            llm_success_rate = (llm_success_requests / llm_requests * 100) if llm_requests > 0 else 0

            # 获取当前活跃会话数（这里简化处理，实际应该从数据库查询）
            from app.services.session_service import SessionService
            active_sessions = SessionService.get_active_sessions_count()

            return PerformanceMetric(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_usage_mb=memory_usage_mb,
                disk_usage_percent=disk_usage_percent,
                active_sessions=active_sessions,
                total_requests=self.stats['total_requests'],
                avg_response_time=avg_response_time,
                error_rate=error_rate,
                llm_requests=llm_requests,
                llm_success_rate=llm_success_rate
            )

        except Exception as e:
            logger.error(f"收集系统指标失败: {str(e)}")
            # 返回默认指标
            return PerformanceMetric(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_usage_mb=0.0,
                disk_usage_percent=0.0,
                active_sessions=0,
                total_requests=self.stats['total_requests'],
                avg_response_time=0.0,
                error_rate=0.0,
                llm_requests=0,
                llm_success_rate=0.0
            )

    def _update_stats(self):
        """更新统计数据"""
        current_time = datetime.now()
        last_minute_time = current_time - timedelta(minutes=1)

        # 更新最近一分钟的请求数
        recent_requests = [
            req for req in self.request_history
            if req.timestamp >= last_minute_time
        ]
        self.stats['requests_per_minute'] = len(recent_requests)
        self.stats['last_minute_requests'] = deque(recent_requests, maxlen=100)

        # 更新端点统计
        for req in recent_requests:
            endpoint_key = f"{req.method} {req.endpoint}"
            stats = self.stats['endpoint_stats'][endpoint_key]
            stats['count'] += 1

            # 更新平均响应时间
            total_time = stats['avg_response_time'] * (stats['count'] - 1) + req.response_time
            stats['avg_response_time'] = total_time / stats['count']

            if req.status_code >= 400:
                stats['error_count'] += 1

        # 更新LLM统计
        recent_llm = [
            llm for llm in self.llm_metrics
            if llm.timestamp >= last_minute_time
        ]

        for llm in recent_llm:
            provider_key = f"{llm.provider}:{llm.model}"
            stats = self.stats['llm_stats'][provider_key]
            stats['total_calls'] += 1

            if llm.success:
                stats['success_calls'] += 1
                stats['total_tokens'] += llm.tokens_used

            # 更新平均响应时间
            total_time = stats['avg_response_time'] * (stats['total_calls'] - 1) + llm.response_time
            stats['avg_response_time'] = total_time / stats['total_calls']

    def _check_alerts(self, metric: PerformanceMetric):
        """检查告警条件"""
        alerts = []

        # CPU告警
        if metric.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu',
                'severity': 'warning',
                'message': f'CPU使用率过高: {metric.cpu_percent:.1f}%',
                'value': metric.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })

        # 内存告警
        if metric.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory',
                'severity': 'warning',
                'message': f'内存使用率过高: {metric.memory_percent:.1f}%',
                'value': metric.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })

        # 磁盘告警
        if metric.disk_usage_percent > self.alert_thresholds['disk_usage_percent']:
            alerts.append({
                'type': 'disk',
                'severity': 'critical',
                'message': f'磁盘使用率过高: {metric.disk_usage_percent:.1f}%',
                'value': metric.disk_usage_percent,
                'threshold': self.alert_thresholds['disk_usage_percent']
            })

        # 错误率告警
        if metric.error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'error_rate',
                'severity': 'warning',
                'message': f'API错误率过高: {metric.error_rate:.1f}%',
                'value': metric.error_rate,
                'threshold': self.alert_thresholds['error_rate']
            })

        # 响应时间告警
        if metric.avg_response_time > self.alert_thresholds['avg_response_time']:
            alerts.append({
                'type': 'response_time',
                'severity': 'warning',
                'message': f'平均响应时间过长: {metric.avg_response_time:.2f}s',
                'value': metric.avg_response_time,
                'threshold': self.alert_thresholds['avg_response_time']
            })

        # LLM错误率告警 - 修复：如果没有LLM调用，不触发告警
        if metric.llm_requests > 0:
            llm_error_rate = 100 - metric.llm_success_rate
            if llm_error_rate > self.alert_thresholds['llm_error_rate']:
                alerts.append({
                    'type': 'llm_error_rate',
                    'severity': 'warning',
                    'message': f'LLM调用错误率过高: {llm_error_rate:.1f}%',
                    'value': llm_error_rate,
                    'threshold': self.alert_thresholds['llm_error_rate']
                })

        # 触发告警回调
        for alert in alerts:
            self._trigger_alert(alert)

    def _trigger_alert(self, alert: Dict[str, Any]):
        """触发告警"""
        logger.warning(f"系统告警: {alert['message']}")

        # 调用告警回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败: {str(e)}")

    def record_request(self, endpoint: str, method: str, status_code: int,
                      response_time: float, user_id: str = None, session_id: str = None):
        """记录请求指标"""
        request_metric = RequestMetric(
            timestamp=datetime.now(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            session_id=session_id
        )

        self.request_history.append(request_metric)
        self.stats['total_requests'] += 1

        if status_code >= 400:
            self.stats['error_count'] += 1

    def record_llm_call(self, provider: str, model: str, tokens_used: int,
                       response_time: float, success: bool, error_message: str = None):
        """记录LLM调用指标"""
        llm_metric = LLMMetric(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            response_time=response_time,
            success=success,
            error_message=error_message
        )

        self.llm_metrics.append(llm_metric)

    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前性能指标"""
        if not self.metrics_history:
            return {}

        latest_metric = self.metrics_history[-1]
        return {
            'system': asdict(latest_metric),
            'requests_per_minute': self.stats['requests_per_minute'],
            'total_requests': self.stats['total_requests'],
            'total_errors': self.stats['error_count'],
            'endpoint_stats': dict(self.stats['endpoint_stats']),
            'llm_stats': dict(self.stats['llm_stats'])
        }

    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取历史指标数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_metrics = [
            asdict(metric) for metric in self.metrics_history
            if metric.timestamp >= cutoff_time
        ]

        return filtered_metrics

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics_history:
            return {'status': 'no_data'}

        latest_metric = self.metrics_history[-1]

        # 计算趋势（最近1小时 vs 前1小时）
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)

        recent_metrics = [m for m in self.metrics_history if m.timestamp >= hour_ago]
        previous_metrics = [m for m in self.metrics_history if two_hours_ago <= m.timestamp < hour_ago]

        trend = {}
        if recent_metrics and previous_metrics:
            recent_avg = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            previous_avg = sum(m.cpu_percent for m in previous_metrics) / len(previous_metrics)
            trend['cpu_trend'] = 'up' if recent_avg > previous_avg else 'down'

        # 健康状态评估
        health_score = 100
        issues = []

        if latest_metric.cpu_percent > 80:
            health_score -= 20
            issues.append('CPU使用率过高')

        if latest_metric.memory_percent > 85:
            health_score -= 20
            issues.append('内存使用率过高')

        if latest_metric.error_rate > 5:
            health_score -= 30
            issues.append('API错误率过高')

        if latest_metric.avg_response_time > 2:
            health_score -= 15
            issues.append('响应时间过长')

        health_status = 'excellent'
        if health_score < 60:
            health_status = 'poor'
        elif health_score < 80:
            health_status = 'fair'
        elif health_score < 95:
            health_status = 'good'

        return {
            'health_score': max(0, health_score),
            'health_status': health_status,
            'issues': issues,
            'trend': trend,
            'uptime': self._get_uptime(),
            'last_updated': latest_metric.timestamp.isoformat()
        }

    def _get_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            return f"{days}天 {hours}小时 {minutes}分钟"
        except Exception:
            return "未知"

    def add_alert_callback(self, callback):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def set_alert_threshold(self, metric_type: str, threshold: float):
        """设置告警阈值"""
        if metric_type in self.alert_thresholds:
            self.alert_thresholds[metric_type] = threshold
            logger.info(f"告警阈值已更新: {metric_type} = {threshold}")

    def clear_history(self):
        """清空历史数据"""
        self.metrics_history.clear()
        self.request_history.clear()
        self.llm_metrics.clear()
        logger.info("监控历史数据已清空")


# 全局性能监控实例
performance_monitor = PerformanceMonitor()