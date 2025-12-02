#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志系统验证测试脚本 - 简化版
用于验证日志修复是否生效
"""

import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_log_directory():
    """测试日志目录"""
    print("=" * 60)
    print("日志目录检查")
    print("=" * 60)

    log_dir = Path("logs")
    if not log_dir.exists():
        print("创建日志目录...")
        log_dir.mkdir(exist_ok=True)

    print(f"日志目录: {log_dir.absolute()}")

    # 检查现有文件
    files = list(log_dir.glob("*"))
    print(f"现有日志文件数量: {len(files)}")
    for f in files:
        size = f.stat().st_size if f.is_file() else 0
        print(f"  - {f.name} ({size} bytes)")

    return log_dir.exists()

def test_flask_config():
    """测试Flask配置"""
    print("\n" + "=" * 60)
    print("Flask日志配置检查")
    print("=" * 60)

    try:
        from app.config import config
        app_config = config['default']

        print(f"LOG_LEVEL: {app_config.LOG_LEVEL}")
        print(f"LOG_FILE: {app_config.LOG_FILE}")
        print(f"LOG_TO_FILE: {app_config.LOG_TO_FILE}")

        # 检查环境变量
        env_log_to_file = os.environ.get('LOG_TO_FILE', 'true')
        print(f"环境变量 LOG_TO_FILE: {env_log_to_file}")

        return True
    except Exception as e:
        print(f"配置检查失败: {e}")
        return False

def test_llm_logger():
    """测试LLM日志系统"""
    print("\n" + "=" * 60)
    print("LLM日志系统测试")
    print("=" * 60)

    try:
        from app.utils.llm_logger import get_llm_logger

        logger = get_llm_logger()
        print(f"LLM日志文件: {logger.get_log_file_path()}")
        print(f"当前日志大小: {logger.get_log_size()} bytes")

        # 写入测试日志
        test_id = f"TEST-{int(time.time())}"
        logger.log_info(test_id, "日志验证测试", "VALIDATION", test_type="validation")

        print(f"写入测试日志，请求ID: {test_id}")

        # 等待写入并检查
        time.sleep(1)
        log_path = logger.get_log_file_path()
        if log_path and os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if test_id in content:
                    print("[OK] LLM日志写入成功")
                    return True
                else:
                    print("[FAIL] 测试ID未在日志中找到")
                    return False
        else:
            print("[FAIL] LLM日志文件不存在")
            return False

    except Exception as e:
        print(f"LLM日志测试失败: {e}")
        return False

def test_api_call():
    """测试API调用"""
    print("\n" + "=" * 60)
    print("API调用测试")
    print("=" * 60)

    url = "http://127.0.0.1:5000/api/llm/chat"

    try:
        data = {"message": "日志验证测试", "history": []}
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": "log_validation_test",
            "X-Session-ID": "validation_session"
        }

        print(f"发送请求到: {url}")
        response = requests.post(url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print("[OK] API调用成功")
            print(f"响应状态: {result.get('success', 'unknown')}")
            return True
        else:
            print(f"[WARN] API返回状态码: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("[WARN] 无法连接到API服务器，请确保Flask服务正在运行")
        return False
    except Exception as e:
        print(f"[WARN] API测试失败: {e}")
        return False

def final_check():
    """最终检查"""
    print("\n" + "=" * 60)
    print("最终结果检查")
    print("=" * 60)

    log_dir = Path("logs")
    if log_dir.exists():
        files = list(log_dir.glob("*"))
        print(f"日志文件总数: {len(files)}")

        for f in files:
            if f.is_file():
                size = f.stat().st_size
                modified = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n文件: {f.name}")
                print(f"  大小: {size} bytes")
                print(f"  修改时间: {modified}")

                # 显示最后几行
                if size > 0:
                    try:
                        with open(f, 'r', encoding='utf-8') as file:
                            lines = file.readlines()
                            print(f"  总行数: {len(lines)}")
                            if lines:
                                print("  最后2行:")
                                for line in lines[-2:]:
                                    preview = line.strip()[:80]
                                    print(f"    {preview}")
                    except Exception as e:
                        print(f"  读取失败: {e}")
    else:
        print("日志目录不存在")

def main():
    """主函数"""
    print("MultiRoleChat 日志系统验证测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作目录: {os.getcwd()}")

    results = []

    # 1. 目录检查
    results.append(("日志目录", test_log_directory()))

    # 2. 配置检查
    results.append(("Flask配置", test_flask_config()))

    # 3. LLM日志测试
    results.append(("LLM日志系统", test_llm_logger()))

    # 4. API测试
    results.append(("API调用", test_api_call()))

    # 最终检查
    final_check()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    success_count = sum(1 for _, result in results if result)
    total_count = len(results)

    print(f"\n通过测试: {success_count}/{total_count}")

    if success_count == total_count:
        print("所有测试通过！日志系统正常工作。")
    else:
        print("部分测试失败，请检查相关配置。")

    print("\n请检查 logs/ 目录查看生成的日志文件。")

if __name__ == "__main__":
    main()