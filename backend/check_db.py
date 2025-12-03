import sqlite3

# 连接数据库
conn = sqlite3.connect('conversations.db')
cursor = conn.cursor()

try:
    # 查看模板数量
    cursor.execute("SELECT COUNT(*) FROM flow_templates")
    template_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM flow_steps")
    step_count = cursor.fetchone()[0]

    print(f"数据库中有 {template_count} 个模板和 {step_count} 个步骤")

    if template_count > 0:
        print("模板列表:")
        cursor.execute("SELECT id, name, type FROM flow_templates")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, 名称: {row[1]}, 类型: {row[2]}")

    if step_count > 0:
        print(f"第一个步骤示例:")
        cursor.execute("SELECT * FROM flow_steps LIMIT 1")
        step = cursor.fetchone()
        if step:
            print(f"  步骤ID: {step[0]}, 模板ID: {step[1]}, 顺序: {step[2]}, 角色引用: {step[3]}")

finally:
    conn.close()