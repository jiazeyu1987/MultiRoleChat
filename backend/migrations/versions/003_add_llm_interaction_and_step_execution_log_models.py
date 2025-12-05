"""Add LLM interaction and step execution log models

Revision ID: 003
Revises: 002
Create Date: 2024-12-04 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002_allow_null_speaker_session_role'
branch_labels = None
depends_on = None


def upgrade():
    # Create llm_interactions table
    op.create_table('llm_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('step_id', sa.Integer(), nullable=True),
        sa.Column('session_role_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('user_prompt', sa.Text(), nullable=False),
        sa.Column('full_prompt', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('finish_reason', sa.String(length=50), nullable=True),
        sa.Column('usage_input_tokens', sa.Integer(), nullable=True),
        sa.Column('usage_output_tokens', sa.Integer(), nullable=True),
        sa.Column('usage_total_tokens', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['session_role_id'], ['session_roles.id'], ),
        sa.ForeignKeyConstraint(['step_id'], ['flow_steps.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_interactions_created_at'), 'llm_interactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_llm_interactions_session_id'), 'llm_interactions', ['session_id'], unique=False)
    op.create_index(op.f('ix_llm_interactions_status'), 'llm_interactions', ['status'], unique=False)

    # Create step_execution_logs table
    op.create_table('step_execution_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('step_id', sa.Integer(), nullable=False),
        sa.Column('parent_log_id', sa.Integer(), nullable=True),
        sa.Column('execution_order', sa.Integer(), nullable=False),
        sa.Column('round_index', sa.Integer(), nullable=True),
        sa.Column('loop_iteration', sa.Integer(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('result_type', sa.String(length=50), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.Column('condition_evaluation', sa.Boolean(), nullable=True),
        sa.Column('loop_check_result', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('step_snapshot', sa.Text(), nullable=True),
        sa.Column('context_snapshot', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['parent_log_id'], ['step_execution_logs.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['step_id'], ['flow_steps.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_step_execution_logs_created_at'), 'step_execution_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_step_execution_logs_execution_order'), 'step_execution_logs', ['execution_order'], unique=False)
    op.create_index(op.f('ix_step_execution_logs_session_id'), 'step_execution_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_step_execution_logs_status'), 'step_execution_logs', ['status'], unique=False)


def downgrade():
    # Drop step_execution_logs table
    op.drop_index(op.f('ix_step_execution_logs_status'), table_name='step_execution_logs')
    op.drop_index(op.f('ix_step_execution_logs_session_id'), table_name='step_execution_logs')
    op.drop_index(op.f('ix_step_execution_logs_execution_order'), table_name='step_execution_logs')
    op.drop_index(op.f('ix_step_execution_logs_created_at'), table_name='step_execution_logs')
    op.drop_table('step_execution_logs')

    # Drop llm_interactions table
    op.drop_index(op.f('ix_llm_interactions_status'), table_name='llm_interactions')
    op.drop_index(op.f('ix_llm_interactions_session_id'), table_name='llm_interactions')
    op.drop_index(op.f('ix_llm_interactions_created_at'), table_name='llm_interactions')
    op.drop_table('llm_interactions')