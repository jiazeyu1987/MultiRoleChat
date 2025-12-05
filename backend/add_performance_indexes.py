#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
添加数据库性能索引

为关键表添加性能优化索引，提升查询性能
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.session import Session
from app.models.message import Message
from app.models.llm_interaction import LLMInteraction
from app.models.step_execution_log import StepExecutionLog

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_performance_indexes():
    """创建性能优化索引"""

    app = create_app()

    with app.app_context():
        try:
            logger.info("开始创建数据库性能索引...")

            # 获取数据库连接
            engine = db.engine

            # 定义要创建的索引
            indexes = [
                # Sessions表索引
                {
                    'name': 'idx_sessions_user_id',
                    'table': 'sessions',
                    'columns': ['user_id'],
                    'description': '用户会话查询优化'
                },
                {
                    'name': 'idx_sessions_status_created',
                    'table': 'sessions',
                    'columns': ['status', 'created_at'],
                    'description': '按状态和创建时间查询优化'
                },
                {
                    'name': 'idx_sessions_flow_template',
                    'table': 'sessions',
                    'columns': ['flow_template_id'],
                    'description': '流程模板关联查询优化'
                },
                {
                    'name': 'idx_sessions_updated_at',
                    'table': 'sessions',
                    'columns': ['updated_at'],
                    'description': '最近更新会话查询优化'
                },

                # Messages表索引
                {
                    'name': 'idx_messages_session_created',
                    'table': 'messages',
                    'columns': ['session_id', 'created_at'],
                    'description': '会话消息按时间查询优化'
                },
                {
                    'name': 'idx_messages_speaker_session_role',
                    'table': 'messages',
                    'columns': ['speaker_session_role_id'],
                    'description': '发言者角色查询优化'
                },
                {
                    'name': 'idx_messages_round_index',
                    'table': 'messages',
                    'columns': ['round_index'],
                    'description': '轮次查询优化'
                },
                {
                    'name': 'idx_messages_reply_to',
                    'table': 'messages',
                    'columns': ['reply_to_message_id'],
                    'description': '回复关系查询优化'
                },

                # LLM Interactions表索引
                {
                    'name': 'idx_llm_interactions_session_created',
                    'table': 'llm_interactions',
                    'columns': ['session_id', 'created_at'],
                    'description': '会话LLM交互按时间查询优化'
                },
                {
                    'name': 'idx_llm_interactions_step_id',
                    'table': 'llm_interactions',
                    'columns': ['step_id'],
                    'description': '步骤关联查询优化'
                },
                {
                    'name': 'idx_llm_interactions_status',
                    'table': 'llm_interactions',
                    'columns': ['status'],
                    'description': '状态筛选优化'
                },
                {
                    'name': 'idx_llm_interactions_provider_model',
                    'table': 'llm_interactions',
                    'columns': ['provider', 'model'],
                    'description': '提供商和模型查询优化'
                },
                {
                    'name': 'idx_llm_interactions_session_role',
                    'table': 'llm_interactions',
                    'columns': ['session_role_id'],
                    'description': '角色关联查询优化'
                },
                {
                    'name': 'idx_llm_interactions_request_id',
                    'table': 'llm_interactions',
                    'columns': ['request_id'],
                    'description': '请求ID查询优化'
                },
                {
                    'name': 'idx_llm_interactions_created_at',
                    'table': 'llm_interactions',
                    'columns': ['created_at'],
                    'description': '时间范围查询优化'
                },
                {
                    'name': 'idx_llm_interactions_latency',
                    'table': 'llm_interactions',
                    'columns': ['latency_ms'],
                    'description': '性能分析查询优化'
                },

                # Step Execution Logs表索引
                {
                    'name': 'idx_step_logs_session_execution_order',
                    'table': 'step_execution_logs',
                    'columns': ['session_id', 'execution_order'],
                    'description': '会话步骤执行顺序查询优化'
                },
                {
                    'name': 'idx_step_logs_step_id',
                    'table': 'step_execution_logs',
                    'columns': ['step_id'],
                    'description': '步骤关联查询优化'
                },
                {
                    'name': 'idx_step_logs_status',
                    'table': 'step_execution_logs',
                    'columns': ['status'],
                    'description': '状态筛选优化'
                },
                {
                    'name': 'idx_step_logs_parent_log',
                    'table': 'step_execution_logs',
                    'columns': ['parent_log_id'],
                    'description': '父子关系查询优化'
                },
                {
                    'name': 'idx_step_logs_round_loop',
                    'table': 'step_execution_logs',
                    'columns': ['round_index', 'loop_iteration'],
                    'description': '轮次和循环查询优化'
                },
                {
                    'name': 'idx_step_logs_created_at',
                    'table': 'step_execution_logs',
                    'columns': ['created_at'],
                    'description': '时间范围查询优化'
                },
                {
                    'name': 'idx_step_logs_duration',
                    'table': 'step_execution_logs',
                    'columns': ['duration_ms'],
                    'description': '性能分析查询优化'
                },
                {
                    'name': 'idx_step_logs_result_type',
                    'table': 'step_execution_logs',
                    'columns': ['result_type'],
                    'description': '结果类型查询优化'
                }
            ]

            # 创建索引
            created_count = 0
            skipped_count = 0

            for index_info in indexes:
                index_name = index_info['name']
                table_name = index_info['table']
                columns = index_info['columns']
                description = index_info['description']

                try:
                    # 检查索引是否已存在
                    check_sql = """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name=?
                    """
                    result = engine.execute(check_sql, (index_name,)).fetchone()

                    if result:
                        logger.info(f"索引 '{index_name}' 已存在，跳过")
                        skipped_count += 1
                        continue

                    # 创建索引
                    columns_str = ', '.join(columns)
                    create_sql = f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"

                    logger.info(f"创建索引: {index_name} - {description}")
                    engine.execute(create_sql)

                    created_count += 1
                    logger.info(f"✅ 成功创建索引: {index_name}")

                except Exception as e:
                    logger.error(f"❌ 创建索引 '{index_name}' 失败: {str(e)}")
                    continue

            # 创建复合索引（对于高频查询组合）
            composite_indexes = [
                {
                    'name': 'idx_sessions_status_updated_composite',
                    'table': 'sessions',
                    'columns': ['status', 'updated_at', 'id'],
                    'description': '活跃会话复合查询优化'
                },
                {
                    'name': 'idx_llm_interactions_session_status_created',
                    'table': 'llm_interactions',
                    'columns': ['session_id', 'status', 'created_at'],
                    'description': '会话LLM交互状态时间复合查询优化'
                },
                {
                    'name': 'idx_step_logs_session_status_execution',
                    'table': 'step_execution_logs',
                    'columns': ['session_id', 'status', 'execution_order'],
                    'description': '会话步骤状态执行顺序复合查询优化'
                },
                {
                    'name': 'idx_messages_session_round_created',
                    'table': 'messages',
                    'columns': ['session_id', 'round_index', 'created_at'],
                    'description': '会话消息轮次时间复合查询优化'
                }
            ]

            for index_info in composite_indexes:
                index_name = index_info['name']
                table_name = index_info['table']
                columns = index_info['columns']
                description = index_info['description']

                try:
                    # 检查索引是否已存在
                    check_sql = """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name=?
                    """
                    result = engine.execute(check_sql, (index_name,)).fetchone()

                    if result:
                        logger.info(f"复合索引 '{index_name}' 已存在，跳过")
                        skipped_count += 1
                        continue

                    # 创建复合索引
                    columns_str = ', '.join(columns)
                    create_sql = f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"

                    logger.info(f"创建复合索引: {index_name} - {description}")
                    engine.execute(create_sql)

                    created_count += 1
                    logger.info(f"✅ 成功创建复合索引: {index_name}")

                except Exception as e:
                    logger.error(f"❌ 创建复合索引 '{index_name}' 失败: {str(e)}")
                    continue

            # 分析数据库统计信息（优化查询计划）
            try:
                logger.info("分析数据库统计信息...")
                engine.execute("ANALYZE")
                logger.info("✅ 数据库统计信息分析完成")
            except Exception as e:
                logger.warning(f"⚠️ 数据库统计信息分析失败: {str(e)}")

            # 输出总结
            logger.info("=" * 60)
            logger.info("数据库索引创建总结:")
            logger.info(f"✅ 成功创建索引: {created_count} 个")
            logger.info(f"⏭️ 跳过已存在索引: {skipped_count} 个")
            logger.info(f"📊 总计处理索引: {created_count + skipped_count} 个")
            logger.info("=" * 60)

            # 提供使用建议
            logger.info("🚀 性能优化建议:")
            logger.info("1. 定期运行 VACUUM 命令清理数据库碎片")
            logger.info("2. 对于大量数据删除/更新后，运行 ANALYZE 更新统计信息")
            logger.info("3. 监控查询性能，根据实际使用情况调整索引")
            logger.info("4. 考虑为报表查询创建专门的汇总表")

            return True

        except Exception as e:
            logger.error(f"创建数据库索引过程中发生错误: {str(e)}")
            return False


