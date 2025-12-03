#!/usr/bin/env python3
"""
清理数据库中所有流程模板的脚本
"""

import sys
import os

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FlowTemplate, FlowStep

def clear_all_templates():
    """删除所有流程模板和相关步骤"""
    app = create_app()

    with app.app_context():
        try:
            # 获取当前模板数量
            template_count = FlowTemplate.query.count()
            step_count = FlowStep.query.count()

            print(f"当前数据库状态:")
            print(f"  流程模板数量: {template_count}")
            print(f"  流程步骤数量: {step_count}")

            if template_count == 0:
                print("数据库中没有流程模板，无需清理。")
                return

            print("\n开始清理数据库中的流程模板...")

            # 先删除所有流程步骤（由于外键约束，必须先删除子表）
            deleted_steps = FlowStep.query.delete()
            print(f"已删除 {deleted_steps} 个流程步骤")

            # 再删除所有流程模板
            deleted_templates = FlowTemplate.query.delete()
            print(f"已删除 {deleted_templates} 个流程模板")

            # 提交更改
            db.session.commit()

            print("\n✅ 数据库清理完成！")
            print(f"删除的流程模板: {deleted_templates}")
            print(f"删除的流程步骤: {deleted_steps}")

        except Exception as e:
            print(f"❌ 清理过程中发生错误: {e}")
            db.session.rollback()
            raise

def confirm_action():
    """确认用户真的想要执行清理操作"""
    print("⚠️  警告：此操作将永久删除数据库中的所有流程模板！")
    print("⚠️  这个操作不可逆！")
    print("⚠️  请确保您已经备份了重要数据！")

    confirm = input("\n确定要继续吗？输入 'DELETE ALL TEMPLATES' 来确认: ")
    return confirm == "DELETE ALL TEMPLATES"

if __name__ == "__main__":
    print("=" * 50)
    print("流程模板数据库清理工具")
    print("=" * 50)

    if confirm_action():
        clear_all_templates()
    else:
        print("操作已取消。")