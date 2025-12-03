import sqlite3

conn = sqlite3.connect('conversations.db')
cursor = conn.cursor()

# 查看当前状态
try:
    cursor.execute("SELECT COUNT(*) FROM flow_templates")
    templates = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flow_steps") 
    steps = cursor.fetchone()[0]
    print(f"Before: {templates} templates, {steps} steps")
    
    # 删除数据
    cursor.execute("DELETE FROM flow_steps")
    cursor.execute("DELETE FROM flow_templates")
    
    conn.commit()
    print("Deleted all templates and steps")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
