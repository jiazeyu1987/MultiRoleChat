#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的Anthropic LLM调用函数

基于 anthropic.Anthropic(api_key=None) 的最小LLM调用实现
无需设置API KEY，让SDK自动寻找认证方式

使用方法:
    from simple_anthropic_llm import llm_call, simple_llm

    # 最简单的调用
    response = llm_call("你好，请介绍一下人工智能")
    print(response)

    # 带参数的调用
    response = simple_llm(
        "请解释机器学习的基本概念",
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000
    )
    print(response)
"""

import anthropic
from typing import Optional


def llm_call(prompt: str) -> str:
    """
    最小的LLM调用函数

    Args:
        prompt (str): 输入提示词

    Returns:
        str: LLM响应内容

    Example:
        >>> response = llm_call("你好")
        >>> print(response)
    """
    try:
        # 创建客户端，不设置API KEY，让SDK自动寻找认证
        client = anthropic.Anthropic(api_key=None)

        # 调用API
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # 使用默认模型
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # 返回响应内容
        return response.content[0].text

    except Exception as e:
        return f"调用失败: {str(e)}"


def simple_llm(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    api_key: Optional[str] = None
) -> str:
    """
    简单的LLM调用函数，基于用户的代码风格

    Args:
        prompt (str): 输入提示词
        model (str): 模型名称，默认使用claude-3-5-sonnet
        max_tokens (int): 最大输出token数
        api_key (Optional[str]): API密钥，None表示自动寻找

    Returns:
        str: LLM响应内容

    Example:
        >>> response = simple_llm(
        ...     "请解释机器学习的基本概念",
        ...     model="claude-3-5-sonnet-20241022",
        ...     max_tokens=2000
        ... )
        >>> print(response)
    """
    try:
        # 创建客户端
        client = anthropic.Anthropic(api_key=api_key)

        # 构建消息
        messages = [{"role": "user", "content": prompt}]

        # 调用API
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages
        )

        # 提取并返回内容
        if response.content:
            return response.content[0].text
        else:
            return "未收到有效响应"

    except anthropic.APIError as e:
        return f"API错误: {str(e)}"
    except Exception as e:
        return f"调用失败: {str(e)}"


def llm_call_with_history(
    prompt: str,
    history: Optional[list] = None,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    api_key: Optional[str] = None
) -> str:
    """
    带历史记录的LLM调用函数

    Args:
        prompt (str): 当前用户输入
        history (Optional[list]): 对话历史，格式为 [{"role": "user", "content": "..."}, ...]
        model (str): 模型名称
        max_tokens (int): 最大输出token数
        api_key (Optional[str]): API密钥，None表示自动寻找

    Returns:
        str: LLM响应内容

    Example:
        >>> history = [
        ...     {"role": "user", "content": "你好"},
        ...     {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"}
        ... ]
        >>> response = llm_call_with_history("我想了解Python", history)
        >>> print(response)
    """
    try:
        # 创建客户端
        client = anthropic.Anthropic(api_key=api_key)

        # 构建消息列表
        messages = []

        # 添加历史消息
        if history:
            messages.extend(history)

        # 添加当前消息
        messages.append({"role": "user", "content": prompt})

        # 调用API
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages
        )

        # 提取并返回内容
        if response.content:
            return response.content[0].text
        else:
            return "未收到有效响应"

    except anthropic.APIError as e:
        return f"API错误: {str(e)}"
    except Exception as e:
        return f"调用失败: {str(e)}"


# 便捷函数
def quick_test():
    """
    快速测试函数，验证LLM连接是否正常
    """
    try:
        test_prompt = "请简单回答：1+1等于几？"
        response = llm_call_with_history(test_prompt)
        print("✅ LLM连接测试成功！")
        print(f"测试响应: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM连接测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 如果直接运行此文件，执行快速测试
    print("正在测试Anthropic LLM连接...")
    quick_test()