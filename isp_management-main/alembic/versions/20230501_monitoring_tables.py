"""
Monitoring Module Database Tables

Revision ID: 20230501_monitoring_tables
Revises: 05ae82c589d1
Create Date: 2023-05-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20230501_monitoring_tables'
down_revision = '05ae82c589d1'  # Points to the initial schema migration
branch_labels = None
depends_on = None


def upgrade():
    # Create monitoring_service_logs table
    op.create_table(
        'monitoring_service_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', JSONB, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for better query performance
    op.create_index(op.f('ix_monitoring_service_logs_service_name'), 'monitoring_service_logs', ['service_name'], unique=False)
    op.create_index(op.f('ix_monitoring_service_logs_log_level'), 'monitoring_service_logs', ['log_level'], unique=False)
    op.create_index(op.f('ix_monitoring_service_logs_timestamp'), 'monitoring_service_logs', ['timestamp'], unique=False)
    
    # Create monitoring_system_metrics table
    op.create_table(
        'monitoring_system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('node_id', sa.Integer(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for monitoring_system_metrics
    op.create_index(op.f('ix_monitoring_system_metrics_metric_name'), 'monitoring_system_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_monitoring_system_metrics_timestamp'), 'monitoring_system_metrics', ['timestamp'], unique=False)
    op.create_index(op.f('ix_monitoring_system_metrics_node_id'), 'monitoring_system_metrics', ['node_id'], unique=False)
    
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


def downgrade():
    # Drop monitoring tables
    op.drop_table('monitoring_alerts')
    op.drop_table('monitoring_system_metrics')
    op.drop_table('monitoring_service_logs')
