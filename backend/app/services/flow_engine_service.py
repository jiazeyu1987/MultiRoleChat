import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from app import db
from app.models import Session, SessionRole, Message, FlowTemplate, FlowStep, Role
from app.services.session_service import SessionService, SessionError, FlowExecutionError
from app.services.llm.conversation_service import conversation_llm_service
from app.services.llm.base import LLMError


class FlowEngineService:
    """流程引擎服务类 - 负责执行对话流程"""

    @staticmethod
    def execute_next_step(session_id: int) -> Tuple[Message, Dict[str, Any]]:
        """
        执行会话的下一步骤

        Args:
            session_id: 会话ID

        Returns:
            Tuple[Message, Dict[str, Any]]: (生成的消息, 执行状态信息)

        Raises:
            SessionError: 会话相关错误
            FlowExecutionError: 流程执行错误
        """
        # 获取会话
        session = Session.query.get(session_id)
        if not session:
            raise SessionError(f"会话ID {session_id} 不存在")

        if session.status != 'running':
            raise FlowExecutionError(f"会话状态为 {session.status}，无法执行步骤")

        try:
            # 获取当前步骤
            current_step = FlowStep.query.get(session.current_step_id)
            if not current_step:
                raise FlowExecutionError(f"当前步骤ID {session.current_step_id} 不存在")

            # 获取发言角色
            speaker_session_role = SessionService.get_session_role_by_ref(
                session_id, current_step.speaker_role_ref
            )
            if not speaker_session_role:
                raise FlowExecutionError(f"发言角色 '{current_step.speaker_role_ref}' 未找到")

            # 构建上下文
            context = FlowEngineService._build_context(session, current_step)

            # 使用LLM服务生成内容
            prompt_content = FlowEngineService._generate_llm_response_sync(
                speaker_session_role.role, current_step, context
            )

            # 创建消息
            message = Message(
                session_id=session_id,
                speaker_session_role_id=speaker_session_role.id,
                target_session_role_id=FlowEngineService._get_target_session_role_id(
                    session_id, current_step.target_role_ref
                ),
                reply_to_message_id=FlowEngineService._get_reply_to_message_id(session, current_step),
                content=prompt_content,
                content_summary=FlowEngineService._generate_content_summary(prompt_content),
                round_index=session.current_round,
                section=FlowEngineService._determine_message_section(current_step)
            )

            db.session.add(message)
            db.session.flush()  # 获取消息ID

            # 更新会话状态
            FlowEngineService._update_session_after_step_execution(session, current_step)

            db.session.commit()

            # 构建执行状态信息
            execution_info = {
                'step_executed': True,
                'session_status': session.status,
                'current_round': session.current_round,
                'executed_steps_count': session.executed_steps_count,
                'next_step_id': session.current_step_id,
                'is_finished': session.status == 'finished'
            }

            return message, execution_info

        except Exception as e:
            db.session.rollback()
            if isinstance(e, (SessionError, FlowExecutionError)):
                raise
            raise FlowExecutionError(f"执行步骤失败: {str(e)}")

    @staticmethod
    def _build_context(session: Session, current_step: FlowStep) -> Dict[str, Any]:
        """
        构建对话上下文

        Args:
            session: 会话对象
            current_step: 当前步骤

        Returns:
            Dict: 上下文字典
        """
        context = {
            'session_topic': session.topic,
            'current_round': session.current_round,
            'step_count': session.executed_steps_count,
            'session_roles': SessionService.get_role_mapping(session.id)
        }

        # 根据上下文范围选择历史消息
        messages = FlowEngineService._select_context_messages(session, current_step)
        context['history_messages'] = [
            {
                'id': msg.id,
                'speaker_role': msg.speaker_role.role_detail.name if msg.speaker_role else None,
                'target_role': msg.target_role.role_detail.name if msg.target_role else None,
                'content': msg.content,
                'round_index': msg.round_index,
                'section': msg.section,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]

        # 添加当前步骤信息
        context['current_step'] = {
            'task_type': current_step.task_type,
            'description': current_step.description,
            'target_role_ref': current_step.target_role_ref
        }

        return context

    @staticmethod
    def _select_context_messages(session: Session, current_step: FlowStep) -> List[Message]:
        """
        根据上下文范围选择历史消息

        Args:
            session: 会话对象
            current_step: 当前步骤

        Returns:
            List[Message]: 消息列表
        """
        query = Message.query.filter_by(session_id=session.id).order_by(Message.created_at.desc())

        if current_step.context_scope == 'none':
            return []

        elif current_step.context_scope == 'last_message':
            return query.limit(1).all()

        elif current_step.context_scope == 'last_round':
            # 获取当前轮次的最后一条消息
            last_round_message = query.filter(
                Message.round_index == session.current_round - 1
            ).first()

            if last_round_message:
                # 获取该轮次的所有消息
                return Message.query.filter(
                    and_(
                        Message.session_id == session.id,
                        Message.round_index == session.current_round - 1
                    )
                ).order_by(Message.created_at.asc()).all()
            return []

        elif current_step.context_scope == 'last_n_messages':
            n = current_step.context_param_dict.get('n', 5)
            return query.limit(n).all()

        elif current_step.context_scope == 'all':
            return query.order_by(Message.created_at.asc()).all()

        return []

    @staticmethod
    def _build_prompt(role: Role, step: FlowStep, context: Dict[str, Any]) -> str:
        """
        构建LLM提示词

        Args:
            role: 发言角色
            step: 当前步骤
            context: 上下文信息

        Returns:
            str: 提示词内容
        """
        # 角色信息
        role_info = f"""
你是{role.name}。
角色描述：{role.description}
发言风格：{role.style}
关注点：{', '.join(role.focus_points_list)}
""".strip()

        # 任务信息
        task_info = f"""
任务类型：{step.task_type}
任务描述：{step.description if step.description else '无'}
""".strip()

        # 上下文信息
        context_info = f"""
会话主题：{context['session_topic']}
当前轮次：{context['current_round']}
已执行步骤数：{context['step_count']}
""".strip()

        # 历史消息
        history_info = ""
        if context['history_messages']:
            history_info = "\n之前的对话：\n"
            for msg in context['history_messages']:
                speaker = msg['speaker_role'] or '未知角色'
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                history_info += f"{speaker}: {content}\n"

        # 组合提示词
        prompt = f"""{role_info}

{task_info}

{context_info}

{history_info}

请根据你的角色设定和当前任务，发表你的观点。"""

        return prompt

    @staticmethod
    def _get_target_session_role_id(session_id: int, target_role_ref: Optional[str]) -> Optional[int]:
        """
        获取目标角色的会话角色ID

        Args:
            session_id: 会话ID
            target_role_ref: 目标角色引用

        Returns:
            Optional[int]: 目标会话角色ID
        """
        if not target_role_ref:
            return None

        target_role = SessionService.get_session_role_by_ref(session_id, target_role_ref)
        return target_role.id if target_role else None

    @staticmethod
    def _get_reply_to_message_id(session: Session, current_step: FlowStep) -> Optional[int]:
        """
        获取回复消息ID

        Args:
            session: 会话对象
            current_step: 当前步骤

        Returns:
            Optional[int]: 回复消息ID
        """
        # 获取上一条消息作为回复目标
        last_message = Message.query.filter_by(session_id=session.id).order_by(Message.created_at.desc()).first()
        return last_message.id if last_message else None

    @staticmethod
    def _generate_content_summary(content: str) -> str:
        """
        生成内容摘要

        Args:
            content: 原始内容

        Returns:
            str: 摘要内容
        """
        # 简单的摘要逻辑，后续可以替换为更复杂的算法
        if len(content) <= 100:
            return content
        return content[:97] + "..."

    @staticmethod
    def _determine_message_section(step: FlowStep) -> str:
        """
        确定消息的阶段/小节

        Args:
            step: 当前步骤

        Returns:
            str: 阶段名称
        """
        task_type_to_section = {
            'ask_question': '提问阶段',
            'answer_question': '回答阶段',
            'review_answer': '点评阶段',
            'question': '质疑阶段',
            'summarize': '总结阶段',
            'evaluate': '评估阶段',
            'suggest': '建议阶段',
            'challenge': '挑战阶段',
            'support': '支持阶段',
            'conclude': '结论阶段'
        }
        return task_type_to_section.get(step.task_type, '讨论阶段')

    @staticmethod
    def _update_session_after_step_execution(session: Session, executed_step: FlowStep) -> None:
        """
        步骤执行后更新会话状态

        Args:
            session: 会话对象
            executed_step: 已执行的步骤
        """
        # 更新执行计数
        session.executed_steps_count += 1
        session.updated_at = datetime.utcnow()

        # 检查是否需要进入下一轮
        if FlowEngineService._should_start_new_round(session, executed_step):
            session.current_round += 1

        # 确定下一步骤
        next_step_id = FlowEngineService._determine_next_step(session, executed_step)
        if next_step_id:
            session.current_step_id = next_step_id
        else:
            # 没有下一步骤，结束会话
            session.status = 'finished'
            session.ended_at = datetime.utcnow()

    @staticmethod
    def _should_start_new_round(session: Session, step: FlowStep) -> bool:
        """
        判断是否应该开始新的轮次

        Args:
            session: 会话对象
            step: 当前步骤

        Returns:
            bool: 是否开始新轮次
        """
        # 简单的逻辑：当执行到总结类型的步骤时，开始新轮次
        return step.task_type in ['summarize', 'conclude']

    @staticmethod
    def _determine_next_step(session: Session, current_step: FlowStep) -> Optional[int]:
        """
        确定下一步骤ID

        Args:
            session: 会话对象
            current_step: 当前步骤

        Returns:
            Optional[int]: 下一步骤ID，如果没有则返回None
        """
        # 获取流程模板的所有步骤
        flow_template = FlowTemplate.query.get(session.flow_template_id)
        if not flow_template:
            return None

        all_steps = flow_template.steps.order_by(FlowStep.order).all()

        # 查找当前步骤在列表中的位置
        current_index = None
        for i, step in enumerate(all_steps):
            if step.id == current_step.id:
                current_index = i
                break

        if current_index is None:
            return None

        # 检查是否有下一步骤
        if current_index < len(all_steps) - 1:
            return all_steps[current_index + 1].id

        # 检查循环配置
        loop_config = current_step.loop_config_dict
        if loop_config.get('enabled', False):
            max_loops = loop_config.get('max_loops', 1)
            if session.current_round < max_loops:
                # 返回循环开始步骤
                loop_start_step_ref = loop_config.get('loop_start_role_ref')
                if loop_start_step_ref:
                    for step in all_steps:
                        if step.speaker_role_ref == loop_start_step_ref:
                            return step.id
                # 如果没有指定循环开始，返回第一个步骤
                return all_steps[0].id if all_steps else None

        return None

    @staticmethod
    def get_execution_context(session_id: int) -> Dict[str, Any]:
        """
        获取会话执行上下文信息

        Args:
            session_id: 会话ID

        Returns:
            Dict: 执行上下文信息
        """
        session = Session.query.get(session_id)
        if not session:
            raise SessionError(f"会话ID {session_id} 不存在")

        current_step = None
        if session.current_step_id:
            current_step = FlowStep.query.get(session.current_step_id)

        # 获取角色映射
        role_mapping = SessionService.get_role_mapping(session_id)

        # 获取最近的几条消息
        recent_messages = Message.query.filter_by(session_id=session_id)\
            .order_by(Message.created_at.desc()).limit(5).all()

        return {
            'session': {
                'id': session.id,
                'topic': session.topic,
                'status': session.status,
                'current_round': session.current_round,
                'executed_steps_count': session.executed_steps_count
            },
            'current_step': {
                'id': current_step.id if current_step else None,
                'order': current_step.order if current_step else None,
                'speaker_role_ref': current_step.speaker_role_ref if current_step else None,
                'task_type': current_step.task_type if current_step else None,
                'description': current_step.description if current_step else None
            } if current_step else None,
            'role_mapping': role_mapping,
            'recent_messages': [
                {
                    'id': msg.id,
                    'speaker_role': msg.speaker_role.role_detail.name if msg.speaker_role else None,
                    'content': msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in recent_messages
            ],
            'flow_template': {
                'id': session.flow_template_id,
                'name': session.flow_template.name if session.flow_template else None,
                'total_steps': len(session.flow_template.steps.all()) if session.flow_template else 0
            }
        }

    @staticmethod
    async def _generate_llm_response(
        role: Role,
        step: FlowStep,
        context: Dict[str, Any],
        llm_provider: str = None
    ) -> str:
        """
        使用LLM服务生成响应内容

        Args:
            role: 发言角色
            step: 当前步骤
            context: 上下文信息
            llm_provider: LLM提供商

        Returns:
            str: 生成的响应内容

        Raises:
            FlowExecutionError: LLM生成失败
        """
        try:
            # 构建角色信息
            role_info = {
                'name': role.name,
                'description': role.description,
                'style': role.style,
                'focus_points': role.focus_points_list if hasattr(role, 'focus_points_list') else []
            }

            # 构建任务信息
            task_info = {
                'task_type': step.task_type,
                'description': step.description or '',
                'session_topic': context.get('session_topic', ''),
                'current_round': context.get('current_round', 1),
                'step_count': context.get('step_count', 0)
            }

            # 获取目标角色信息
            target_role_ref = step.target_role_ref
            if target_role_ref and 'session_roles' in context:
                target_role_info = context['session_roles'].get(target_role_ref)
                if target_role_info:
                    task_info['target_role'] = target_role_info.get('name', '')

            # 调用LLM服务生成响应
            response = await conversation_llm_service.generate_response_with_context(
                speaker_role=role_info,
                target_role=None,  # 已经在task_info中处理
                session_topic=context.get('session_topic', ''),
                task_type=step.task_type,
                task_description=step.description or '',
                history_messages=context.get('history_messages', []),
                current_round=context.get('current_round', 1),
                step_count=context.get('step_count', 0),
                provider=llm_provider
            )

            # 验证响应质量
            quality_check = await conversation_llm_service.validate_response_quality(
                response, role_info, task_info
            )

            # 如果质量分数过低，记录警告
            if quality_check['quality_score'] < 0.5:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"LLM响应质量较低 (分数: {quality_check['quality_score']}): "
                    f"{', '.join(quality_check['issues'])}"
                )

            return response.content

        except LLMError as e:
            raise FlowExecutionError(f"LLM生成失败: {str(e)}")
        except Exception as e:
            raise FlowExecutionError(f"生成LLM响应时发生错误: {str(e)}")

    @staticmethod
    def _generate_llm_response_sync(
        role: Role,
        step: FlowStep,
        context: Dict[str, Any],
        llm_provider: str = None
    ) -> str:
        """
        使用LLM服务生成响应内容（同步版本）

        Args:
            role: 发言角色
            step: 当前步骤
            context: 上下文信息
            llm_provider: LLM提供商

        Returns:
            str: 生成的响应内容

        Raises:
            FlowExecutionError: LLM生成失败
        """
        try:
            # 运行异步方法
            loop = None
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果循环正在运行，我们需要在新线程中运行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, FlowEngineService._generate_llm_response(
                            role, step, context, llm_provider
                        ))
                        return future.result()
                else:
                    # 如果循环存在但未运行，直接使用
                    return loop.run_until_complete(FlowEngineService._generate_llm_response(
                        role, step, context, llm_provider
                    ))
            except RuntimeError:
                # 没有事件循环，创建新的
                return asyncio.run(FlowEngineService._generate_llm_response(
                    role, step, context, llm_provider
                ))

        except Exception as e:
            # 如果LLM服务失败，回退到模拟模式
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LLM服务不可用，使用模拟响应: {str(e)}")

            # 返回模拟响应
            return FlowEngineService._build_prompt(role, step, context)

    @staticmethod
    def execute_next_step_sync(session_id: int) -> Tuple[Message, Dict[str, Any]]:
        """
        同步版本的执行下一步骤（用于向后兼容）

        Args:
            session_id: 会话ID

        Returns:
            Tuple[Message, Dict[str, Any]]: (生成的消息, 执行状态信息)
        """
        loop = None
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果循环正在运行，我们需要在新线程中运行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, FlowEngineService.execute_next_step(session_id))
                        return future.result()
                else:
                    # 如果循环存在但未运行，直接使用
                    return loop.run_until_complete(FlowEngineService.execute_next_step(session_id))
            except RuntimeError:
                # 没有事件循环，创建新的
                return asyncio.run(FlowEngineService.execute_next_step(session_id))

        except Exception as e:
            if isinstance(e, (SessionError, FlowExecutionError)):
                raise
            raise FlowExecutionError(f"执行步骤失败: {str(e)}")