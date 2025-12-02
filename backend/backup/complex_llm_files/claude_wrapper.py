#!/usr/bin/env python3
"""
Claude CLI Wrapper
简单的CLI包装器，用于与现有的Claude CLI工具进行通信
"""
import sys
import argparse
import os
import subprocess
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_claude_cli(prompt_text):
    """
    调用Claude CLI工具

    Args:
        prompt_text (str): 用户输入的提示词

    Returns:
        str: Claude的回复
    """
    try:
        # 尝试调用系统中的claude命令
        cmd = ['claude']

        # 启动子进程
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # 发送提示词并获取回复
        stdout, stderr = process.communicate(input=prompt_text, timeout=60)

        if process.returncode != 0:
            logger.error(f"Claude CLI执行失败: {stderr}")
            return f"错误: Claude CLI执行失败 - {stderr}"

        response = stdout.strip()
        if not response:
            return "抱歉，我没有收到有效的回复。"

        return response

    except subprocess.TimeoutExpired:
        process.kill()
        logger.error("Claude CLI执行超时")
        return "错误: Claude CLI执行超时"

    except FileNotFoundError:
        logger.warning("Claude CLI命令未找到，使用演示模式")
        return get_demo_response(prompt_text)

    except Exception as e:
        logger.error(f"Claude CLI调用异常: {str(e)}")
        return f"错误: Claude CLI调用异常 - {str(e)}"


def get_demo_response(prompt_text):
    """
    当Claude CLI不可用时，提供演示响应

    Args:
        prompt_text (str): 用户输入的提示词

    Returns:
        str: 演示回复
    """
    # 简单的关键词匹配来生成演示响应
    prompt_lower = prompt_text.lower()

    if '你好' in prompt_lower or 'hello' in prompt_lower:
        return "你好！我是Claude AI助手。很高兴为您服务。请问有什么可以帮助您的吗？"

    elif '测试' in prompt_lower or 'test' in prompt_lower:
        return "测试成功！系统运行正常。这是一个演示响应，因为当前未安装Claude CLI工具。"

    elif '天气' in prompt_lower:
        return "今天天气晴朗，温度适宜。适合外出活动。记得根据天气情况适当增减衣物。"

    elif '帮助' in prompt_lower or 'help' in prompt_lower:
        return """我可以帮助您：
        - 回答问题和提供建议
        - 协助编写和优化代码
        - 分析文档和总结内容
        - 进行创意写作和头脑风暴
        - 解答技术问题

        请告诉我您需要什么帮助！"""

    elif '谢谢' in prompt_lower or 'thank' in prompt_lower:
        return "不客气！很高兴能帮到您。如果还有其他问题，随时告诉我。"

    elif '再见' in prompt_lower or 'bye' in prompt_lower:
        return "再见！期待下次为您服务。祝您有美好的一天！"

    else:
        # 默认响应
        return """感谢您的提问！这是一个演示响应。

当前系统运行在演示模式下，因为未检测到Claude CLI工具。要获得完整的AI助手功能，请：

1. 安装Claude CLI工具
2. 确保其在系统PATH中可用
3. 重启服务

演示模式下，我会根据关键词提供简单的预设回复。系统架构和集成代码已完全就绪。"""

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Claude CLI包装器')
    parser.add_argument('--version', action='version', version='Claude CLI Wrapper 1.0')

    args = parser.parse_args()

    # 从stdin读取输入
    try:
        prompt_text = sys.stdin.read().strip()
        if not prompt_text:
            logger.error("未收到输入文本")
            print("错误: 未收到输入文本", file=sys.stderr)
            sys.exit(1)

        # 调用Claude CLI
        response = run_claude_cli(prompt_text)

        # 输出结果
        print(response)

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行异常: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()