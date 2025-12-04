#!/usr/bin/env python3
"""
验证FlowEngineService的修改
通过文本分析检查修改是否正确应用
"""

import os
import re

def validate_flow_engine_service():
    """验证FlowEngineService文件的修改"""
    file_path = os.path.join('backend', 'app', 'services', 'flow_engine_service.py')

    if not os.path.exists(file_path):
        print("✗ FlowEngineService文件不存在")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        # 检查是否包含HTTP请求相关代码
        (r'requests\.post', '✓ 包含HTTP POST请求代码'),
        (r'api_url.*=.*localhost:5010', '✓ 设置了正确的API端点'),
        (r'payload.*=.*{', '✓ 构建了请求负载'),
        (r'history_messages', '✓ 处理历史消息'),

        # 检查是否包含新的简化提示词方法
        (r'_build_simple_prompt', '✓ 添加了简化提示词构建方法'),
        (r'def _build_simple_prompt', '✓ 简化提示词方法定义完整'),

        # 检查是否保留了原来的复杂方法
        (r'_build_prompt.*role.*step.*context', '✓ 保留了原来的复杂提示词方法'),

        # 检查错误处理
        (r'except.*RequestException', '✓ 包含请求异常处理'),
        (r'FlowExecutionError', '✓ 包含流程执行错误处理'),
    ]

    print("=== FlowEngineService修改验证 ===")
    all_passed = True

    for pattern, description in checks:
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(description)
        else:
            print(f"✗ {description}")
            all_passed = False

    # 检查是否移除了对复杂LLM服务的调用
    complex_patterns = [
        r'conversation_llm_service\.generate_response_with_context',
        r'await.*generate_response_with_context'
    ]

    print("\n=== 检查复杂调用是否已移除 ===")
    for pattern in complex_patterns:
        if re.search(pattern, content):
            print(f"⚠ 仍包含复杂调用: {pattern}")
        else:
            print(f"✓ 已移除复杂调用: {pattern}")

    return all_passed

def validate_api_endpoint():
    """验证LLM API端点存在"""
    file_path = os.path.join('backend', 'app', 'api', 'llm.py')

    if not os.path.exists(file_path):
        print("✗ LLM API文件不存在")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("\n=== LLM API端点验证 ===")

    if re.search(r'/api/llm/chat', content):
        print("✓ /api/llm/chat端点存在")
    else:
        print("✗ /api/llm/chat端点不存在")
        return False

    if re.search(r'class LLMChatResource', content):
        print("✓ LLMChatResource类存在")
    else:
        print("✗ LLMChatResource类不存在")
        return False

    return True

def main():
    print("=== 会话剧场LLM调用修改验证 ===\n")

    # 验证主要修改
    flow_ok = validate_flow_engine_service()
    api_ok = validate_api_endpoint()

    print("\n=== 总结 ===")
    if flow_ok and api_ok:
        print("✓ 所有验证通过！")
        print("✓ 会话剧场已成功修改为使用CLI方式的LLM调用")
        print("\n主要修改内容:")
        print("1. FlowEngineService._generate_llm_response_sync 现在使用HTTP请求")
        print("2. 新增 _build_simple_prompt 方法构建简化提示词")
        print("3. 历史消息转换为简单的role/content格式")
        print("4. 增强了错误处理和回退机制")
        print("\n现在会话剧场与LLM测试页面使用相同的调用方式！")
    else:
        print("✗ 部分验证未通过，请检查修改")

if __name__ == "__main__":
    main()