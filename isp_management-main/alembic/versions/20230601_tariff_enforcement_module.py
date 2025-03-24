"""
Tariff Enforcement Module Database Migration

Revision ID: 20230601_tariff_enforcement
Revises: 05ae82c589d1
Create Date: 2023-06-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, BIGINT


# revision identifiers, used by Alembic.
revision = '20230601_tariff_enforcement'
<<<<<<< HEAD
down_revision = '05ae82c589d1'  # Updated to point to the initial schema migration
=======
down_revision = '05ae82c589d1'  # Replace with the actual previous revision ID
>>>>>>> 7e0a2fe (Saving local changes before pulling)
branch_labels = None
depends_on = None


def upgrade():
    # Create tariff_plans table
    op.create_table(
        'tariff_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('billing_cycle', sa.String(), nullable=False, server_default='monthly'),
        sa.Column('download_speed', sa.Integer(), nullable=False),
        sa.Column('upload_speed', sa.Integer(), nullable=False),
        sa.Column('data_cap', BIGINT(), nullable=True),
        sa.Column('fup_threshold', BIGINT(), nullable=True),
        sa.Column('throttle_speed_download', sa.Integer(), nullable=True),
        sa.Column('throttle_speed_upload', sa.Integer(), nullable=True),
        sa.Column('radius_policy_id', sa.Integer(), nullable=True),
        sa.Column('throttled_radius_policy_id', sa.Integer(), nullable=True),
        sa.Column('time_restrictions', JSON(), nullable=True),
        sa.Column('features', JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tariff_plans_id'), 'tariff_plans', ['id'], unique=False)
    op.create_index(op.f('ix_tariff_plans_name'), 'tariff_plans', ['name'], unique=True)
    
    # Create user_tariff_plans table
    op.create_table(
        'user_tariff_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tariff_plan_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('start_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('current_cycle_start', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('current_cycle_end', sa.DateTime(), nullable=True),
        sa.Column('data_used', BIGINT(), nullable=False, server_default='0'),
        sa.Column('is_throttled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('throttled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tariff_plan_id'], ['tariff_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_tariff_plans_id'), 'user_tariff_plans', ['id'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_user_id'), 'user_tariff_plans', ['user_id'], unique=False)
    
    # Create user_usage_records table
    op.create_table(
        'user_usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_tariff_plan_id', sa.Integer(), nullable=False),
        sa.Column('download_bytes', BIGINT(), nullable=False, server_default='0'),
        sa.Column('upload_bytes', BIGINT(), nullable=False, server_default='0'),
        sa.Column('total_bytes', BIGINT(), nullable=False, server_default='0'),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_tariff_plan_id'], ['user_tariff_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_usage_records_id'), 'user_usage_records', ['id'], unique=False)
    op.create_index(op.f('ix_user_usage_records_user_tariff_plan_id'), 'user_usage_records', ['user_tariff_plan_id'], unique=False)
    
    # Create tariff_plan_changes table
    op.create_table(
        'tariff_plan_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('previous_plan_id', sa.Integer(), nullable=False),
        sa.Column('new_plan_id', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('effective_date', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('prorated_credit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('prorated_charge', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['new_plan_id'], ['tariff_plans.id'], ),
        sa.ForeignKeyConstraint(['previous_plan_id'], ['tariff_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tariff_plan_changes_id'), 'tariff_plan_changes', ['id'], unique=False)
    op.create_index(op.f('ix_tariff_plan_changes_user_id'), 'tariff_plan_changes', ['user_id'], unique=False)
    
    # Create tariff_policy_actions table
    op.create_table(
        'tariff_policy_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tariff_plan_id', sa.Integer(), nullable=False),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('threshold_value', BIGINT(), nullable=True),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_params', JSON(), nullable=True),
        sa.Column('notification_template_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tariff_plan_id'], ['tariff_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tariff_policy_actions_id'), 'tariff_policy_actions', ['id'], unique=False)
    op.create_index(op.f('ix_tariff_policy_actions_tariff_plan_id'), 'tariff_policy_actions', ['tariff_plan_id'], unique=False)


def downgrade():
    # Drop tables in reverse order of creation
    op.drop_table('tariff_policy_actions')
    op.drop_table('tariff_plan_changes')
    op.drop_table('user_usage_records')
    op.drop_table('user_tariff_plans')
    op.drop_table('tariff_plans')
