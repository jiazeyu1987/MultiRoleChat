import sqlite3
import json

def migrate_database():
    """执行数据库迁移"""
    db_path = 'conversations.db'

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("开始数据库迁移...")

        # 备份现有数据
        print("1. 备份现有数据...")
        cursor.execute("CREATE TABLE IF NOT EXISTS flow_templates_backup AS SELECT * FROM flow_templates")
        cursor.execute("CREATE TABLE IF NOT EXISTS flow_steps_backup AS SELECT * FROM flow_steps")

        # 创建新的表结构
        print("2. 创建新的表结构...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flow_templates_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                topic VARCHAR(200),
                type VARCHAR(50) NOT NULL,
                description TEXT,
                version VARCHAR(20),
                is_active BOOLEAN,
                termination_config TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flow_steps_new (
                id INTEGER PRIMARY KEY,
                flow_template_id INTEGER NOT NULL,
                "order" INTEGER NOT NULL,
                speaker_role_ref VARCHAR(50) NOT NULL,
                target_role_ref VARCHAR(50),
                task_type VARCHAR(50) NOT NULL,
                context_scope TEXT NOT NULL,
                context_param TEXT,
                logic_config TEXT,
                next_step_id INTEGER,
                description VARCHAR(500),
                FOREIGN KEY (flow_template_id) REFERENCES flow_templates (id)
            )
        """)

        # 迁移数据
        print("3. 迁移数据...")
        cursor.execute("""
            INSERT INTO flow_templates_new (
                id, name, topic, type, description, version, is_active,
                termination_config, created_at, updated_at
            )
            SELECT
                id, name, topic, type, description, version, is_active,
                termination_config, created_at, updated_at
            FROM flow_templates
        """)

        cursor.execute("""
            INSERT INTO flow_steps_new (
                id, flow_template_id, "order", speaker_role_ref, target_role_ref,
                task_type, context_scope, context_param, logic_config,
                next_step_id, description
            )
            SELECT
                id, flow_template_id, "order", speaker_role_ref, target_role_ref,
                task_type, context_scope, context_param, logic_config,
                next_step_id, description
            FROM flow_steps
        """)

        # 删除旧表
        print("4. 替换旧表...")
        cursor.execute("DROP TABLE IF EXISTS flow_templates")
        cursor.execute("DROP TABLE IF EXISTS flow_steps")

        # 重命名新表
        cursor.execute("ALTER TABLE flow_templates_new RENAME TO flow_templates")
        cursor.execute("ALTER TABLE flow_steps_new RENAME TO flow_steps")

        # 数据后处理
        print("5. 数据后处理...")
        cursor.execute("""
            UPDATE flow_templates
            SET version = CASE
                WHEN version IS NULL THEN '1.0.0'
                ELSE version
            END
        """)

        cursor.execute("""
            UPDATE flow_templates
            SET is_active = CASE
                WHEN is_active IS NULL THEN 1
                ELSE is_active
            END
        """)

        cursor.execute("""
            UPDATE flow_steps
            SET context_scope = CASE
                WHEN context_scope IS NULL OR context_scope = '' THEN 'all'
                ELSE context_scope
            END
        """)

        # 创建索引
        print("6. 创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_steps_template_id ON flow_steps(flow_template_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_steps_order ON flow_steps([order])")

        # 提交更改
        conn.commit()
        print("数据库迁移成功完成！")

        # 验证迁移结果
        cursor.execute("SELECT COUNT(*) FROM flow_templates")
        template_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM flow_steps")
        step_count = cursor.fetchone()[0]

        print(f"验证结果: {template_count} 个模板, {step_count} 个步骤")

    except Exception as e:
        print(f"迁移失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise

    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_database()