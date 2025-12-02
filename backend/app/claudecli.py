import anthropic
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class ConversationManager:
    """带持久化存储的对话管理器"""
    
    def __init__(self, api_key=None, db_path="conversations.db"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.db_path = db_path
        self.current_session_id = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                model TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        # 创建消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_session(self, name=None, model="claude-sonnet-4-20250514"):
        """创建新的对话会话"""
        if name is None:
            name = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO sessions (name, model, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (name, model, now, now))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.current_session_id = session_id
        print(f"创建新会话: {name} (ID: {session_id})")
        return session_id
    
    def load_session(self, session_id):
        """加载现有会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        session = cursor.fetchone()
        conn.close()
        
        if session:
            self.current_session_id = session_id
            print(f"加载会话: {session[1]} (ID: {session_id})")
            return True
        else:
            print(f"会话 {session_id} 不存在")
            return False
    
    def list_sessions(self):
        """列出所有会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.created_at, COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        ''')
        
        sessions = cursor.fetchall()
        conn.close()
        
        return sessions
    
    def get_history(self, session_id=None) -> List[Dict]:
        """获取会话历史"""
        if session_id is None:
            session_id = self.current_session_id
        
        if session_id is None:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
        ''', (session_id,))
        
        messages = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return messages
    
    def send_message(self, content: str, max_tokens=4096):
        """发送消息并保存"""
        if self.current_session_id is None:
            self.create_session()
        
        # 保存用户消息
        self._save_message(self.current_session_id, "user", content)
        
        # 获取完整历史
        history = self.get_history()
        
        try:
            # 获取会话的模型
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT model FROM sessions WHERE id = ?', 
                         (self.current_session_id,))
            model = cursor.fetchone()[0]
            conn.close()
            
            # 调用 API
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=history
            )
            
            assistant_message = response.content[0].text
            
            # 保存助手响应
            self._save_message(self.current_session_id, "assistant", assistant_message)
            
            # 更新会话时间
            self._update_session_timestamp(self.current_session_id)
            
            return assistant_message
            
        except Exception as e:
            print(f"发送消息失败: {e}")
            # 删除刚保存的用户消息
            self._delete_last_message(self.current_session_id)
            return None
    
    def _save_message(self, session_id, role, content):
        """保存单条消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, role, content, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _delete_last_message(self, session_id):
        """删除最后一条消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM messages 
            WHERE id = (
                SELECT id FROM messages 
                WHERE session_id = ? 
                ORDER BY id DESC LIMIT 1
            )
        ''', (session_id,))
        
        conn.commit()
        conn.close()
    
    def _update_session_timestamp(self, session_id):
        """更新会话时间戳"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions SET updated_at = ? WHERE id = ?
        ''', (datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def export_session(self, session_id=None, filename=None):
        """导出会话到 JSON"""
        if session_id is None:
            session_id = self.current_session_id
        
        history = self.get_history(session_id)
        
        if filename is None:
            filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        print(f"会话已导出到: {filename}")
        return filename


# 使用示例
if __name__ == "__main__":
    # 创建管理器
    manager = ConversationManager()
    
    # 创建新会话
    manager.create_session("Python Web 开发项目")
    
    # 多轮对话
    print("\n第1轮:")
    print(manager.send_message("帮我创建一个 Flask 应用"))
    
    print("\n第2轮:")
    print(manager.send_message("添加用户认证功能"))
    
    print("\n第3轮:")
    print(manager.send_message("使用 JWT 做 token 认证"))
    
    # 列出所有会话
    print("\n\n=== 所有会话 ===")
    sessions = manager.list_sessions()
    for sess in sessions:
        print(f"ID: {sess[0]}, 名称: {sess[1]}, 消息数: {sess[3]}")
    
    # 导出会话
    manager.export_session()
    
    # 稍后可以加载会话继续对话
    # manager.load_session(1)
    # manager.send_message("继续之前的开发...")