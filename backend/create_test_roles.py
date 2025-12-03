#!/usr/bin/env python3
"""
创建测试角色的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Role

def create_test_roles():
    """创建测试角色"""
    app = create_app()

    with app.app_context():
        # 检查是否已有角色
        existing_roles = Role.query.all()
        if existing_roles:
            print(f"数据库中已有 {len(existing_roles)} 个角色:")
            for role in existing_roles:
                print(f"  - {role.name} (ID: {role.id})")
            return

        # 创建测试角色
        test_roles = [
            {
                'name': '老师',
                'prompt': '你是一位专业的老师，善于教学指导，用鼓励式、引导式的方式进行教学，对学生耐心细致。'
            },
            {
                'name': '学生',
                'prompt': '你是一个积极学习的学生，充满好奇心，热爱求知，有时候会犯错误，但总是乐于学习和接受指导。'
            },
            {
                'name': '专家',
                'prompt': '你是一位领域专家，具有丰富的专业知识和实践经验，说话严谨、专业、有说服力。'
            }
        ]

        for role_data in test_roles:
            role = Role(name=role_data['name'], prompt=role_data['prompt'])
            db.session.add(role)
            print(f"创建角色: {role_data['name']}")

        try:
            db.session.commit()
            print(f"\n成功创建 {len(test_roles)} 个测试角色！")
        except Exception as e:
            db.session.rollback()
            print(f"创建角色失败: {e}")
            raise

if __name__ == '__main__':
    create_test_roles()