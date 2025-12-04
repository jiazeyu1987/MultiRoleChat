#!/usr/bin/env python3
"""
设置BP讨论流程所需的角色和流程模板
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app, db
from backend.app.models import Role, FlowTemplate, FlowStep
from datetime import datetime

def setup_bp_discussion():
    """设置BP讨论流程"""
    app = create_app()

    with app.app_context():
        # 1. 创建所需角色
        roles_data = [
            {
                'name': '打工人',
                'type': 'employee',
                'description': '提出商业计划的打工人，有创新想法但需要各方建议',
                'prompt': '你是一个有创新想法的打工人，正在准备商业计划书。你需要根据其他经理的建议不断完善你的方案。',
                'is_builtin': True
            },
            {
                'name': '产品经理',
                'type': 'product_manager',
                'description': '从产品角度分析和建议的专业产品经理',
                'prompt': '你是一个经验丰富的产品经理，擅长从用户体验、产品定位、功能设计等角度分析商业计划的可行性。',
                'is_builtin': True
            },
            {
                'name': '项目经理',
                'type': 'project_manager',
                'description': '从项目管理角度评估风险和执行的计划管理专家',
                'prompt': '你是一个专业的项目经理，擅长评估项目可行性、资源需求、时间规划、风险管理等。',
                'is_builtin': True
            },
            {
                'name': '市场经理',
                'type': 'marketing_manager',
                'description': '从市场推广和商业角度分析的市场营销专家',
                'prompt': '你是一个市场营销专家，擅长市场分析、用户获取、商业模式、竞争分析等。',
                'is_builtin': True
            },
            {
                'name': '技术经理',
                'type': 'tech_manager',
                'description': '从技术实现角度评估的技术管理专家',
                'prompt': '你是一个技术管理专家，擅长技术架构、开发成本、技术可行性、技术风险等分析。',
                'is_builtin': True
            },
            {
                'name': 'CEO',
                'type': 'ceo',
                'description': '从战略和投资角度做最终决策的企业CEO',
                'prompt': '你是一位经验丰富的CEO，需要从战略、投资回报、商业价值等角度评估商业计划，并做出最终决策。',
                'is_builtin': True
            }
        ]

        print("创建角色...")
        for role_data in roles_data:
            existing = Role.query.filter_by(name=role_data['name']).first()
            if existing:
                print(f"  ✅ 角色已存在: {role_data['name']}")
            else:
                role = Role(**role_data)
                db.session.add(role)
                print(f"  ➕ 创建角色: {role_data['name']}")

        db.session.commit()

        # 2. 创建BP讨论流程模板
        existing_flow = FlowTemplate.query.filter_by(name='BP讨论决策流程').first()
        if existing_flow:
            print("  🔄 删除已存在的BP讨论流程")
            FlowStep.query.filter_by(flow_template_id=existing_flow.id).delete()
            db.session.delete(existing_flow)
            db.session.commit()

        flow_template = FlowTemplate(
            name='BP讨论决策流程',
            type='business_discussion',  # 这个类型会被前端识别为无需角色映射
            description='商业计划讨论决策流程：打工人提出BP -> 各部门经理提建议 -> CEO决策',
            version='1.0.0',
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(flow_template)
        db.session.flush()  # 获取ID

        # 3. 创建流程步骤
        steps = [
            {
                'order': 1,
                'speaker_role_ref': '打工人',
                'task_type': 'propose_bp',
                'description': '针对议题提出商业计划书方案',
                'context_scope': 'all',
                '_logic_config': '{"loop_start": true}'
            },
            {
                'order': 2,
                'speaker_role_ref': '产品经理',
                'target_role_ref': '打工人',
                'task_type': 'review_bp',
                'description': '从产品角度对BP提出修改建议',
                'context_scope': 'last_message'
            },
            {
                'order': 3,
                'speaker_role_ref': '项目经理',
                'target_role_ref': '打工人',
                'task_type': 'review_bp',
                'description': '从项目管理角度对BP提出修改建议',
                'context_scope': 'last_message'
            },
            {
                'order': 4,
                'speaker_role_ref': '市场经理',
                'target_role_ref': '打工人',
                'task_type': 'review_bp',
                'description': '从市场角度对BP提出修改建议',
                'context_scope': 'last_message'
            },
            {
                'order': 5,
                'speaker_role_ref': '技术经理',
                'target_role_ref': '打工人',
                'task_type': 'review_bp',
                'description': '从技术角度对BP提出修改建议',
                'context_scope': 'last_message'
            },
            {
                'order': 6,
                'speaker_role_ref': 'CEO',
                'target_role_ref': '打工人',
                'task_type': 'make_decision',
                'description': '决定是否采纳BP。如果采纳，讨论结束；如果不采纳，打工人需要修改后重新提出',
                'context_scope': 'all',
                '_logic_config': '{"decision_point": true, "max_loops": 10}'
            }
        ]

        print("创建流程步骤...")
        for step_data in steps:
            step = FlowStep(
                flow_template_id=flow_template.id,
                **step_data
            )
            db.session.add(step)
            print(f"  ➕ 步骤 {step_data['order']}: {step_data['speaker_role_ref']} - {step_data['description']}")

        db.session.commit()

        print(f"\n✅ BP讨论流程设置完成！")
        print(f"📋 流程ID: {flow_template.id}")
        print(f"📝 流程名称: {flow_template.name}")
        print(f"🎯 角色数量: {len(roles_data)}")
        print(f"⚡ 步骤数量: {len(steps)}")
        print(f"\n💡 使用说明:")
        print(f"1. 启动后端服务: cd backend && python run.py")
        print(f"2. 启动前端服务: cd fronted && npm run dev")
        print(f"3. 在前端选择'BP讨论决策流程'模板")
        print(f"4. 输入议题（如：做一个打败微信的APP）")
        print(f"5. 直接创建会话，无需进行角色映射")
        print(f"6. 开始讨论！")

if __name__ == '__main__':
    setup_bp_discussion()