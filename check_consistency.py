#!/usr/bin/env python3
"""
快速验证会话剧场文档与代码的一致性
"""

import os
import re

def check_method_signatures():
    """检查关键方法签名"""
    results = []

    # 1. 检查SessionService.create_session签名
    session_service_path = os.path.join('backend', 'app', 'services', 'session_service.py')
    if os.path.exists(session_service_path):
        with open(session_service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查方法签名
        if re.search(r'def create_session\(session_data: Dict\[str, Any\]\)', content):
            results.append("✓ SessionService.create_session 方法签名正确")
        else:
            results.append("✗ SessionService.create_session 方法签名不匹配")

        # 检查是否使用了with db.session.begin_nested()
        if re.search(r'with db\.session\.begin_nested\(\):', content):
            results.append("✓ 使用了正确的事务处理")
        else:
            results.append("⚠ 未找到事务处理代码")

    # 2. 检查FlowEngineService LLM调用
    flow_service_path = os.path.join('backend', 'app', 'services', 'flow_engine_service.py')
    if os.path.exists(flow_service_path):
        with open(flow_service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查HTTP请求调用
        if re.search(r"requests\.post\('http://localhost:5010/api/llm/chat'", content):
            results.append("✓ FlowEngineService使用HTTP API调用LLM")
        else:
            results.append("✗ FlowEngineService LLM调用方式不匹配")

        # 检查_build_simple_prompt方法
        if re.search(r'def _build_simple_prompt\(', content):
            results.append("✓ 存在简化提示词构建方法")
        else:
            results.append("✗ 缺少简化提示词构建方法")

    # 3. 检查API层调用
    api_path = os.path.join('backend', 'app', 'api', 'sessions.py')
    if os.path.exists(api_path):
        with open(api_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if re.search(r'SessionService\.create_session\(json_data\)', content):
            results.append("✓ API层正确调用SessionService.create_session")
        else:
            results.append("✗ API层调用方式不匹配")

    return results

def check_data_models():
    """检查数据模型字段"""
    results = []

    # 检查Session模型
    session_model_path = os.path.join('backend', 'app', 'models', 'session.py')
    if os.path.exists(session_model_path):
        with open(session_model_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键字段
        checks = [
            (r'topic = db\.Column\(db\.String\(200\), nullable=False\)', "✓ Session.topic 字段类型正确"),
            (r'error_reason = db\.Column\(db\.String\(500\)\)', "✓ Session.error_reason 字段类型正确"),
            (r'flow_snapshot_dict.*property', "✓ Session有flow_snapshot_dict属性"),
            (r'roles_snapshot_dict.*property', "✓ Session有roles_snapshot_dict属性"),
        ]

        for pattern, message in checks:
            if re.search(pattern, content):
                results.append(message)
            else:
                results.append(f"✗ {message.split(' ')[1]} 字段检查失败")

    return results

def check_frontend_implementation():
    """检查前端实现"""
    results = []

    frontend_path = os.path.join('fronted', 'src', 'MultiRoleDialogSystem.tsx')
    if os.path.exists(frontend_path):
        with open(frontend_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键实现
        checks = [
            (r'role_mappings\.reduce.*acc\[mapping\.role_ref\]', "✓ 前端正确转换role_mappings格式"),
            (r'const loadData = async \(\)', "✓ 前端使用loadData函数而非轮询"),
            (r'await sessionApi\.getSession\(sessionId\)', "✓ 前端正确调用session API"),
        ]

        for pattern, message in checks:
            if re.search(pattern, content, re.DOTALL):
                results.append(message)
            else:
                results.append(f"⚠ {message.split(' ')[1]} 实现可能不匹配")

    return results

def main():
    print("=== 会话剧场文档与代码一致性验证 ===\n")

    all_results = []

    # 检查方法签名
    print("1. 方法签名检查:")
    method_results = check_method_signatures()
    all_results.extend(method_results)
    for result in method_results:
        print(f"   {result}")

    print("\n2. 数据模型检查:")
    model_results = check_data_models()
    all_results.extend(model_results)
    for result in model_results:
        print(f"   {result}")

    print("\n3. 前端实现检查:")
    frontend_results = check_frontend_implementation()
    all_results.extend(frontend_results)
    for result in frontend_results:
        print(f"   {result}")

    print(f"\n=== 验证总结 ===")
    success_count = len([r for r in all_results if r.startswith("✓")])
    warning_count = len([r for r in all_results if r.startswith("⚠")])
    error_count = len([r for r in all_results if r.startswith("✗")])

    print(f"✓ 通过: {success_count}")
    print(f"⚠ 警告: {warning_count}")
    print(f"✗ 失败: {error_count}")

    if error_count == 0:
        print("\n🎉 所有关键检查都通过！文档与代码高度一致。")
    else:
        print(f"\n⚠️  发现 {error_count} 个不匹配项，需要进一步检查。")

if __name__ == "__main__":
    main()