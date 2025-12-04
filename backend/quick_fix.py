#!/usr/bin/env python3
import sqlite3
import os

def quick_fix():
    db_path = "conversations.db"
    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查当前表结构
    cursor.execute("PRAGMA table_info(messages);")
    columns = cursor.fetchall()

    print("当前messages表结构:")
    for col in columns:
        print(f"  {col[1]}: {col[2]} {'NULL' if col[3] == 0 else 'NOT NULL'}")

    # 直接修改表结构 - SQLite方法
    try:
        # 创建新表
        cursor.execute("""
        CREATE TABLE messages_temp (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            speaker_session_role_id INTEGER,
            target_session_role_id INTEGER,
            reply_to_message_id INTEGER,
            content TEXT NOT NULL,
            content_summary TEXT,
            round_index INTEGER DEFAULT 1,
            section TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (speaker_session_role_id) REFERENCES session_roles (id),
            FOREIGN KEY (target_session_role_id) REFERENCES session_roles (id),
            FOREIGN KEY (reply_to_message_id) REFERENCES messages (id)
        );
        """)

        # 复制数据
        cursor.execute("""
        INSERT INTO messages_temp
        SELECT * FROM messages;
        """)

        # 删除旧表并重命名
        cursor.execute("DROP TABLE messages;")
        cursor.execute("ALTER TABLE messages_temp RENAME TO messages;")

        # 重建索引
        cursor.execute("CREATE INDEX idx_messages_session_id ON messages (session_id);")

        conn.commit()
        print("✅ 数据库修复成功！")

        # 验证结果
        cursor.execute("PRAGMA table_info(messages);")
        new_columns = cursor.fetchall()
        print("修复后messages表结构:")
        for col in new_columns:
            if col[1] == 'speaker_session_role_id':
                print(f"  {col[1]}: {col[2]} {'NULL' if col[3] == 0 else 'NOT NULL'} ✅")

    except Exception as e:
        print(f"修复失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    quick_fix()