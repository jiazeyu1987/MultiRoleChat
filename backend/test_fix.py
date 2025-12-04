#!/usr/bin/env python3
"""
测试数据库修复是否正确
"""

import sqlite3
import os

def test_fix():
    db_path = "conversations.db"
    if not os.path.exists(db_path):
        print("数据库文件不存在，无法测试")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表结构
        cursor.execute("PRAGMA table_info(messages);")
        columns = cursor.fetchall()

        speaker_nullable = None
        for col in columns:
            if col[1] == 'speaker_session_role_id':
                speaker_nullable = (col[3] == 0)  # 0 = NULL, 1 = NOT NULL
                break

        print(f"speaker_session_role_id 是否支持NULL: {speaker_nullable}")

        if not speaker_nullable:
            print("❌ 数据库仍然不支持NULL，需要修复")

            # 尝试修复
            print("🔧 尝试修复数据库...")

            # 备份
            conn.execute("CREATE TABLE messages_backup AS SELECT * FROM messages;")

            # 重建表
            conn.execute("DROP TABLE messages;")
            conn.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    speaker_session_role_id INTEGER,
                    target_session_role_id INTEGER,
                    reply_to_message_id INTEGER,
                    content TEXT NOT NULL,
                    content_summary TEXT,
                    round_index INTEGER DEFAULT 1,
                    section TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 恢复数据
            conn.execute("INSERT INTO messages SELECT * FROM messages_backup;")
            conn.execute("DROP TABLE messages_backup;")

            # 检查修复结果
            cursor.execute("PRAGMA table_info(messages);")
            new_columns = cursor.fetchall()
            for col in new_columns:
                if col[1] == 'speaker_session_role_id':
                    new_speaker_nullable = (col[3] == 0)
                    print(f"✅ 修复后支持NULL: {new_speaker_nullable}")
                    break
        else:
            print("✅ 数据库已支持NULL，无需修复")

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_fix()