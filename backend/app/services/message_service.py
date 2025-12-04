import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import or_, and_, desc
from app import db
from app.models import Message, Session, SessionRole


class MessageService:
    """消息服务类"""

    @staticmethod
    def get_session_messages(session_id: int, page: int = 1, page_size: int = 20,
                            speaker_role_id: Optional[int] = None,
                            target_role_id: Optional[int] = None,
                            round_index: Optional[int] = None,
                            section: Optional[str] = None,
                            keyword: Optional[str] = None,
                            order_by: str = 'created_at') -> Dict[str, Any]:
        """
        获取会话消息列表

        Args:
            session_id: 会话ID
            page: 页码
            page_size: 每页大小
            speaker_role_id: 发言角色ID筛选
            target_role_id: 目标角色ID筛选
            round_index: 轮次筛选
            section: 阶段筛选
            keyword: 关键词搜索
            order_by: 排序方式

        Returns:
            Dict: 包含消息列表和分页信息的字典
        """
        query = Message.query.filter_by(session_id=session_id)

        # 角色筛选
        if speaker_role_id:
            query = query.filter(Message.speaker_session_role_id == speaker_role_id)

        if target_role_id:
            query = query.filter(Message.target_session_role_id == target_role_id)

        # 轮次筛选
        if round_index:
            query = query.filter(Message.round_index == round_index)

        # 阶段筛选
        if section:
            query = query.filter(Message.section == section)

        # 关键词搜索
        if keyword:
            query = query.filter(
                or_(
                    Message.content.contains(keyword),
                    Message.content_summary.contains(keyword)
                )
            )

        # 排序
        if order_by == 'created_at':
            query = query.order_by(Message.created_at.desc())
        elif order_by == 'created_at_asc':
            query = query.order_by(Message.created_at.asc())
        elif order_by == 'round_index':
            query = query.order_by(Message.round_index.desc(), Message.created_at.desc())

        # 分页查询
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        return {
            'messages': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[Message]:
        """
        根据ID获取消息

        Args:
            message_id: 消息ID

        Returns:
            Optional[Message]: 消息对象
        """
        return Message.query.get(message_id)

    @staticmethod
    def get_message_replies(message_id: int) -> List[Message]:
        """
        获取消息的回复

        Args:
            message_id: 消息ID

        Returns:
            List[Message]: 回复消息列表
        """
        return Message.query.filter_by(reply_to_message_id=message_id)\
            .order_by(Message.created_at.asc()).all()

    @staticmethod
    def get_session_rounds(session_id: int) -> List[Dict[str, Any]]:
        """
        获取会话的轮次信息

        Args:
            session_id: 会话ID

        Returns:
            List[Dict]: 轮次信息列表
        """
        # 按轮次分组统计消息
        round_stats = db.session.query(
            Message.round_index,
            db.func.count(Message.id).label('message_count'),
            db.func.min(Message.created_at).label('start_time'),
            db.func.max(Message.created_at).label('end_time')
        ).filter_by(session_id=session_id)\
         .group_by(Message.round_index)\
         .order_by(Message.round_index).all()

        rounds = []
        for stat in round_stats:
            # 获取该轮次的角色参与情况
            roles_in_round = db.session.query(
                SessionRole.role_id,
                Role.name,
                db.func.count(Message.id).label('message_count')
            ).join(Message, Message.speaker_session_role_id == SessionRole.id)\
             .join(Role, Role.id == SessionRole.role_id)\
             .filter(Message.session_id == session_id)\
             .filter(Message.round_index == stat.round_index)\
             .group_by(SessionRole.role_id, Role.name)\
             .all()

            rounds.append({
                'round_index': stat.round_index,
                'message_count': stat.message_count,
                'start_time': stat.start_time.isoformat() if stat.start_time else None,
                'end_time': stat.end_time.isoformat() if stat.end_time else None,
                'participants': [
                    {
                        'role_id': role_stat.role_id,
                        'role_name': role_stat.name,
                        'message_count': role_stat.message_count
                    }
                    for role_stat in roles_in_round
                ]
            })

        return rounds

    @staticmethod
    def get_session_conversation_flow(session_id: int) -> List[Dict[str, Any]]:
        """
        获取会话的对话流程

        Args:
            session_id: 会话ID

        Returns:
            List[Dict]: 对话流程信息
        """
        messages = Message.query.filter_by(session_id=session_id)\
            .order_by(Message.created_at.asc()).all()

        flow = []
        for message in messages:
            speaker_name = (
                message.speaker_role.role.name
                if message.speaker_role and message.speaker_role.role
                else '未知角色'
            )
            target_name = (
                message.target_role.role.name
                if message.target_role and message.target_role.role
                else None
            )

            flow.append({
                'id': message.id,
                'speaker_role': speaker_name,
                'target_role': target_name,
                'content': message.content,
                'content_summary': message.content_summary,
                'round_index': message.round_index,
                'section': message.section,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'reply_to_message_id': message.reply_to_message_id
            })

        return flow

    @staticmethod
    def search_messages(query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索消息

        Args:
            query_params: 查询参数

        Returns:
            Dict: 搜索结果
        """
        # 构建查询
        query = Message.query

        # 会话筛选
        if query_params.get('session_id'):
            query = query.filter(Message.session_id == query_params['session_id'])

        # 角色筛选
        if query_params.get('speaker_role_id'):
            query = query.filter(Message.speaker_session_role_id == query_params['speaker_role_id'])

        # 时间范围筛选
        if query_params.get('start_date'):
            query = query.filter(Message.created_at >= query_params['start_date'])

        if query_params.get('end_date'):
            query = query.filter(Message.created_at <= query_params['end_date'])

        # 关键词搜索
        keyword = query_params.get('keyword', '')
        if keyword:
            query = query.filter(
                or_(
                    Message.content.contains(keyword),
                    Message.content_summary.contains(keyword),
                    Message.section.contains(keyword)
                )
            )

        # 排序
        order_by = query_params.get('order_by', 'created_at')
        if order_by == 'created_at':
            query = query.order_by(Message.created_at.desc())
        elif order_by == 'created_at_asc':
            query = query.order_by(Message.created_at.asc())

        # 分页
        page = query_params.get('page', 1)
        page_size = min(query_params.get('page_size', 20), 100)

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        return {
            'messages': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def get_message_statistics(session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取消息统计信息

        Args:
            session_id: 会话ID，如果为None则统计所有消息

        Returns:
            Dict: 统计信息
        """
        query = db.session.query(Message)

        if session_id:
            query = query.filter(Message.session_id == session_id)

        total_messages = query.count()

        # 按轮次统计
        round_stats = db.session.query(
            Message.round_index,
            db.func.count(Message.id).label('count')
        ).filter_by(session_id=session_id if session_id else Message.session_id)\
         .group_by(Message.round_index)\
         .all() if session_id else []

        # 按阶段统计
        section_stats = db.session.query(
            Message.section,
            db.func.count(Message.id).label('count')
        ).filter_by(session_id=session_id if session_id else Message.session_id)\
         .group_by(Message.section)\
         .all() if session_id else []

        # 按角色统计
        role_stats = db.session.query(
            SessionRole.role_id,
            Role.name,
            db.func.count(Message.id).label('message_count')
        ).join(Message, Message.speaker_session_role_id == SessionRole.id)\
         .join(Role, Role.id == SessionRole.role_id)\
         .filter(Message.session_id == session_id if session_id else True)\
         .group_by(SessionRole.role_id, Role.name)\
         .all()

        return {
            'total_messages': total_messages,
            'round_distribution': {stat.round_index: stat.count for stat in round_stats},
            'section_distribution': {stat.section: stat.count for stat in section_stats},
            'role_distribution': {
                stat.name: stat.message_count for stat in role_stats
            }
        }

    @staticmethod
    def export_conversation(session_id: int, format: str = 'json') -> Dict[str, Any]:
        """
        导出对话记录

        Args:
            session_id: 会话ID
            format: 导出格式 ('json', 'markdown', 'text')

        Returns:
            Dict: 导出结果
        """
        session = Session.query.get(session_id)
        if not session:
            raise ValueError(f"会话ID {session_id} 不存在")

        messages = Message.query.filter_by(session_id=session_id)\
            .order_by(Message.created_at.asc()).all()

        if format == 'json':
            return MessageService._export_to_json(session, messages)
        elif format == 'markdown':
            return MessageService._export_to_markdown(session, messages)
        elif format == 'text':
            return MessageService._export_to_text(session, messages)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

    @staticmethod
    def _export_to_json(session: Session, messages: List[Message]) -> Dict[str, Any]:
        """导出为JSON格式"""
        return {
            'session': {
                'id': session.id,
                'topic': session.topic,
                'flow_template_id': session.flow_template_id,
                'status': session.status,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None
            },
            'messages': [
                {
                    'id': msg.id,
                    'speaker_role': msg.speaker_role.role_detail.name if msg.speaker_role else None,
                    'target_role': msg.target_role.role_detail.name if msg.target_role else None,
                    'content': msg.content,
                    'content_summary': msg.content_summary,
                    'round_index': msg.round_index,
                    'section': msg.section,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ]
        }

    @staticmethod
    def _export_to_markdown(session: Session, messages: List[Message]) -> Dict[str, Any]:
        """导出为Markdown格式"""
        content = f"# {session.topic}\n\n"
        content += f"**会话ID**: {session.id}\n"
        content += f"**状态**: {session.status}\n"
        content += f"**创建时间**: {session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else 'N/A'}\n\n"

        content += "## 对话记录\n\n"

        current_round = None
        for msg in messages:
            if msg.round_index != current_round:
                current_round = msg.round_index
                content += f"\n### 第 {current_round} 轮对话\n\n"

            speaker = msg.speaker_role.role_detail.name if msg.speaker_role else '未知角色'
            target = f" (回复: {msg.target_role.role_detail.name})" if msg.target_role else ""

            content += f"**{speaker}{target}**: {msg.content}\n\n"

        return {
            'content': content,
            'filename': f"conversation_{session.id}_{session.topic.replace(' ', '_')}.md"
        }

    @staticmethod
    def _export_to_text(session: Session, messages: List[Message]) -> Dict[str, Any]:
        """导出为纯文本格式"""
        content = f"对话主题: {session.topic}\n"
        content += f"会话ID: {session.id}\n"
        content += f"状态: {session.status}\n"
        content += f"创建时间: {session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else 'N/A'}\n"
        content += "=" * 50 + "\n\n"

        for msg in messages:
            speaker = msg.speaker_role.role_detail.name if msg.speaker_role else '未知角色'
            target = f" (回复: {msg.target_role.role_detail.name})" if msg.target_role else ""
            timestamp = msg.created_at.strftime('%H:%M:%S') if msg.created_at else 'N/A'

            content += f"[{timestamp}] 第{msg.round_index}轮 {speaker}{target}:\n"
            content += f"{msg.content}\n\n"

        return {
            'content': content,
            'filename': f"conversation_{session.id}_{session.topic.replace(' ', '_')}.txt"
        }

    @staticmethod
    def delete_message(message_id: int, soft_delete: bool = True) -> bool:
        """
        删除消息

        Args:
            message_id: 消息ID
            soft_delete: 是否软删除

        Returns:
            bool: 删除是否成功
        """
        message = Message.query.get(message_id)
        if not message:
            return False

        try:
            if soft_delete:
                # 软删除：将内容标记为已删除
                message.content = "[消息已删除]"
                message.content_summary = "[消息已删除]"
                db.session.commit()
            else:
                # 硬删除：直接删除
                db.session.delete(message)
                db.session.commit()
            return True

        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def update_message(message_id: int, content: str) -> Optional[Message]:
        """
        更新消息内容

        Args:
            message_id: 消息ID
            content: 新内容

        Returns:
            Optional[Message]: 更新后的消息对象
        """
        message = Message.query.get(message_id)
        if not message:
            return None

        try:
            message.content = content
            message.content_summary = MessageService._generate_content_summary(content)
            db.session.commit()
            return message

        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def _generate_content_summary(content: str) -> str:
        """生成内容摘要"""
        if len(content) <= 100:
            return content
        return content[:97] + "..."
