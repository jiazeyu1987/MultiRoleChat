#!/usr/bin/env python3
import sqlite3
import os

# 数据库文件路径
db_path = 'conversations.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取清理前的数量
        cursor.execute("SELECT COUNT(*) FROM flow_templates")
        template_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM flow_steps")
        step_count = cursor.fetchone()[0]

        print(f"清理前 - 模板: {template_count}, 步骤: {step_count}")

        # 删除所有步骤（先删除子表）
        cursor.execute("DELETE FROM flow_steps")
        deleted_steps = cursor.rowcount

        # 删除所有模板
        cursor.execute("DELETE FROM flow_templates")
        deleted_templates = cursor.rowcount

        # 提交更改
        conn.commit()

        print(f"清理完成 - 删除模板: {deleted_templates}, 删除步骤: {deleted_steps}")

    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()
else:
    print("数据库文件不存在")