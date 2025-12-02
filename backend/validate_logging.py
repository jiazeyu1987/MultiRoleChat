#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志系统验证测试脚本

用于验证日志修复是否生效，确认日志文件能够正确生成和写入
测试Flask应用日志和LLM专用日志系统
"""

import os
import sys
import time
import requests
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_log_directory():
    """检查日志目录状态"""
    print("=" * 60)
    print("[检查] 日志目录状态")
    print("=" * 60)

    log_dir = Path("logs")

    if log_dir.exists():
        print(f"[OK] 日志目录存在: {log_dir.absolute()}")

        # 列出目录内容
        log_files = list(log_dir.glob("*"))
        if log_files:
            print(f"[INFO] 发现 {len(log_files)} 个日志文件:")
            for file in log_files:
                size = file.stat().st_size if file.is_file() else 0
                modified = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   - {file.name} ({size} bytes, 修改时间: {modified})")
        else:
            print("[WARN] 日志目录存在但没有文件")
    else:
        print(f"[ERROR] 日志目录不存在: {log_dir.absolute()}")
        print("[ACTION] 尝试创建日志目录...")
        try:
            log_dir.mkdir(exist_ok=True)
            print(f"[OK] 日志目录创建成功: {log_dir.absolute()}")
        except Exception as e:
            print(f"[ERROR] 创建日志目录失败: {e}")

    return log_dir.exists()

def test_flask_logging():
    """测试Flask应用日志"""
    print("\n" + "=" * 60)
    print("🔧 测试Flask应用日志")
    print("=" * 60)

    try:
        # 导入Flask应用配置
        from app.config import config
        app_config = config['default']

        print(f"📋 Flask日志配置:")
        print(f"   - LOG_LEVEL: {app_config.LOG_LEVEL}")
        print(f"   - LOG_FILE: {app_config.LOG_FILE}")
        print(f"   - LOG_TO_FILE: {app_config.LOG_TO_FILE}")

        # 测试环境变量
        log_to_file = os.environ.get('LOG_TO_FILE', 'true').lower()
        print(f"   - 环境变量 LOG_TO_FILE: {log_to_file}")

        # 创建测试日志条目
        import logging
        test_logger = logging.getLogger('test_validation')
        test_logger.setLevel(logging.INFO)

        # 创建文件处理器测试
        log_file_path = app_config.LOG_FILE
        log_dir = os.path.dirname(log_file_path)

        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        test_logger.addHandler(file_handler)

        test_message = f"日志验证测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        test_logger.info(test_message)

        # 检查日志是否写入成功
        time.sleep(0.5)  # 等待写入

        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if test_message in content:
                    print(f"✅ Flask日志写入测试成功")
                    print(f"   📄 日志文件: {log_file_path}")
                    print(f"   📝 测试消息已写入")
                else:
                    print(f"⚠️  日志文件存在但测试消息未找到")
        else:
            print(f"❌ Flask日志文件创建失败: {log_file_path}")

        # 清理处理器
        test_logger.removeHandler(file_handler)
        file_handler.close()

    except Exception as e:
        print(f"❌ Flask日志测试失败: {e}")

def test_llm_special_logger():
    """测试LLM专用日志系统"""
    print("\n" + "=" * 60)
    print("🤖 测试LLM专用日志系统")
    print("=" * 60)

    try:
        from app.utils.llm_logger import get_llm_logger

        llm_logger = get_llm_logger()

        print(f"📋 LLM日志系统信息:")
        print(f"   - 日志文件路径: {llm_logger.get_log_file_path()}")
        print(f"   - 当前日志大小: {llm_logger.get_log_size()} bytes")

        # 创建测试日志条目
        test_request_id = f"TEST-{int(time.time() * 1000)}"
        test_user_id = "test_validation_user"
        test_session_id = "test_validation_session"

        print(f"\n🧪 执行LLM日志测试...")
        print(f"   - 请求ID: {test_request_id}")

        # 记录测试日志
        llm_logger.log_request_start(
            request_id=test_request_id,
            user_id=test_user_id,
            session_id=test_session_id,
            test_type="validation"
        )

        llm_logger.log_api_call(
            request_id=test_request_id,
            layer="TEST",
            action="验证日志功能",
            test_timestamp=datetime.now().isoformat()
        )

        llm_logger.log_content(
            request_id=test_request_id,
            content_type="测试消息",
            content="这是一个日志验证测试消息，用于验证LLM日志系统是否正常工作"
        )

        llm_logger.log_request_end(
            request_id=test_request_id,
            success=True,
            response_time=0.001,
            response_length=50,
            test_result="success"
        )

        # 检查日志是否写入
        time.sleep(0.5)  # 等待写入

        log_file_path = llm_logger.get_log_file_path()
        if log_file_path and os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if test_request_id in content:
                    print(f"✅ LLM专用日志测试成功")
                    print(f"   📄 日志文件: {log_file_path}")
                    print(f"   📝 测试请求ID已写入日志")
                else:
                    print(f"⚠️  LLM日志文件存在但测试内容未找到")
        else:
            print(f"❌ LLM日志文件未找到: {log_file_path}")

    except Exception as e:
        print(f"❌ LLM日志测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_api_request_logging():
    """测试API请求日志记录"""
    print("\n" + "=" * 60)
    print("🌐 测试API请求日志记录")
    print("=" * 60)

    # 测试URL
    test_url = "http://127.0.0.1:5000/api/llm/chat"

    print(f"📡 发送测试API请求到: {test_url}")

    try:
        test_data = {
            "message": "日志验证测试消息",
            "history": []
        }

        test_headers = {
            "Content-Type": "application/json",
            "X-User-ID": "log_validation_test",
            "X-Session-ID": "validation_session"
        }

        print(f"📤 请求内容:")
        print(f"   - 消息: {test_data['message']}")
        print(f"   - 用户ID: {test_headers['X-User-ID']}")
        print(f"   - 会话ID: {test_headers['X-Session-ID']}")

        response = requests.post(test_url, json=test_data, headers=test_headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ API请求成功")
            print(f"   - 响应状态: {response.status_code}")
            print(f"   - 响应数据: {result.get('success', 'unknown')}")

            if result.get('data') and result['data'].get('response'):
                response_length = len(result['data']['response'])
                print(f"   - 响应长度: {response_length} 字符")
        else:
            print(f"⚠️  API请求返回非200状态码")
            print(f"   - 响应状态: {response.status_code}")
            print(f"   - 响应内容: {response.text[:200]}...")

        # 等待日志写入
        time.sleep(2)

    except requests.exceptions.ConnectionError:
        print(f"⚠️  无法连接到API服务器")
        print(f"   请确保Flask服务正在运行")
    except requests.exceptions.Timeout:
        print(f"⚠️  API请求超时")
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def check_log_files_after_tests():
    """检查测试后的日志文件状态"""
    print("\n" + "=" * 60)
    print("📊 检查测试后的日志文件状态")
    print("=" * 60)

    log_dir = Path("logs")

    if log_dir.exists():
        log_files = list(log_dir.glob("*"))
        if log_files:
            print(f"📄 发现 {len(log_files)} 个日志文件:")

            for file in log_files:
                size = file.stat().st_size if file.is_file() else 0
                modified = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')

                print(f"\n📁 文件: {file.name}")
                print(f"   📏 大小: {size} bytes")
                print(f"   🕒 修改时间: {modified}")

                # 读取最后几行内容
                if file.is_file() and size > 0:
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if lines:
                                print(f"   📝 总行数: {len(lines)}")
                                print(f"   🔍 最后3行内容:")
                                for i, line in enumerate(lines[-3:], len(lines) - 2):
                                    preview = line.strip()[:100]
                                    if len(line.strip()) > 100:
                                        preview += "..."
                                    print(f"     {i}: {preview}")
                    except Exception as e:
                        print(f"   ❌ 读取文件失败: {e}")
        else:
            print("⚠️  仍然没有日志文件")
    else:
        print("❌ 日志目录不存在")

def main():
    """主测试函数"""
    print("🚀 MultiRoleChat 日志系统验证测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 工作目录: {os.getcwd()}")

    # 1. 检查日志目录
    dir_ok = check_log_directory()

    if not dir_ok:
        print("\n❌ 日志目录检查失败，无法继续测试")
        return

    # 2. 测试Flask日志
    test_flask_logging()

    # 3. 测试LLM专用日志
    test_llm_special_logger()

    # 4. 测试API请求日志
    test_api_request_logging()

    # 5. 检查测试后的日志文件状态
    check_log_files_after_tests()

    print("\n" + "=" * 60)
    print("🎯 测试总结")
    print("=" * 60)
    print("1. ✅ 日志目录检查完成")
    print("2. ✅ Flask日志系统测试完成")
    print("3. ✅ LLM专用日志测试完成")
    print("4. ✅ API请求日志测试完成")
    print("5. ✅ 日志文件状态检查完成")
    print("\n💡 如果以上测试都显示成功，说明日志系统已正常工作")
    print("📁 请检查 logs/ 目录查看生成的日志文件")

if __name__ == "__main__":
    main()