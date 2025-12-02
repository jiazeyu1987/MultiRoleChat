"""
Claude Code CLI LLM服务
使用Claude Code CLI工具进行LLM交互，替代API KEY方式
"""
import asyncio
import json
import subprocess
import sys
import threading
import time
import os
from typing import Dict, List, Optional, Union, Any
import logging
from datetime import datetime

from .base import BaseLLMService, LLMMessage, LLMResponse, LLMConfig, LLMError

logger = logging.getLogger(__name__)


class ClaudeCLIService(BaseLLMService):
    """Claude Code CLI LLM服务实现"""

    def __init__(self, config: Optional[Union[Dict, LLMConfig]] = None):
        """
        初始化Claude CLI服务

        Args:
            config: 配置字典或LLMConfig对象，包含claude命令路径、超时设置等
        """
        # 如果传入的是字典，转换为LLMConfig
        if isinstance(config, dict):
            llm_config = LLMConfig(
                model="claude-sonnet-4",  # Claude CLI使用的默认模型
                timeout=config.get('timeout', 120),
                max_retries=config.get('max_retries', 3),
                retry_delay=config.get('retry_delay', 1)
            )
            # 使用Claude CLI包装脚本
            claude_cli_path = config.get('claude_command', 'claude')
            if claude_cli_path == 'claude':
                # 使用项目中的包装脚本
                self.claude_command = [sys.executable, 'app/claude_wrapper.py']
            else:
                # 使用自定义命令
                self.claude_command = claude_cli_path
        else:
            llm_config = config or LLMConfig(
                model="claude-sonnet-4",
                timeout=120,
                max_retries=3,
                retry_delay=1
            )
            # 使用项目中的包装脚本
            self.claude_command = [sys.executable, 'app/claude_wrapper.py']

        super().__init__(llm_config)

        # 验证Claude CLI是否可用
        self._validate_claude_cli()

    def _validate_claude_cli(self):
        """验证Claude CLI是否可用"""
        try:
            # 简单验证文件是否存在
            import os
            if isinstance(self.claude_command, list):
                # 列表格式：[python_executable, script_path]
                file_path = self.claude_command[1]
            else:
                # 字符串格式：命令路径
                file_path = self.claude_command

            if os.path.exists(file_path):
                logger.info("Claude CLI包装脚本验证成功")
            else:
                logger.error(f"Claude CLI包装脚本未找到: {file_path}")
                raise RuntimeError(f"Claude CLI包装脚本未找到: {file_path}")
        except Exception as e:
            logger.error(f"Claude CLI验证失败: {str(e)}")
            raise RuntimeError(f"Claude CLI验证失败: {str(e)}")

    def _execute_claude_command(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        执行Claude CLI命令

        Args:
            prompt: 用户提示词
            context: 上下文信息

        Returns:
            Claude响应文本
        """
        try:
            # 构建完整的提示词
            full_prompt = self._build_prompt(prompt, context)

            # 确定命令格式
            if isinstance(self.claude_command, list):
                command = self.claude_command
            else:
                # 字符串命令需要分割
                command = self.claude_command.split()

            # 使用subprocess运行Claude CLI
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # 发送提示词
            stdout, stderr = process.communicate(input=full_prompt, timeout=self.timeout)

            if process.returncode != 0:
                error_msg = f"Claude CLI执行失败 (返回码: {process.returncode}): {stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # 清理输出
            response = stdout.strip()
            if not response:
                raise RuntimeError("Claude CLI返回空响应")

            logger.info(f"Claude CLI响应成功，长度: {len(response)}")
            return response

        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = f"Claude CLI执行超时 ({self.timeout}秒)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Claude CLI执行异常: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _build_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        构建完整的提示词

        Args:
            prompt: 基础提示词
            context: 上下文信息

        Returns:
            完整的提示词
        """
        full_prompt = prompt

        # 添加上下文信息
        if context:
            if 'role' in context:
                full_prompt = f"你是{context['role']}。\n\n{full_prompt}"

            if 'persona' in context:
                full_prompt = f"人设: {context['persona']}\n\n{full_prompt}"

            if 'scene' in context:
                full_prompt = f"场景: {context['scene']}\n\n{full_prompt}"

            if 'history' in context and context['history']:
                history_text = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in context['history'][-5:]  # 只保留最近5轮对话
                ])
                full_prompt = f"对话历史:\n{history_text}\n\n{full_prompt}"

        # 添加系统指令
        system_instruction = (
            "请根据给定的人设和场景进行回应。保持角色的一致性， "
            "回应要符合角色的语言风格和特点。"
        )

        return f"{system_instruction}\n\n{full_prompt}"

    def generate_response(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        生成响应（同步版本）

        Args:
            prompt: 输入提示词
            context: 上下文信息
            **kwargs: 其他参数

        Returns:
            生成的响应文本
        """
        return self._execute_with_retry(
            self._execute_claude_command,
            prompt,
            context
        )

    async def generate_response_async(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        生成响应（异步版本）

        Args:
            prompt: 输入提示词
            context: 上下文信息
            **kwargs: 其他参数

        Returns:
            生成的响应文本
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_response,
            prompt,
            context
        )

    def generate_response_with_history(
        self,
        prompt: str,
        history: List[Dict],
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        基于历史对话生成响应

        Args:
            prompt: 输入提示词
            history: 对话历史
            context: 上下文信息
            **kwargs: 其他参数

        Returns:
            生成的响应文本
        """
        # 构建包含历史信息的上下文
        full_context = context.copy() if context else {}
        full_context['history'] = history

        return self.generate_response(prompt, full_context)

    async def generate_response_with_history_async(
        self,
        prompt: str,
        history: List[Dict],
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        基于历史对话生成响应（异步版本）

        Args:
            prompt: 输入提示词
            history: 对话历史
            context: 上下文信息
            **kwargs: 其他参数

        Returns:
            生成的响应文本
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_response_with_history,
            prompt,
            history,
            context
        )

    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息

        Returns:
            服务信息字典
        """
        return {
            'service_name': 'ClaudeCLI',
            'version': '1.0.0',
            'command': self.claude_command,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'created_at': datetime.now().isoformat()
        }

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            服务是否健康
        """
        try:
            # 执行简单的测试命令
            test_prompt = "请回复'健康检查通过'"
            response = self._execute_claude_command(test_prompt)
            return bool(response and len(response) > 0)
        except Exception as e:
            logger.error(f"Claude CLI健康检查失败: {e}")
            return False

    def supports_streaming(self) -> bool:
        """
        是否支持流式响应

        Returns:
            False，Claude CLI当前不支持流式响应
        """
        return False

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 输入文本

        Returns:
            估算的token数量
        """
        # 简单的token估算：大约4个字符等于1个token
        return len(text) // 4

    def get_max_tokens(self) -> int:
        """
        获取支持的最大token数量

        Returns:
            最大token数量
        """
        # Claude CLI通常支持较大的上下文
        return 200000

    async def generate_response(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        生成LLM响应（实现基类抽象方法）

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLMResponse: LLM响应对象
        """
        # 构建完整的提示词
        full_prompt = self._build_prompt_from_messages(messages)

        try:
            # 执行Claude CLI命令
            response_text = self._execute_with_retry(
                self._execute_claude_command_with_prompt,
                full_prompt
            )

            # 创建LLMResponse对象
            return LLMResponse(
                content=response_text,
                model=self.config.model,
                usage={
                    'prompt_tokens': self.estimate_tokens(full_prompt),
                    'completion_tokens': self.estimate_tokens(response_text),
                    'total_tokens': self.estimate_tokens(full_prompt + response_text)
                },
                response_time=0.0  # 将在重试机制中设置
            )

        except Exception as e:
            logger.error(f"Claude CLI响应生成失败: {str(e)}")
            raise LLMError(f"Claude CLI响应生成失败: {str(e)}", "claude_cli")

    def _build_prompt_from_messages(self, messages: List[LLMMessage]) -> str:
        """
        从消息列表构建完整的提示词

        Args:
            messages: 消息列表

        Returns:
            str: 完整的提示词
        """
        prompt_parts = []

        for message in messages:
            role_prefix = {
                "system": "系统指令：",
                "user": "用户：",
                "assistant": "助手："
            }.get(message.role, f"{message.role}：")

            prompt_parts.append(f"{role_prefix}\n{message.content}")

        return "\n\n".join(prompt_parts)

    def _execute_claude_command_with_prompt(self, prompt: str) -> str:
        """
        使用提示词执行Claude CLI命令

        Args:
            prompt: 完整的提示词

        Returns:
            Claude响应文本
        """
        try:
            # 确定命令格式
            if isinstance(self.claude_command, list):
                command = self.claude_command
            else:
                # 字符串命令需要分割
                command = self.claude_command.split()

            # 使用subprocess运行Claude CLI
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # 发送提示词
            stdout, stderr = process.communicate(input=prompt, timeout=self.config.timeout)

            if process.returncode != 0:
                error_msg = f"Claude CLI执行失败 (返回码: {process.returncode}): {stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # 清理输出
            response = stdout.strip()
            if not response:
                raise RuntimeError("Claude CLI返回空响应")

            logger.info(f"Claude CLI响应成功，长度: {len(response)}")
            return response

        except subprocess.TimeoutExpired:
            if 'process' in locals():
                process.kill()
            error_msg = f"Claude CLI执行超时 ({self.config.timeout}秒)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Claude CLI执行异常: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        try:
            # 简单验证包装脚本是否存在且可执行
            if isinstance(self.claude_command, list):
                file_path = self.claude_command[1]
            else:
                file_path = self.claude_command

            # 检查文件是否存在
            import os
            if os.path.exists(file_path):
                # 尝试运行包装脚本的--version参数
                if isinstance(self.claude_command, list):
                    command = self.claude_command + ['--version']
                else:
                    command = f"{self.claude_command} --version"

                result = subprocess.run(
                    command if isinstance(command, list) else command.split(),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            return False
        except Exception:
            return False

    def cleanup(self):
        """
        清理资源
        """
        logger.info("Claude CLI服务清理完成")