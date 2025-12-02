#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试前后端通信修复的验证脚本
发送测试请求并验证响应格式
"""

import requests
import json
import time

def test_llm_api_response():
    """测试LLM API响应格式"""
    print("=" * 60)
    print("测试LLM API响应格式")
    print("=" * 60)

    url = "http://127.0.0.1:5000/api/llm/chat"

    test_data = {
        "message": "测试前后端通信修复",
        "history": []
    }

    test_headers = {
        "Content-Type": "application/json",
        "X-User-ID": "test_fix_validation",
        "X-Session-ID": "test_fix_session"
    }

    print(f"发送测试请求到: {url}")
    print(f"测试消息: {test_data['message']}")

    try:
        response = requests.post(url, json=test_data, headers=test_headers, timeout=15)

        print(f"\n📡 HTTP响应状态:")
        print(f"   - 状态码: {response.status_code}")
        print(f"   - 响应头: {dict(response.headers)}")

        if response.status_code == 200:
            try:
                data = response.json()

                print(f"\n📋 响应数据结构:")
                print(f"   - 响应大小: {len(response.content)} bytes")
                print(f"   - 数据类型: {type(data)}")
                print(f"   - 顶级键: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

                if isinstance(data, dict):
                    print(f"\n🔍 响应内容分析:")

                    # 检查success字段
                    if 'success' in data:
                        print(f"   ✅ success字段: {data['success']}")

                    # 检查data字段
                    if 'data' in data:
                        print(f"   ✅ data字段存在: {type(data['data'])}")
                        if isinstance(data['data'], dict):
                            print(f"      - data子键: {list(data['data'].keys())}")

                            # 检查response字段
                            if 'response' in data['data']:
                                response_content = data['data']['response']
                                print(f"   ✅ data.response字段: {len(response_content)} 字符")
                                if response_content:
                                    preview = response_content[:100] + "..." if len(response_content) > 100 else response_content
                                    print(f"      - 预览: {preview}")
                                else:
                                    print(f"      - ⚠️ 内容为空")

                            # 检查其他有用字段
                            for key in ['model', 'usage', 'provider', 'response_time']:
                                if key in data['data']:
                                    print(f"   ✅ data.{key}: {data['data'][key]}")

                    # 检查直接的response字段（兼容性）
                    if 'response' in data:
                        print(f"   ✅ 直接response字段: {len(str(data['response']))} 字符")

                    # 检查直接的content字段（兼容性）
                    if 'content' in data:
                        print(f"   ✅ 直接content字段: {len(str(data['content']))} 字符")

                print(f"\n📄 完整响应数据:")
                print(json.dumps(data, indent=2, ensure_ascii=False))

                print(f"\n🎯 前端解析测试:")

                # 模拟前端解析逻辑
                response_content = data.get('data', {}).get('response') or data.get('data', {}).get('content') or data.get('response') or data.get('content')

                if response_content:
                    print(f"   ✅ 前端能够解析到回复内容")
                    print(f"   ✅ 内容长度: {len(response_content)} 字符")
                    print(f"   ✅ 修复成功！")
                else:
                    print(f"   ❌ 前端无法解析到回复内容")
                    print(f"   ❌ 修复失败！")

            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
                print(f"   📄 原始响应: {response.text[:500]}...")
        else:
            print(f"   ❌ API调用失败，状态码: {response.status_code}")
            print(f"   📄 错误响应: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"   ❌ 无法连接到API服务器")
        print(f"   💡 请确保Flask服务正在运行")
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🚀 前后端通信修复验证测试")
    print(f"⏰ 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    test_llm_api_response()

    print("\n" + "=" * 60)
    print("🎯 测试完成")
    print("=" * 60)
    print("💡 请检查前端控制台输出的调试信息")
    print("💡 如果前端能够显示LLM回复，说明修复成功！")

if __name__ == "__main__":
    main()