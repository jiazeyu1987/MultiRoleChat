#!/usr/bin/env python3
"""
通过Flask应用清理数据库
"""
import os
import sys

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FlowTemplate, FlowStep

def clean_database():
    app = create_app()

    with app.app_context():
        # 查看当前数据
        templates = FlowTemplate.query.all()
        steps = FlowStep.query.all()

        print(f"当前数据库中有 {len(templates)} 个模板和 {len(steps)} 个步骤")

        if templates:
            print("模板列表:")
            for t in templates:
                print(f"  - ID: {t.id}, 名称: {t.name}, 类型: {t.type}")

        # 删除所有步骤（先删除子表）
        FlowStep.query.delete()

        # 删除所有模板
        FlowTemplate.query.delete()

        # 提交
        db.session.commit()

        print("✅ 数据库清理完成！")

        # 验证清理结果
        remaining_templates = FlowTemplate.query.count()
        remaining_steps = FlowStep.query.count()
        print(f"清理后剩余: {remaining_templates} 个模板, {remaining_steps} 个步骤")

if __name__ == "__main__":
    clean_database()