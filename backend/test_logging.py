#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试请求追踪和日志功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.request_tracker import RequestTracker, log_llm_info, generate_request_id

def test_request_tracker():
    """测试请求追踪功能"""
    print("=== 测试请求追踪功能 ===")

    # 生成请求ID
    request_id = generate_request_id()
    print(f"生成的请求ID: {request_id}")

    # 测试日志格式化
    log_message = RequestTracker.format_log(
        "TEST",
        "这是一个测试日志消息",
        request_id,
        extra_data={"message_length": 50, "test_param": "test_value"}
    )
    print(f"格式化日志: {log_message}")

    # 测试上下文管理器
    print("\n=== 测试上下文管理器 ===")
    with RequestTracker.track_request(
        request_id=request_id,
        layer="TEST",
        user_id="test_user",
        session_id="test_session"
    ) as context:
        print(f"上下文请求ID: {context.request_id}")
        print(f"上下文层级: {context.layer}")

        # 在上下文中记录日志
        log_llm_info("TEST", "在上下文中记录的日志", request_id=request_id)

        # 测试获取当前上下文
        current_context = RequestTracker.get_context()
        print(f"当前上下文请求ID: {current_context.request_id if current_context else 'None'}")

def test_direct_logging():
    """测试直接日志记录"""
    print("\n=== 测试直接日志记录 ===")

    request_id = generate_request_id()

    # 测试不同类型的日志
    log_llm_info("TEST", "信息级别日志", request_id, param1="value1", param2=123)
    log_llm_info("TEST", "带内容的日志", request_id, content="这是一个很长的测试内容，用来测试内容预览功能是否正常工作..." * 5)

    print("直接日志记录完成")

if __name__ == "__main__":
    test_request_tracker()
    test_direct_logging()
    print("\n=== 测试完成 ===")