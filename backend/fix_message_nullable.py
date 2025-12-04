#!/usr/bin/env python3
"""
修复messages表中speaker_session_role_id的NOT NULL约束问题
"""

import sqlite3
import sys
import os

def check_database_schema(db_path):
    """检查数据库schema"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查messages表结构
        cursor.execute("PRAGMA table_info(messages)")
        columns = cursor.fetchall()

        print("=== Messages表结构 ===")
        for col in columns:
            cid, name, data_type, not_null, default_val, is_pk = col
            nullable = "NULL" if not_null == 0 else "NOT NULL"
            print(f"  {name}: {data_type} {nullable} (Default: {default_val})")

            if name == 'speaker_session_role_id':
                speaker_session_role_nullable = (not_null == 0)

        # 检查是否有数据
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        print(f"\n消息总数: {message_count}")

        conn.close()
        return speaker_session_role_nullable, message_count

    except Exception as e:
        print(f"检查数据库失败: {e}")
        return False, 0

def fix_database_schema(db_path):
    """修复数据库schema"""
    try:
        print(f"\n=== 开始修复数据库: {db_path} ===")

        # 备份数据库
        backup_path = db_path + ".backup"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查SQLite版本
        cursor.execute("SELECT sqlite_version()")
        sqlite_version = cursor.fetchone()[0]
        print(f"📊 SQLite版本: {sqlite_version}")

        # 修改列约束 (SQLite不支持直接修改列约束，需要重建表)
        print("🔄 开始重建messages表...")

        # 1. 创建临时表
        cursor.execute("""
            CREATE TABLE messages_new (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                speaker_session_role_id INTEGER,  -- 移除NOT NULL约束
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
            )
        """)
        print("✅ 创建新表结构")

        # 2. 复制数据
        cursor.execute("""
            INSERT INTO messages_new (
                id, session_id, speaker_session_role_id, target_session_role_id,
                reply_to_message_id, content, content_summary, round_index,
                section, created_at
            )
            SELECT
                id, session_id, speaker_session_role_id, target_session_role_id,
                reply_to_message_id, content, content_summary, round_index,
                section, created_at
            FROM messages
        """)

        affected_rows = cursor.rowcount
        print(f"✅ 复制了 {affected_rows} 条消息记录")

        # 3. 删除旧表
        cursor.execute("DROP TABLE messages")
        print("✅ 删除旧表")

        # 4. 重命名新表
        cursor.execute("ALTER TABLE messages_new RENAME TO messages")
        print("✅ 重命名新表")

        # 5. 重建索引
        cursor.execute("CREATE INDEX idx_messages_session_id ON messages (session_id)")
        cursor.execute("CREATE INDEX idx_messages_created_at ON messages (created_at)")
        print("✅ 重建索引")

        # 提交事务
        conn.commit()
        print("✅ 数据库修复完成")

        # 验证修复结果
        cursor.execute("PRAGMA table_info(messages)")
        columns = cursor.fetchall()

        print("\n=== 修复后的表结构 ===")
        for col in columns:
            cid, name, data_type, not_null, default_val, is_pk = col
            nullable = "NULL" if not_null == 0 else "NOT NULL"
            print(f"  {name}: {data_type} {nullable}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    db_path = "conversations.db"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print("🔍 检查当前数据库状态...")
    is_nullable, message_count = check_database_schema(db_path)

    if is_nullable:
        print("✅ speaker_session_role_id已经支持NULL，无需修复")
        return True
    else:
        print("❌ speaker_session_role_id仍然是NOT NULL，需要修复")

        if message_count > 0:
            print(f"⚠️  数据库中有 {message_count} 条消息，修复过程会保留所有数据")

        response = input("\n是否继续修复数据库? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            success = fix_database_schema(db_path)
            if success:
                print("\n🎉 数据库修复成功！")
                print("现在可以正常使用无角色映射的会话功能了。")
                return True
            else:
                print("\n❌ 数据库修复失败！")
                return False
        else:
            print("修复已取消")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)