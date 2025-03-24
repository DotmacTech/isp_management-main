"""
Add service monitoring tables.

Revision ID: 002
Revises: 001
Create Date: 2025-03-14 14:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
import uuid
from datetime import datetime

# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

# Create enums
protocol_type = ENUM('http', 'https', 'tcp', 'udp', 'icmp', 'dns', name='protocol_type')
status_type = ENUM('up', 'down', 'degraded', 'maintenance', 'unknown', name='status_type')
severity_level = ENUM('critical', 'high', 'medium', 'low', 'info', name='severity_level')


def upgrade():
    # Create protocol_type enum if it doesn't exist
    op.execute('CREATE TYPE IF NOT EXISTS protocol_type AS ENUM '
               "('http', 'https', 'tcp', 'udp', 'icmp', 'dns')")
    
    # Create status_type enum if it doesn't exist
    op.execute('CREATE TYPE IF NOT EXISTS status_type AS ENUM '
               "('up', 'down', 'degraded', 'maintenance', 'unknown')")
    
    # Create severity_level enum if it doesn't exist
    op.execute('CREATE TYPE IF NOT EXISTS severity_level AS ENUM '
               "('critical', 'high', 'medium', 'low', 'info')")
    
    # Create service_endpoints table
    op.create_table(
        'service_endpoints',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(255), nullable=False),
        sa.Column('protocol', sa.Enum('http', 'https', 'tcp', 'udp', 'icmp', 'dns', 
                                     name='protocol_type', create_type=False), nullable=False),
        sa.Column('check_interval', sa.Integer(), nullable=False, default=60),
        sa.Column('timeout', sa.Integer(), nullable=False, default=5),
        sa.Column('retries', sa.Integer(), nullable=False, default=3),
        sa.Column('expected_status_code', sa.Integer(), nullable=True),
        sa.Column('expected_pattern', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, 
                  onupdate=datetime.utcnow)
    )
    
    # Create service_statuses table
    op.create_table(
        'service_statuses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id'), nullable=False),
        sa.Column('status', sa.Enum('up', 'down', 'degraded', 'maintenance', 'unknown', 
                                   name='status_type', create_type=False), nullable=False),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('error_message', sa.String(1024), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, default=False)
    )
    
    # Create service_outages table
    op.create_table(
        'service_outages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id'), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('severity', sa.Enum('critical', 'high', 'medium', 'low', 'info', 
                                     name='severity_level', create_type=False), 
                  nullable=False, default='high'),
        sa.Column('description', sa.String(1024), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolution_notes', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, 
                  onupdate=datetime.utcnow)
    )
    
    # Create maintenance_windows table
    op.create_table(
        'maintenance_windows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('endpoint_id', sa.String(36), sa.ForeignKey('service_endpoints.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1024), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, 
                  onupdate=datetime.utcnow)
    )
    
    # Create indexes
    op.create_index('ix_service_endpoints_is_active', 'service_endpoints', ['is_active'])
    op.create_index('ix_service_statuses_endpoint_id', 'service_statuses', ['endpoint_id'])
    op.create_index('ix_service_statuses_timestamp', 'service_statuses', ['timestamp'])
    op.create_index('ix_service_statuses_elasticsearch_synced', 'service_statuses', ['elasticsearch_synced'])
    op.create_index('ix_service_outages_endpoint_id', 'service_outages', ['endpoint_id'])
    op.create_index('ix_service_outages_resolved', 'service_outages', ['resolved'])
    op.create_index('ix_maintenance_windows_endpoint_id', 'maintenance_windows', ['endpoint_id'])
    op.create_index('ix_maintenance_windows_is_active', 'maintenance_windows', ['is_active'])
    op.create_index('ix_maintenance_windows_start_time', 'maintenance_windows', ['start_time'])
    op.create_index('ix_maintenance_windows_end_time', 'maintenance_windows', ['end_time'])


def downgrade():
    # Drop tables
    op.drop_table('maintenance_windows')
    op.drop_table('service_outages')
    op.drop_table('service_statuses')
    op.drop_table('service_endpoints')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS severity_level')
    op.execute('DROP TYPE IF EXISTS status_type')
    op.execute('DROP TYPE IF EXISTS protocol_type')
