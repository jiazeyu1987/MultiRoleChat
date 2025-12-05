from datetime import datetime
from app import db


class Message(db.Model):
    """消息模型"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    speaker_session_role_id = db.Column(db.Integer, db.ForeignKey('session_roles.id'), nullable=True)  # 允许为空以支持无角色映射模式
    target_session_role_id = db.Column(db.Integer, db.ForeignKey('session_roles.id'))  # 目标角色ID
    reply_to_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))  # 回复消息ID

    # 性能索引定义
    __table_args__ = (
        db.Index('idx_messages_session_created', 'session_id', 'created_at'),
        db.Index('idx_messages_speaker_session_role', 'speaker_session_role_id'),
        db.Index('idx_messages_round_index', 'round_index'),
        db.Index('idx_messages_reply_to', 'reply_to_message_id'),
        db.Index('idx_messages_session_round_created', 'session_id', 'round_index', 'created_at'),
    )
    content = db.Column(db.Text, nullable=False)  # 消息内容
    content_summary = db.Column(db.String(500))  # 内容摘要
    round_index = db.Column(db.Integer, default=1)  # 轮次索引
    section = db.Column(db.String(100))  # 话题阶段
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    speaker_role = db.relationship('SessionRole', foreign_keys=[speaker_session_role_id])
    target_role = db.relationship('SessionRole', foreign_keys=[target_session_role_id])
    reply_to_message = db.relationship('Message', remote_side=[id])
    reply_messages = db.relationship('Message', remote_side=[reply_to_message_id])

    def get_speaker_role_name(self):
        """获取发言角色名称，支持无角色映射模式"""
        if self.speaker_role and self.speaker_role.role:
            return self.speaker_role.role.name

        # 如果没有session_role，尝试从消息内容中提取或使用默认值
        # 这里可以后续优化，比如从会话快照中获取角色信息
        return "未知角色"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'speaker_session_role_id': self.speaker_session_role_id,
            'speaker_role_name': self.get_speaker_role_name(),
            'target_session_role_id': self.target_session_role_id,
            'target_role_name': self.target_role.role.name if self.target_role and self.target_role.role else None,
            'reply_to_message_id': self.reply_to_message_id,
            'content': self.content,
            'content_summary': self.content_summary,
            'round_index': self.round_index,
            'section': self.section,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Message {self.id}:Session{self.session_id}>'