def verify_indexes():
    """验证索引是否正确创建"""

    app = create_app()

    with app.app_context():
        try:
            logger.info("开始验证数据库索引...")

            engine = db.engine

            # 获取所有索引
            result = engine.execute("""
                SELECT name, tbl_name, sql
                FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY tbl_name, name
            """).fetchall()

            if not result:
                logger.warning("未找到任何自定义索引")
                return False

            logger.info("当前数据库中的自定义索引:")
            logger.info("-" * 80)

            for row in result:
                name, table, sql = row
                logger.info(f"📋 表: {table:<20} 索引: {name:<30}")
                if sql:
                    logger.info(f"    SQL: {sql}")
                logger.info("")

            logger.info("-" * 80)
            logger.info(f"总计找到 {len(result)} 个自定义索引")

            return True

        except Exception as e:
            logger.error(f"验证索引时发生错误: {str(e)}")
            return False


def show_query_performance_tips():
    """显示查询性能优化建议"""

    logger.info("🔧 数据库查询性能优化建议:")
    logger.info("")

    logger.info("1. 高频查询优化:")
    logger.info("   - 使用 EXPLAIN QUERY PLAN 分析查询执行计划")
    logger.info("   - 避免 SELECT *，只查询需要的字段")
    logger.info("   - 使用 LIMIT 限制结果集大小")
    logger.info("")

    logger.info("2. 索引使用策略:")
    logger.info("   - 为 WHERE、JOIN、ORDER BY 子句中的字段创建索引")
    logger.info("   - 复合索引的字段顺序很重要，高选择性字段放前面")
    logger.info("   - 避免过度索引，影响写入性能")
    logger.info("")

    logger.info("3. 分页查询优化:")
    logger.info("   - 使用 OFFSET/LIMIT 进行分页")
    logger.info("   - 对于大数据集，考虑使用游标分页")
    logger.info("")

    logger.info("4. 连接池优化:")
    logger.info("   - 合理设置连接池大小")
    logger.info("   - 使用连接池减少连接开销")
    logger.info("")

    logger.info("5. 缓存策略:")
    logger.info("   - 使用 Redis 缓存热点数据")
    logger.info("   - 实现查询结果缓存")
    logger.info("   - 设置合理的缓存过期时间")


if __name__ == "__main__":
    logger.info("🚀 开始数据库性能优化...")
    logger.info(f"执行时间: {datetime.now().isoformat()}")

    # 创建索引
    success = create_performance_indexes()

    if success:
        # 验证索引
        verify_indexes()

        # 显示优化建议
        show_query_performance_tips()

        logger.info("✅ 数据库性能优化完成！")
        sys.exit(0)
    else:
        logger.error("❌ 数据库性能优化失败！")
        sys.exit(1)