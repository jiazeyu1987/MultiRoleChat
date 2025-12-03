import os
from app import create_app, db

app = create_app()

@app.cli.command()
def init_db():
    """初始化数据库"""
    db.create_all()
    print("数据库初始化完成！")

@app.cli.command()
def create_builtin_roles():
    """创建系统预置角色"""
    from app.models import Role

    builtin_roles = [
        {
            'name': '老师',
            'type': 'teacher',
            'description': '负责教学指导和知识传授的专业教师角色',
            'style': '鼓励式、引导式、耐心细致',
            'constraints': '不涉及超出教学范围的专业建议',
            'focus_points': ['学习效果', '概念理解', '实践应用'],
            'is_builtin': True
        },
        {
            'name': '学生',
            'type': 'student',
            'description': '积极学习的学生角色，代表学习者视角',
            'style': '好奇、求知、有时会犯错误',
            'constraints': '仅从学习者角度提问，不作专业判断',
            'focus_points': ['知识点掌握', '学习方法', '实践练习'],
            'is_builtin': True
        },
        {
            'name': '专家',
            'type': 'expert',
            'description': '具有丰富专业知识和经验的领域专家',
            'style': '严谨、专业、有说服力',
            'constraints': '仅提供专业意见，不承担法律责任',
            'focus_points': ['专业性', '可行性', '风险评估'],
            'is_builtin': True
        },
        {
            'name': '评审员',
            'type': 'reviewer',
            'description': '负责方案评审和质量把控的专业评审人员',
            'style': '客观、公正、注重细节',
            'constraints': '仅提供评审意见，不做最终决策',
            'focus_points': ['合规性', '质量标准', '改进建议'],
            'is_builtin': True
        }
    ]

    for role_data in builtin_roles:
        existing_role = Role.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            role = Role(**role_data)
            db.session.add(role)

    db.session.commit()
    print("系统预置角色创建完成！")

@app.cli.command()
def clear_templates():
    """清理所有流程模板和步骤"""
    from app.models import FlowTemplate, FlowStep

    # 查看当前数据
    template_count = FlowTemplate.query.count()
    step_count = FlowStep.query.count()

    print(f"当前数据库中有 {template_count} 个模板和 {step_count} 个步骤")

    # 删除所有步骤（先删除子表）
    deleted_steps = FlowStep.query.delete()

    # 删除所有模板
    deleted_templates = FlowTemplate.query.delete()

    # 提交更改
    db.session.commit()

    print(f"✅ 清理完成！删除了 {deleted_templates} 个模板和 {deleted_steps} 个步骤")

@app.cli.command()
def create_builtin_flows():
    """创建系统预置流程模板"""
    from app.models import FlowTemplate, FlowStep
    from datetime import datetime

    # 教学对话模板
    teaching_flow = FlowTemplate(
        name='教学对话模板',
        type='teaching',
        description='老师提出问题 -> 学生尝试回答 -> 老师点评 -> 老师总结',
        version='1.0.0',
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(teaching_flow)
    db.session.flush()  # 获取teaching_flow.id

    teaching_steps = [
        {
            'order': 1,
            'speaker_role_ref': 'teacher',
            'task_type': 'ask_question',
            'context_scope': 'none',
            'description': '老师提出学习问题'
        },
        {
            'order': 2,
            'speaker_role_ref': 'student',
            'target_role_ref': 'teacher',
            'task_type': 'answer_question',
            'context_scope': 'last_message',
            'description': '学生回答问题'
        },
        {
            'order': 3,
            'speaker_role_ref': 'teacher',
            'target_role_ref': 'student',
            'task_type': 'review_answer',
            'context_scope': 'last_round',
            'description': '老师点评学生回答'
        },
        {
            'order': 4,
            'speaker_role_ref': 'teacher',
            'task_type': 'summarize',
            'context_scope': 'all',
            'description': '老师总结知识点'
        }
    ]

    for step_data in teaching_steps:
        step = FlowStep(
            flow_template_id=teaching_flow.id,
            **step_data
        )
        db.session.add(step)

    db.session.commit()
    print("系统预置流程模板创建完成！")

if __name__ == '__main__':
    app.run(
        host=app.config['API_HOST'],
        port=app.config['API_PORT'],
        debug=app.config['API_DEBUG']
    )