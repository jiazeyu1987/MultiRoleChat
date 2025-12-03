"""
重置流程模板数据的脚本
"""

def reset_templates():
    import sqlite3
    import os

    db_file = 'conversations.db'
    backup_file = 'conversations.db.backup'

    print("开始重置流程模板数据...")

    # 连接数据库
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # 查看当前数据
        cursor.execute("SELECT COUNT(*) FROM flow_templates")
        template_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM flow_steps")
        step_count = cursor.fetchone()[0]
        print(f"当前数据库中: {template_count} 个模板, {step_count} 个步骤")

        # 删除所有步骤（先删除子表，避免外键约束错误）
        cursor.execute("DELETE FROM flow_steps")
        steps_deleted = cursor.rowcount
        print(f"删除了 {steps_deleted} 个步骤")

        # 删除所有模板
        cursor.execute("DELETE FROM flow_templates")
        templates_deleted = cursor.rowcount
        print(f"删除了 {templates_deleted} 个模板")

        # 提交更改
        conn.commit()

        # 验证清理结果
        cursor.execute("SELECT COUNT(*) FROM flow_templates")
        remaining_templates = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM flow_steps")
        remaining_steps = cursor.fetchone()[0]

        print(f"✅ 清理完成！剩余: {remaining_templates} 个模板, {remaining_steps} 个步骤")

    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_templates()