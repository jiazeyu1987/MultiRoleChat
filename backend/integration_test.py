#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端集成测试

验证Advanced Dialog System的完整功能集成
"""

import sys
import os
import logging
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.session import Session
from app.models.role import Role
from app.models.flow import FlowTemplate, FlowStep
from app.services.security_service import get_api_key_manager, PermissionLevel
from app.services.rate_limit_service import get_rate_limit_service, RateLimitType
from app.services.cache_service import get_cache_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """集成测试套件"""

    def __init__(self):
        """初始化测试套件"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.base_url = "http://localhost:5000/api"
        self.test_results = []
        self.session_id = None

    def log_test_result(self, test_name: str, passed: bool, details: str = "", duration: float = 0):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.test_results.append(result)

        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name} ({duration:.3f}s) - {details}")

    def setup_test_data(self):
        """设置测试数据"""
        try:
            with self.app.app_context():
                logger.info("🔧 设置测试数据...")

                # 创建测试角色
                test_roles = [
                    {
                        'name': '教师',
                        'description': '负责教学和指导学生的老师',
                        'prompt': '你是一位经验丰富的教师，擅长用简单易懂的方式解释复杂概念。'
                    },
                    {
                        'name': '学生',
                        'description': '正在学习的学生',
                        'prompt': '你是一个好奇的学生，喜欢提问并积极参与讨论。'
                    }
                ]

                for role_data in test_roles:
                    existing_role = Role.query.filter_by(name=role_data['name']).first()
                    if not existing_role:
                        role = Role(**role_data)
                        db.session.add(role)

                # 创建测试流程模板
                existing_flow = FlowTemplate.query.filter_by(name='测试问答流程').first()
                if not existing_flow:
                    flow_template = FlowTemplate(
                        name='测试问答流程',
                        description='用于集成测试的简单问答流程',
                        config={
                            'steps': [
                                {
                                    'name': '开始对话',
                                    'type': 'dialogue',
                                    'speaker_role': '教师',
                                    'prompt': '同学们好！今天我们来学习一下人工智能的基本概念。',
                                    'next_step_condition': None
                                },
                                {
                                    'name': '学生提问',
                                    'type': 'dialogue',
                                    'speaker_role': '学生',
                                    'prompt': '老师，我对AI很感兴趣，能简单介绍一下吗？',
                                    'next_step_condition': None
                                },
                                {
                                    'name': '老师回答',
                                    'type': 'dialogue',
                                    'speaker_role': '教师',
                                    'prompt': '当然可以！人工智能就是让计算机像人一样思考和行动的技术。',
                                    'next_step_condition': None
                                }
                            ]
                        }
                    )
                    db.session.add(flow_template)

                db.session.commit()
                logger.info("✅ 测试数据设置完成")

                return True

        except Exception as e:
            logger.error(f"❌ 设置测试数据失败: {str(e)}")
            return False

    def test_api_endpoints(self) -> bool:
        """测试API端点"""
        start_time = time.time()

        try:
            logger.info("🌐 测试API端点...")

            # 测试健康检查
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                assert health_data.get('status') == 'healthy'
                self.log_test_result("API健康检查", True, "API服务正常")
            else:
                self.log_test_result("API健康检查", False, f"状态码: {response.status_code}")
                return False

            # 测试角色列表
            response = requests.get(f"{self.base_url}/roles", timeout=10)
            if response.status_code == 200:
                roles_data = response.json()
                assert isinstance(roles_data, list)
                self.log_test_result("角色列表API", True, f"获取到 {len(roles_data)} 个角色")
            else:
                self.log_test_result("角色列表API", False, f"状态码: {response.status_code}")

            # 测试流程模板列表
            response = requests.get(f"{self.base_url}/flows", timeout=10)
            if response.status_code == 200:
                flows_data = response.json()
                assert isinstance(flows_data, list)
                self.log_test_result("流程模板API", True, f"获取到 {len(flows_data)} 个流程")
            else:
                self.log_test_result("流程模板API", False, f"状态码: {response.status_code}")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("API端点测试", False, str(e), duration)
            return False

    def test_session_creation(self) -> bool:
        """测试会话创建"""
        start_time = time.time()

        try:
            logger.info("🆕 测试会话创建...")

            # 获取流程模板
            with self.app.app_context():
                flow_template = FlowTemplate.query.filter_by(name='测试问答流程').first()
                if not flow_template:
                    self.log_test_result("会话创建", False, "找不到测试流程模板")
                    return False

            # 创建会话
            session_data = {
                'topic': 'AI基础概念学习',
                'flow_template_id': flow_template.id
            }

            response = requests.post(f"{self.base_url}/sessions", json=session_data, timeout=10)

            if response.status_code == 201:
                created_session = response.json()
                self.session_id = created_session['id']
                assert isinstance(self.session_id, int)
                self.log_test_result("会话创建", True, f"会话ID: {self.session_id}")
                return True
            else:
                self.log_test_result("会话创建", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("会话创建", False, str(e), duration)
            return False

    def test_step_progress_service(self) -> bool:
        """测试步骤进度服务"""
        start_time = time.time()

        try:
            logger.info("📊 测试步骤进度服务...")

            if not self.session_id:
                self.log_test_result("步骤进度服务", False, "没有有效的会话ID")
                return False

            # 测试获取步骤进度
            response = requests.get(f"{self.base_url}/sessions/{self.session_id}/step-progress", timeout=10)

            if response.status_code == 200:
                progress_data = response.json()
                assert 'logs' in progress_data
                assert 'summary' in progress_data
                self.log_test_result("步骤进度API", True, f"获取到 {len(progress_data['logs'])} 条日志")
            else:
                self.log_test_result("步骤进度API", False, f"状态码: {response.status_code}")
                return False

            # 测试流程可视化
            response = requests.get(f"{self.base_url}/sessions/{self.session_id}/flow-visualization", timeout=10)

            if response.status_code == 200:
                viz_data = response.json()
                assert 'steps' in viz_data
                self.log_test_result("流程可视化API", True, f"获取到 {len(viz_data['steps'])} 个步骤")
            else:
                self.log_test_result("流程可视化API", False, f"状态码: {response.status_code}")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("步骤进度服务", False, str(e), duration)
            return False

    def test_llm_interaction_service(self) -> bool:
        """测试LLM交互服务"""
        start_time = time.time()

        try:
            logger.info("🤖 测试LLM交互服务...")

            if not self.session_id:
                self.log_test_result("LLM交互服务", False, "没有有效的会话ID")
                return False

            # 测试获取LLM交互记录
            response = requests.get(f"{self.base_url}/sessions/{self.session_id}/llm-interactions", timeout=10)

            if response.status_code == 200:
                llm_data = response.json()
                assert 'interactions' in llm_data
                assert 'statistics' in llm_data
                self.log_test_result("LLM交互API", True, f"获取到 {len(llm_data['interactions'])} 条交互记录")
            else:
                self.log_test_result("LLM交互API", False, f"状态码: {response.status_code}")
                return False

            # 测试LLM统计
            response = requests.get(f"{self.base_url}/sessions/{self.session_id}/llm-statistics", timeout=10)

            if response.status_code == 200:
                stats_data = response.json()
                assert 'total_interactions' in stats_data
                self.log_test_result("LLM统计API", True, f"总交互数: {stats_data['total_interactions']}")
            else:
                self.log_test_result("LLM统计API", False, f"状态码: {response.status_code}")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("LLM交互服务", False, str(e), duration)
            return False

    def test_security_service(self) -> bool:
        """测试安全服务"""
        start_time = time.time()

        try:
            logger.info("🔒 测试安全服务...")

            security_manager = get_api_key_manager()

            # 测试敏感数据过滤
            test_text = "API密钥: sk-1234567890abcdef1234567890abcdef12345678"
            filtered_text = security_manager.mask_sensitive_data(test_text)

            assert "sk-1234" not in filtered_text
            assert "***" in filtered_text
            self.log_test_result("敏感数据过滤", True, "API密钥已正确屏蔽")

            # 测试权限系统
            permission = security_manager.create_permission(
                user_id="test_user",
                level=PermissionLevel.DEBUG,
                resources=["sessions", "llm_interactions"]
            )

            assert security_manager.check_permission("test_user", PermissionLevel.READ_ONLY)
            assert security_manager.check_permission("test_user", PermissionLevel.DEBUG)
            assert not security_manager.check_permission("test_user", PermissionLevel.ADMIN)

            self.log_test_result("权限系统", True, "权限检查正常工作")

            # 测试API密钥管理
            api_key = security_manager.get_safe_api_key("anthropic")
            # 这里只验证函数不抛出异常
            self.log_test_result("API密钥管理", True, "API密钥获取功能正常")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("安全服务", False, str(e), duration)
            return False

    def test_rate_limit_service(self) -> bool:
        """测试速率限制服务"""
        start_time = time.time()

        try:
            logger.info("⚡ 测试速率限制服务...")

            rate_limiter = get_rate_limit_service()

            # 测试API调用速率限制
            result1 = rate_limiter.check_rate_limit(RateLimitType.API_CALL, weight=1)
            assert result1.allowed
            assert result1.remaining >= 0

            # 测试调试访问速率限制
            result2 = rate_limiter.check_rate_limit(RateLimitType.DEBUG_ACCESS, weight=1)
            assert result2.allowed

            # 测试使用统计
            stats = rate_limiter.get_usage_stats(RateLimitType.API_CALL)
            assert 'current_usage' in stats
            assert 'remaining' in stats

            self.log_test_result("速率限制服务", True, "速率限制功能正常")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("速率限制服务", False, str(e), duration)
            return False

    def test_cache_service(self) -> bool:
        """测试缓存服务"""
        start_time = time.time()

        try:
            logger.info("💾 测试缓存服务...")

            cache_service = get_cache_service()

            # 测试基本缓存操作
            test_key = "test_integration_key"
            test_value = {"message": "Hello, World!", "timestamp": time.time()}

            # 设置缓存
            set_result = cache_service.set(test_key, test_value, ttl=60)
            assert set_result

            # 获取缓存
            retrieved_value = cache_service.get(test_key)
            assert retrieved_value == test_value

            # 测试键存在检查
            exists = cache_service.exists(test_key)
            assert exists

            # 删除缓存
            delete_result = cache_service.delete(test_key)
            assert delete_result

            # 验证删除
            exists_after_delete = cache_service.exists(test_key)
            assert not exists_after_delete

            self.log_test_result("缓存服务", True, "缓存操作正常")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("缓存服务", False, str(e), duration)
            return False

    def test_database_indexes(self) -> bool:
        """测试数据库索引"""
        start_time = time.time()

        try:
            logger.info("🗄️ 测试数据库索引...")

            with self.app.app_context():
                # 检查关键表是否有索引
                engine = db.engine

                # 检查LLM交互表索引
                result = engine.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_llm_interactions_%'
                """).fetchall()

                llm_indexes = [row[0] for row in result]
                expected_llm_indexes = [
                    'idx_llm_interactions_session_created',
                    'idx_llm_interactions_status',
                    'idx_llm_interactions_created_at'
                ]

                missing_indexes = [idx for idx in expected_llm_indexes if idx not in llm_indexes]
                if missing_indexes:
                    self.log_test_result("数据库索引", False, f"缺少LLM交互表索引: {missing_indexes}")
                    return False

                # 检查步骤执行日志表索引
                result = engine.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_step_logs_%'
                """).fetchall()

                step_indexes = [row[0] for row in result]
                expected_step_indexes = [
                    'idx_step_logs_session_execution_order',
                    'idx_step_logs_status',
                    'idx_step_logs_created_at'
                ]

                missing_indexes = [idx for idx in expected_step_indexes if idx not in step_indexes]
                if missing_indexes:
                    self.log_test_result("数据库索引", False, f"缺少步骤执行日志表索引: {missing_indexes}")
                    return False

                self.log_test_result("数据库索引", True, f"LLM表索引: {len(llm_indexes)}, 步骤表索引: {len(step_indexes)}")

            duration = time.time() - start_time
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("数据库索引", False, str(e), duration)
            return False

    def test_frontend_components(self) -> bool:
        """测试前端组件（模拟）"""
        start_time = time.time()

        try:
            logger.info("🎨 测试前端组件...")

            # 这里模拟前端组件测试
            # 在实际环境中，应该使用前端测试框架

            # 检查组件文件是否存在
            component_files = [
                "fronted/src/components/StepProgressDisplay.tsx",
                "fronted/src/components/LLMIODisplay.tsx",
                "fronted/src/components/DebugPanel.tsx",
                "fronted/src/components/EnhancedSessionTheater.tsx"
            ]

            existing_components = []
            for file_path in component_files:
                full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
                if os.path.exists(full_path):
                    existing_components.append(file_path)

            if len(existing_components) == len(component_files):
                self.log_test_result("前端组件", True, f"所有 {len(component_files)} 个组件文件存在")
            else:
                missing = len(component_files) - len(existing_components)
                self.log_test_result("前端组件", False, f"缺少 {missing} 个组件文件")

            duration = time.time() - start_time
            return len(existing_components) == len(component_files)

        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("前端组件", False, str(e), duration)
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("🚀 开始运行集成测试套件...")
        start_time = time.time()

        # 设置测试数据
        if not self.setup_test_data():
            return {
                'success': False,
                'error': '测试数据设置失败'
            }

        # 运行各项测试
        tests = [
            self.test_api_endpoints,
            self.test_session_creation,
            self.test_step_progress_service,
            self.test_llm_interaction_service,
            self.test_security_service,
            self.test_rate_limit_service,
            self.test_cache_service,
            self.test_database_indexes,
            self.test_frontend_components
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"测试执行异常: {str(e)}")

        # 生成测试报告
        total_duration = time.time() - start_time
        success_rate = (passed_tests / total_tests) * 100

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': success_rate,
            'total_duration': total_duration,
            'test_results': self.test_results,
            'summary': {
                'status': 'PASSED' if passed_tests == total_tests else 'FAILED',
                'message': f'通过 {passed_tests}/{total_tests} 项测试' if passed_tests == total_tests else f'失败 {total_tests - passed_tests}/{total_tests} 项测试'
            }
        }

        # 输出测试总结
        logger.info("=" * 80)
        logger.info("🧪 集成测试总结:")
        logger.info(f"📊 总测试数: {total_tests}")
        logger.info(f"✅ 通过测试: {passed_tests}")
        logger.info(f"❌ 失败测试: {total_tests - passed_tests}")
        logger.info(f"📈 成功率: {success_rate:.1f}%")
        logger.info(f"⏱️ 总耗时: {total_duration:.2f}秒")
        logger.info(f"🎯 测试状态: {report['summary']['status']}")
        logger.info("=" * 80)

        return report

    def save_test_report(self, report: Dict[str, Any], filename: str = None):
        """保存测试报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integration_test_report_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 测试报告已保存到: {filename}")
        except Exception as e:
            logger.error(f"❌ 保存测试报告失败: {str(e)}")


if __name__ == "__main__":
    # 运行集成测试
    test_suite = IntegrationTestSuite()
    report = test_suite.run_all_tests()

    # 保存测试报告
    test_suite.save_test_report(report)

    # 根据测试结果退出
    sys.exit(0 if report['summary']['status'] == 'PASSED' else 1)