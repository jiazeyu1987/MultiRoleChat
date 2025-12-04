#!/usr/bin/env python3
"""
创建简化BP讨论流程模板
这个流程不需要角色映射，直接使用预定义的角色
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app, db
from backend.app.models import FlowTemplate, FlowStep
from datetime import datetime

def create_simple_bp_flow():
    """创建简化的BP讨论流程模板"""
    app = create_app()

    with app.app_context():
        # 检查是否已存在
        existing = FlowTemplate.query.filter_by(name='简化BP讨论流程').first()
        if existing:
            print("流程模板已存在，正在删除...")
            # 删除相关步骤
            FlowStep.query.filter_by(flow_template_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        # 创建流程模板
        flow_template = FlowTemplate(
            name='简化BP讨论流程',
            type='business_discussion',
            description='简化的商业计划讨论流程，打工人提出BP，各角色提建议，CEO决策',
            version='1.0.0',
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(flow_template)
        db.session.flush()  # 获取ID

        # 定义流程步骤
        steps = [
            {
                'order': 1,
                'speaker_role_ref': '打工人',
                'task_type': 'propose_bp',
                'description': '针对议题提出商业计划书',
                'context_scope': 'all'
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
                'task_type': 'decision',
                'description': '决定是否采纳BP，如果采纳则结束，如果不采纳则继续下一轮',
                'context_scope': 'all'
            }
        ]

        # 创建步骤
        for step_data in steps:
            step = FlowStep(
                flow_template_id=flow_template.id,
                **step_data
            )
            db.session.add(step)

        # 为最后一步添加循环配置
        steps[-1]['_logic_config'] = {
            "loop_type": "conditional",
            "condition": "bp_rejected",
            "loop_back_to": 1,  # 回到第一步，打工人重新提BP
            "max_loops": 10  # 最多循环10次
        }

        db.session.commit()
        print(f"✅ 成功创建简化BP讨论流程模板 (ID: {flow_template.id})")
        print("📋 流程步骤:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step['speaker_role_ref']}: {step['description']}")

if __name__ == '__main__':
    create_simple_bp_flow()