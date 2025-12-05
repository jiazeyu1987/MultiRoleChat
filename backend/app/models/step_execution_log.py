from datetime import datetime
from app import db
import json


class StepExecutionLog(db.Model):
    """步骤执行日志模型"""
    __tablename__ = 'step_execution_logs'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('flow_steps.id'), nullable=False)
    parent_log_id = db.Column(db.Integer, db.ForeignKey('step_execution_logs.id'))  # 父日志ID（用于循环）

    # 性能索引定义
    __table_args__ = (
        db.Index('idx_step_logs_session_execution_order', 'session_id', 'execution_order'),
        db.Index('idx_step_logs_step_id', 'step_id'),
        db.Index('idx_step_logs_status', 'status'),
        db.Index('idx_step_logs_parent_log', 'parent_log_id'),
        db.Index('idx_step_logs_round_loop', 'round_index', 'loop_iteration'),
        db.Index('idx_step_logs_created_at', 'created_at'),
        db.Index('idx_step_logs_duration', 'duration_ms'),
        db.Index('idx_step_logs_result_type', 'result_type'),
        db.Index('idx_step_logs_session_status_execution', 'session_id', 'status', 'execution_order'),
    )

    # 执行信息
    execution_order = db.Column(db.Integer, nullable=False)  # 执行顺序
    round_index = db.Column(db.Integer, default=1)  # 轮次索引
    loop_iteration = db.Column(db.Integer, default=0)  # 循环迭代次数
    attempt_count = db.Column(db.Integer, default=1)  # 尝试次数

    # 状态信息
    status = db.Column(db.String(20), default='pending')  # pending/running/completed/failed/skipped/timeout
    result_type = db.Column(db.String(50))  # success/condition_true/condition_false/loop_continue/loop_break/error

    # 执行结果
    result_data = db.Column(db.Text)  # 执行结果数据（JSON格式）
    condition_evaluation = db.Column(db.Boolean)  # 条件评估结果
    loop_check_result = db.Column(db.Boolean)  # 循环检查结果
    error_message = db.Column(db.Text)  # 错误信息

    # 性能指标
    duration_ms = db.Column(db.Integer)  # 执行时长（毫秒）
    memory_usage_mb = db.Column(db.Float)  # 内存使用（MB）

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)  # 开始执行时间
    completed_at = db.Column(db.DateTime)  # 完成时间

    # 步骤快照
    step_snapshot = db.Column(db.Text)  # 步骤配置快照（JSON格式）
    context_snapshot = db.Column(db.Text)  # 执行上下文快照（JSON格式）

    # 关系
    session = db.relationship('Session', backref='step_execution_logs')
    step = db.relationship('FlowStep', backref='execution_logs')
    parent_log = db.relationship('StepExecutionLog', remote_side=[id], backref='child_logs')

    @property
    def result_data_dict(self):
        """获取结果数据字典"""
        if self.result_data:
            try:
                return json.loads(self.result_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @result_data_dict.setter
    def result_data_dict(self, value):
        """设置结果数据"""
        if isinstance(value, dict):
            self.result_data = json.dumps(value, ensure_ascii=False)
        else:
            self.result_data = value

    @property
    def step_snapshot_dict(self):
        """获取步骤快照字典"""
        if self.step_snapshot:
            try:
                return json.loads(self.step_snapshot)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @step_snapshot_dict.setter
    def step_snapshot_dict(self, value):
        """设置步骤快照"""
        if isinstance(value, dict):
            self.step_snapshot = json.dumps(value, ensure_ascii=False)
        else:
            self.step_snapshot = value

    @property
    def context_snapshot_dict(self):
        """获取上下文快照字典"""
        if self.context_snapshot:
            try:
                return json.loads(self.context_snapshot)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @context_snapshot_dict.setter
    def context_snapshot_dict(self, value):
        """设置上下文快照"""
        if isinstance(value, dict):
            self.context_snapshot = json.dumps(value, ensure_ascii=False)
        else:
            self.context_snapshot = value

    @property
    def duration_seconds(self):
        """获取执行时长（秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        elif self.started_at:
            delta = datetime.utcnow() - self.started_at
            return delta.total_seconds()
        return None

    def is_active(self):
        """判断是否正在执行中"""
        return self.status == 'running'

    def is_successful(self):
        """判断是否成功完成"""
        return self.status == 'completed'

    def is_failed(self):
        """判断是否失败"""
        return self.status == 'failed'

    def is_loop_iteration(self):
        """判断是否为循环迭代"""
        return self.loop_iteration > 0

    def to_dict(self, include_details=False):
        """转换为字典"""
        result = {
            'id': self.id,
            'session_id': self.session_id,
            'step_id': self.step_id,
            'parent_log_id': self.parent_log_id,
            'execution_order': self.execution_order,
            'round_index': self.round_index,
            'loop_iteration': self.loop_iteration,
            'attempt_count': self.attempt_count,
            'status': self.status,
            'result_type': self.result_type,
            'condition_evaluation': self.condition_evaluation,
            'loop_check_result': self.loop_check_result,
            'error_message': self.error_message,
            'duration_ms': self.duration_ms,
            'duration_seconds': self.duration_seconds,
            'memory_usage_mb': self.memory_usage_mb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

        if include_details:
            # 包含详细数据
            result.update({
                'result_data': self.result_data_dict,
                'step_snapshot': self.step_snapshot_dict,
                'context_snapshot': self.context_snapshot_dict
            })

            # 步骤信息
            if self.step:
                result['step_info'] = {
                    'id': self.step.id,
                    'name': self.step.name,
                    'step_type': self.step.step_type,
                    'description': self.step.description
                }

            # 子日志数量
            result['child_log_count'] = len(self.child_logs) if self.child_logs else 0

        return result

    @classmethod
    def get_session_progress_summary(cls, session_id):
        """获取会话进度摘要"""
        logs = cls.query.filter_by(session_id=session_id).order_by(cls.execution_order).all()

        if not logs:
            return {
                'total_steps': 0,
                'completed_steps': 0,
                'failed_steps': 0,
                'running_steps': 0,
                'pending_steps': 0,
                'current_step': None,
                'progress_percentage': 0
            }

        total_steps = len(logs)
        completed_steps = len([log for log in logs if log.status == 'completed'])
        failed_steps = len([log for log in logs if log.status == 'failed'])
        running_steps = len([log for log in logs if log.status == 'running'])
        pending_steps = len([log for log in logs if log.status == 'pending'])

        # 获取当前步骤（最后执行的步骤）
        current_step = None
        for log in reversed(logs):
            if log.status in ['running', 'pending', 'completed']:
                current_step = log.to_dict(include_details=False)
                break

        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0

        return {
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'failed_steps': failed_steps,
            'running_steps': running_steps,
            'pending_steps': pending_steps,
            'current_step': current_step,
            'progress_percentage': round(progress_percentage, 2)
        }

    def __repr__(self):
        return f'<StepExecutionLog {self.id}:Session{self.session_id}-Step{self.step_id}-{self.status}>'