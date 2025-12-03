#!/usr/bin/env python3
"""
应用数据库迁移脚本
"""

import os
import sys

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def apply_migration():
    """应用数据库迁移"""
    from app import create_app, db
    from app.models import FlowTemplate, FlowStep
    import sqlite3

    app = create_app()

    with app.app_context():
        print("开始应用数据库迁移...")

        # 直接执行SQL迁移，因为Flask-Migrate可能有问题
        db_path = 'conversations.db'

        try:
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            print("执行 FlowTemplate 表迁移...")

            # 更新FlowTemplate表结构
            # 注意：SQLite不支持直接修改列约束，所以我们创建新表并迁移数据

            # 1. 备份现有数据
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_templates_new AS
                SELECT * FROM flow_templates WHERE 0
            """)

            # 2. 创建新表结构
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_templates_migrated (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    topic VARCHAR(200),
                    type VARCHAR(50) NOT NULL,
                    description TEXT,
                    version VARCHAR(20),
                    is_active BOOLEAN,
                    _termination_config TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 迁移数据
            cursor.execute("""
                INSERT INTO flow_templates_migrated (
                    id, name, topic, type, description, version, is_active,
                    _termination_config, created_at, updated_at
                )
                SELECT
                    id, name, topic, type, description, version, is_active,
                    termination_config, created_at, updated_at
                FROM flow_templates
            """)

            # 4. 删除旧表
            cursor.execute("DROP TABLE IF EXISTS flow_templates")

            # 5. 重命名新表
            cursor.execute("ALTER TABLE flow_templates_migrated RENAME TO flow_templates")

            print("FlowTemplate 表迁移完成！")

            # 对FlowStep表进行类似操作
            print("执行 FlowStep 表迁移...")

            # 备份现有数据
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_steps_new AS
                SELECT * FROM flow_steps WHERE 0
            """)

            # 创建新表结构
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_steps_migrated (
                    id INTEGER PRIMARY KEY,
                    flow_template_id INTEGER NOT NULL,
                    "order" INTEGER NOT NULL,
                    speaker_role_ref VARCHAR(50) NOT NULL,
                    target_role_ref VARCHAR(50),
                    task_type VARCHAR(50) NOT NULL,
                    _context_scope TEXT NOT NULL,
                    _context_param TEXT,
                    _logic_config TEXT,
                    next_step_id INTEGER,
                    description VARCHAR(500),
                    FOREIGN KEY (flow_template_id) REFERENCES flow_templates (id)
                )
            """)

            # 迁移数据
            cursor.execute("""
                INSERT INTO flow_steps_migrated (
                    id, flow_template_id, "order", speaker_role_ref, target_role_ref,
                    task_type, _context_scope, _context_param, _logic_config,
                    next_step_id, description
                )
                SELECT
                    id, flow_template_id, "order", speaker_role_ref, target_role_ref,
                    task_type, context_scope, context_param, logic_config,
                    next_step_id, description
                FROM flow_steps
            """)

            # 删除旧表
            cursor.execute("DROP TABLE IF EXISTS flow_steps")

            # 重命名新表
            cursor.execute("ALTER TABLE flow_steps_migrated RENAME TO flow_steps")

            print("FlowStep 表迁移完成！")

            # 5. 数据后处理：为null字段设置合理默认值
            print("进行数据后处理...")

            # 为null的version字段设置默认值
            cursor.execute("""
                UPDATE flow_templates
                SET version = CASE
                    WHEN version IS NULL THEN '1.0.0'
                    ELSE version
                END
            """)

            # 为null的is_active字段设置默认值
            cursor.execute("""
                UPDATE flow_templates
                SET is_active = CASE
                    WHEN is_active IS NULL THEN 1
                    ELSE is_active
                END
            """)

            # 为空的context_scope设置默认值
            cursor.execute("""
                UPDATE flow_steps
                SET _context_scope = CASE
                    WHEN _context_scope IS NULL OR _context_scope = '' THEN 'all'
                    ELSE _context_scope
                END
            """)

            # 提交更改
            conn.commit()
            print("数据库迁移完成！")

        except Exception as e:
            print(f"迁移失败: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    apply_migration()