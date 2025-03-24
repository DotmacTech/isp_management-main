"""Add service availability monitoring tables

Revision ID: 002
Revises: 001
Create Date: 2025-03-14 14:07:16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    protocol_type = postgresql.ENUM('HTTP', 'HTTPS', 'TCP', 'UDP', 'DNS', 'ICMP', name='protocol_type')
    protocol_type.create(op.get_bind())
    
    status_type = postgresql.ENUM('UP', 'DOWN', 'DEGRADED', 'UNKNOWN', name='status_type')
    status_type.create(op.get_bind())
    
    severity_level = postgresql.ENUM('CRITICAL', 'MAJOR', 'MINOR', 'WARNING', name='severity_level')
    severity_level.create(op.get_bind())
    
    # Create service_endpoints table
    op.create_table(
        'service_endpoints',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(255), nullable=False),
        sa.Column('protocol', sa.Enum('HTTP', 'HTTPS', 'TCP', 'UDP', 'DNS', 'ICMP', name='protocol_type'), nullable=False),
        sa.Column('check_interval', sa.Integer(), nullable=False, default=60),
        sa.Column('timeout', sa.Integer(), nullable=False, default=5),
        sa.Column('retries', sa.Integer(), nullable=False, default=3),
        sa.Column('expected_status_code', sa.Integer(), nullable=True),
        sa.Column('expected_response_pattern', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    
    # Create service_statuses table
    op.create_table(
        'service_statuses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('UP', 'DOWN', 'DEGRADED', 'UNKNOWN', name='status_type'), nullable=False),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, default=False),
    )
    op.create_index('ix_service_statuses_endpoint_id', 'service_statuses', ['endpoint_id'])
    op.create_index('ix_service_statuses_timestamp', 'service_statuses', ['timestamp'])
    op.create_index('ix_service_statuses_elasticsearch_synced', 'service_statuses', ['elasticsearch_synced'])
    
    # Create service_outages table
    op.create_table(
        'service_outages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.Enum('CRITICAL', 'MAJOR', 'MINOR', 'WARNING', name='severity_level'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('ix_service_outages_endpoint_id', 'service_outages', ['endpoint_id'])
    op.create_index('ix_service_outages_start_time', 'service_outages', ['start_time'])
    op.create_index('ix_service_outages_resolved', 'service_outages', ['resolved'])
    op.create_index('ix_service_outages_elasticsearch_synced', 'service_outages', ['elasticsearch_synced'])
    
    # Create maintenance_windows table
    op.create_table(
        'maintenance_windows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('ix_maintenance_windows_start_time', 'maintenance_windows', ['start_time'])
    op.create_index('ix_maintenance_windows_end_time', 'maintenance_windows', ['end_time'])
    
    # Create maintenance_window_endpoints table (many-to-many relationship)
    op.create_table(
        'maintenance_window_endpoints',
        sa.Column('window_id', sa.String(36), sa.ForeignKey('maintenance_windows.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade():
    # Drop tables
    op.drop_table('maintenance_window_endpoints')
    op.drop_table('maintenance_windows')
    op.drop_table('service_outages')
    op.drop_table('service_statuses')
    op.drop_table('service_endpoints')
    
    # Drop enum types
    op.execute('DROP TYPE protocol_type')
    op.execute('DROP TYPE status_type')
    op.execute('DROP TYPE severity_level')
