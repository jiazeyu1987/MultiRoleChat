#!/usr/bin/env python3
"""Debug the logic_config_dict issue"""

from app import create_app
import json

def test_logic_config_issue():
    """Test the logic_config_dict property issue"""
    app = create_app()

    with app.app_context():
        try:
            # Test 1: Try to create a FlowStep with logic_config_dict
            from app.models.flow import FlowStep

            print("Test 1: Creating FlowStep with empty logic_config_dict")
            step = FlowStep(
                flow_template_id=1,
                order=1,
                speaker_role_ref='Product Manager',
                task_type='ask_question',
                context_scope_parsed=['Technical Manager'],
                logic_config_dict={},  # Empty dict
                description='Test step'
            )
            print("SUCCESS: FlowStep created successfully with empty logic_config_dict")

            # Test 2: Try to create with logic_config data
            print("\nTest 2: Creating FlowStep with logic_config data")
            step2 = FlowStep(
                flow_template_id=1,
                order=2,
                speaker_role_ref='Technical Manager',
                task_type='answer_question',
                context_scope_parsed=['Product Manager'],
                logic_config_dict={"type": "condition", "value": "test"},
                description='Test step with config'
            )
            print("SUCCESS: FlowStep created successfully with logic_config data")

            # Test 3: Check what happens when we get the property
            print("\nTest 3: Checking logic_config_dict property")
            print(f"Step 1 logic_config_dict: {step.logic_config_dict}")
            print(f"Step 2 logic_config_dict: {step2.logic_config_dict}")

            # Test 4: Try to reproduce the exact error scenario
            print("\nTest 4: Reproduce service layer scenario")
            step_data = {
                'order': 1,
                'speaker_role_ref': 'Product Manager',
                'task_type': 'ask_question',
                'context_scope': ['Technical Manager', 'Quality Manager'],
                'description': 'Test step with multiple roles'
            }

            logic_config_value = step_data.get('logic_config', {})
            print(f"logic_config_value from step_data: {logic_config_value}")
            print(f"type of logic_config_value: {type(logic_config_value)}")

            # Try to assign it directly
            step3 = FlowStep(
                flow_template_id=1,
                order=step_data['order'],
                speaker_role_ref=step_data['speaker_role_ref'],
                task_type=step_data['task_type'],
                context_scope_parsed=step_data['context_scope'],
                logic_config_dict=logic_config_value,
                description=step_data.get('description', '')
            )
            print("SUCCESS: Service layer scenario reproduced successfully")

            return True

        except Exception as e:
            print(f"Error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    test_logic_config_issue()