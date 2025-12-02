#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiRoleChat LLM日志实时查看工具

用于实时查看和筛选LLM相关的日志输出
支持按请求ID、用户ID、日志级别等条件进行筛选
"""

import os
import sys
import time
import argparse
import re
from datetime import datetime
from typing import Optional, List, Dict, Set
import threading
import requests

class LLMLogViewer:
    """LLM日志查看器"""

    def __init__(self, log_file: str = None, follow: bool = True, filter_patterns: Dict[str, str] = None):
        """
        初始化日志查看器

        Args:
            log_file: 日志文件路径，默认为 logs/app.log
            follow: 是否跟踪实时输出
            filter_patterns: 筛选模式字典
        """
        self.log_file = log_file or "logs/app.log"
        self.follow = follow
        self.filter_patterns = filter_patterns or {}
        self.running = True
        self.line_count = 0
        self.match_count = 0

        # 颜色配置
        self.colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'bold': '\033[1m',
            'reset': '\033[0m'
        }

    def colorize(self, text: str, color: str) -> str:
        """给文本添加颜色"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"

    def print_header(self):
        """打印查看器头部信息"""
        print(self.colorize("=" * 80, 'cyan'))
        print(self.colorize("MultiRoleChat LLM日志实时查看器", 'bold'))
        print(f"日志文件: {self.log_file}")
        print(f"筛选条件: {self.filter_patterns if self.filter_patterns else '无'}")
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def matches_filters(self, line: str) -> bool:
        """检查行是否匹配筛选条件"""
        if not self.filter_patterns:
            return True

        for filter_type, pattern in self.filter_patterns.items():
            if filter_type == "request_id":
                if f"LLM-REQ-ID: {pattern}" in line:
                    return True
            elif filter_type == "user_id":
                if f"user_id={pattern}" in line or f"X-User-ID: {pattern}" in line:
                    return True
            elif filter_type == "session_id":
                if f"session_id={pattern}" in line or f"X-Session-ID: {pattern}" in line:
                    return True
            elif filter_type == "layer":
                if f"{pattern.upper()}_LAYER" in line:
                    return True
            elif filter_type == "error":
                if "ERROR" in line or "error" in line.lower():
                    return True
            elif filter_type == "keyword":
                if pattern.lower() in line.lower():
                    return True

        return False

    def format_line(self, line: str) -> str:
        """格式化日志行输出"""
        line = line.rstrip()

        # 请求ID高亮
        if "LLM-REQ-ID:" in line:
            # 提取请求ID
            req_id_match = re.search(r'LLM-REQ-ID: ([^\s\]]+)', line)
            if req_id_match:
                req_id = req_id_match.group(1)
                line = line.replace(req_id, self.colorize(req_id, 'magenta'))

        # 层级高亮
        if "API_LAYER" in line:
            line = line.replace("API_LAYER", self.colorize("API_LAYER", 'blue'))
        elif "MANAGER" in line:
            line = line.replace("MANAGER", self.colorize("MANAGER", 'yellow'))
        elif "CORE" in line:
            line = line.replace("CORE", self.colorize("CORE", 'green'))

        # 错误高亮
        if "ERROR" in line or "error" in line.lower():
            line = self.colorize(line, 'red')
        elif "WARNING" in line or "warning" in line.lower():
            line = self.colorize(line, 'yellow')

        # 成功高亮
        if "success" in line.lower() or "成功" in line:
            line = self.colorize(line, 'green')

        return line

    def read_log_file(self):
        """读取日志文件"""
        if not os.path.exists(self.log_file):
            print(f"[WARNING] 日志文件不存在: {self.log_file}")
            print(f"[INFO] 提示: 请确保Flask服务正在运行并配置了文件日志")
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # 移动到文件末尾
                f.seek(0, 2)

                print(f"[INFO] 开始监控日志文件: {self.log_file}")
                print("[INFO] 输入 'q' 或 'quit' 退出，'h' 查看帮助\n")

                while self.running:
                    line = f.readline()
                    if line:
                        self.line_count += 1
                        if self.matches_filters(line):
                            self.match_count += 1
                            formatted_line = self.format_line(line)
                            print(f"[{self.line_count:6d}] {formatted_line}")
                    else:
                        if not self.follow:
                            break
                        time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"\n[INFO] 停止监控，共处理 {self.line_count} 行，匹配 {self.match_count} 行")
        except Exception as e:
            print(f"[ERROR] 读取日志文件出错: {e}")

    def test_llm_api(self):
        """测试LLM API调用以生成日志"""
        print("[TEST] 发送测试LLM请求...")
        try:
            test_url = "http://127.0.0.1:5000/api/llm/chat"
            test_data = {
                "message": "这是一个测试消息，用于验证日志功能",
                "history": []
            }
            test_headers = {
                "Content-Type": "application/json",
                "X-User-ID": "test_log_viewer",
                "X-Session-ID": "test_session_log"
            }

            response = requests.post(test_url, json=test_data, headers=test_headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                print(f"[SUCCESS] 测试请求成功，响应长度: {len(result.get('data', {}).get('response', ''))}")
                print(f"[INFO] 请求信息: user_id=test_log_viewer, session_id=test_session_log")
            else:
                print(f"[ERROR] 测试请求失败: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 测试请求异常: {e}")
        except Exception as e:
            print(f"[ERROR] 测试出错: {e}")

    def show_stats(self):
        """显示统计信息"""
        print(f"\n[STATS] 日志统计:")
        print(f"   总行数: {self.line_count}")
        print(f"   匹配行数: {self.match_count}")
        if self.line_count > 0:
            print(f"   匹配率: {(self.match_count/self.line_count*100):.1f}%")
        else:
            print("   匹配率: 0%")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MultiRoleChat LLM日志查看器")

    parser.add_argument("-f", "--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    parser.add_argument("--no-follow", action="store_true", help="不跟踪实时输出")
    parser.add_argument("--request-id", help="按请求ID筛选")
    parser.add_argument("--user-id", help="按用户ID筛选")
    parser.add_argument("--session-id", help="按会话ID筛选")
    parser.add_argument("--layer", choices=["API", "MANAGER", "CORE"], help="按层级筛选")
    parser.add_argument("--error-only", action="store_true", help="只显示错误日志")
    parser.add_argument("--keyword", help="按关键词筛选")
    parser.add_argument("--test-api", action="store_true", help="发送测试API请求")

    args = parser.parse_args()

    # 构建筛选条件
    filter_patterns = {}
    if args.request_id:
        filter_patterns["request_id"] = args.request_id
    if args.user_id:
        filter_patterns["user_id"] = args.user_id
    if args.session_id:
        filter_patterns["session_id"] = args.session_id
    if args.layer:
        filter_patterns["layer"] = args.layer
    if args.error_only:
        filter_patterns["error"] = "true"
    if args.keyword:
        filter_patterns["keyword"] = args.keyword

    # 创建查看器
    viewer = LLMLogViewer(
        log_file=args.file,
        follow=not args.no_follow,
        filter_patterns=filter_patterns
    )

    # 显示头部信息
    viewer.print_header()

    # 如果需要，发送测试请求
    if args.test_api:
        viewer.test_llm_api()
        time.sleep(2)  # 等待日志写入
        print("\n")

    # 开始读取日志
    try:
        viewer.read_log_file()
    except KeyboardInterrupt:
        viewer.show_stats()
        print("\n[INFO] 再见!")

if __name__ == "__main__":
    main()