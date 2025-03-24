"""
Consolidated migration to fix circular dependencies

Revision ID: consolidated_migrations
Revises: 
Create Date: 2025-03-16 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, JSONB, BIGINT


# revision identifiers, used by Alembic.
revision = 'consolidated_migrations'
down_revision = None  # This is a new base migration
branch_labels = None
depends_on = None


def upgrade():
    # Create users table (from initial schema)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create invoices table (from initial schema)
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create payments table (from initial schema)
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create monitoring_service_logs table
    op.create_table(
        'monitoring_service_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for monitoring_service_logs
    op.create_index(op.f('ix_monitoring_service_logs_service_name'), 'monitoring_service_logs', ['service_name'], unique=False)
    op.create_index(op.f('ix_monitoring_service_logs_log_level'), 'monitoring_service_logs', ['log_level'], unique=False)
    op.create_index(op.f('ix_monitoring_service_logs_timestamp'), 'monitoring_service_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_monitoring_service_logs_elasticsearch_synced'), 'monitoring_service_logs', ['elasticsearch_synced'], unique=False)
    
    # Create monitoring_system_metrics table
    op.create_table(
        'monitoring_system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('node_id', sa.Integer(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for monitoring_system_metrics
    op.create_index(op.f('ix_monitoring_system_metrics_metric_name'), 'monitoring_system_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_monitoring_system_metrics_timestamp'), 'monitoring_system_metrics', ['timestamp'], unique=False)
    op.create_index(op.f('ix_monitoring_system_metrics_node_id'), 'monitoring_system_metrics', ['node_id'], unique=False)
    op.create_index(op.f('ix_monitoring_system_metrics_elasticsearch_synced'), 'monitoring_system_metrics', ['elasticsearch_synced'], unique=False)
    
    # Create monitoring_alerts table
    op.create_table(
        'monitoring_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for monitoring_alerts
    op.create_index(op.f('ix_monitoring_alerts_alert_type'), 'monitoring_alerts', ['alert_type'], unique=False)
    op.create_index(op.f('ix_monitoring_alerts_severity'), 'monitoring_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_monitoring_alerts_timestamp'), 'monitoring_alerts', ['timestamp'], unique=False)
    op.create_index(op.f('ix_monitoring_alerts_resolved'), 'monitoring_alerts', ['resolved'], unique=False)
    
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=False),
        sa.Column('subscription_plan', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('settings', JSONB, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for tenants
    op.create_index(op.f('ix_tenants_name'), 'tenants', ['name'], unique=True)
    op.create_index(op.f('ix_tenants_domain'), 'tenants', ['domain'], unique=True)
    op.create_index(op.f('ix_tenants_subscription_plan'), 'tenants', ['subscription_plan'], unique=False)
    op.create_index(op.f('ix_tenants_is_active'), 'tenants', ['is_active'], unique=False)
    
    # Create chatbot_queries table
    op.create_table(
        'chatbot_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('context_data', JSON(), nullable=True),
        sa.Column('intent', sa.String(length=100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('entities', JSON(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('ai_service_name', sa.String(length=50), nullable=True),
        sa.Column('ai_model_version', sa.String(length=50), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for chatbot_queries
    op.create_index(op.f('ix_chatbot_queries_created_at'), 'chatbot_queries', ['created_at'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_id'), 'chatbot_queries', ['id'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_intent'), 'chatbot_queries', ['intent'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_tenant_id'), 'chatbot_queries', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_user_id'), 'chatbot_queries', ['user_id'], unique=False)
    
    # Create chatbot_feedback table
    op.create_table(
        'chatbot_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['query_id'], ['chatbot_queries.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for chatbot_feedback
    op.create_index(op.f('ix_chatbot_feedback_id'), 'chatbot_feedback', ['id'], unique=False)
    op.create_index(op.f('ix_chatbot_feedback_query_id'), 'chatbot_feedback', ['query_id'], unique=False)
    op.create_index(op.f('ix_chatbot_feedback_user_id'), 'chatbot_feedback', ['user_id'], unique=False)
    
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
    
    # Create indices for tariff_plans
    op.create_index(op.f('ix_tariff_plans_id'), 'tariff_plans', ['id'], unique=False)
    op.create_index(op.f('ix_tariff_plans_name'), 'tariff_plans', ['name'], unique=True)
    
    # Create tariff_usage_records table
    op.create_table(
        'tariff_usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tariff_id', sa.Integer(), nullable=False),
        sa.Column('data_used', BIGINT(), nullable=False),
        sa.Column('upload_used', BIGINT(), nullable=False),
        sa.Column('download_used', BIGINT(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_throttled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cycle_start_date', sa.Date(), nullable=False),
        sa.Column('cycle_end_date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['tariff_id'], ['tariff_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for tariff_usage_records
    op.create_index(op.f('ix_tariff_usage_records_cycle_end_date'), 'tariff_usage_records', ['cycle_end_date'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_cycle_start_date'), 'tariff_usage_records', ['cycle_start_date'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_id'), 'tariff_usage_records', ['id'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_is_throttled'), 'tariff_usage_records', ['is_throttled'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_tariff_id'), 'tariff_usage_records', ['tariff_id'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_timestamp'), 'tariff_usage_records', ['timestamp'], unique=False)
    op.create_index(op.f('ix_tariff_usage_records_user_id'), 'tariff_usage_records', ['user_id'], unique=False)
    
    # Create user_tariff_plans table
    op.create_table(
        'user_tariff_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tariff_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tariff_id'], ['tariff_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for user_tariff_plans
    op.create_index(op.f('ix_user_tariff_plans_end_date'), 'user_tariff_plans', ['end_date'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_id'), 'user_tariff_plans', ['id'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_is_active'), 'user_tariff_plans', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_start_date'), 'user_tariff_plans', ['start_date'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_tariff_id'), 'user_tariff_plans', ['tariff_id'], unique=False)
    op.create_index(op.f('ix_user_tariff_plans_user_id'), 'user_tariff_plans', ['user_id'], unique=False)


def downgrade():
    # Drop all tables in reverse order (dependent tables first, then their parents)
    op.drop_table('user_tariff_plans')
    op.drop_table('tariff_usage_records')
    op.drop_table('chatbot_feedback')
    op.drop_table('chatbot_queries')
    op.drop_table('tariff_plans')
    op.drop_table('tenants')
    op.drop_table('monitoring_alerts')
    op.drop_table('monitoring_system_metrics')
    op.drop_table('monitoring_service_logs')
    op.drop_table('payments')
    op.drop_table('invoices')
    op.drop_table('users')
