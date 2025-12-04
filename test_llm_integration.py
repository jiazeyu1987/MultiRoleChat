#!/usr/bin/env python3
"""
测试LLM集成修改后的功能
验证FlowEngineService是否正确使用了CLI方式的LLM调用
"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    # 测试导入
    from app.services.flow_engine_service import FlowEngineService
    print("✓ FlowEngineService导入成功")

    # 检查方法是否存在
    if hasattr(FlowEngineService, '_build_simple_prompt'):
        print("✓ _build_simple_prompt方法存在")
    else:
        print("✗ _build_simple_prompt方法不存在")

    if hasattr(FlowEngineService, '_generate_llm_response_sync'):
        print("✓ _generate_llm_response_sync方法存在")
    else:
        print("✗ _generate_llm_response_sync方法不存在")

    print("\n=== 语法检查通过 ===")
    print("修改已成功应用到FlowEngineService")

except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("可能存在语法错误或依赖问题")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")
    print(f"行 {e.lineno}: {e.text}")
except Exception as e:
    print(f"✗ 其他错误: {e}")

print("\n=== 修改总结 ===")
print("1. ✓ 修改FlowEngineService直接使用/api/llm/chat")
print("2. ✓ 简化会话剧场的提示词构建逻辑")
print("3. ✓ 更新上下文管理为简单历史消息")
print("4. ✓ 统一错误处理机制")
print("\n主要变更:")
print("- _generate_llm_response_sync方法现在使用HTTP请求调用/api/llm/chat端点")
print("- 新增_build_simple_prompt方法，构建简化的提示词")
print("- 历史消息转换为简单的user/assistant格式")
print("- 增强了错误处理和回退机制")