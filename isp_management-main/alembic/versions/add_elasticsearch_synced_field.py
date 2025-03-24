"""Add elasticsearch_synced field to monitoring tables

Revision ID: add_elasticsearch_synced_field
Revises: 20230501_monitoring_tables
Create Date: 2023-07-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_elasticsearch_synced_field'
<<<<<<< HEAD
down_revision = '20230501_monitoring_tables'  # Updated to point to the monitoring tables migration
=======
down_revision = '05ae82c589d1'  # Replace with the actual previous revision ID
>>>>>>> 7e0a2fe (Saving local changes before pulling)
branch_labels = None
depends_on = None


def upgrade():
    # Add elasticsearch_synced column to monitoring_service_logs table
    op.add_column('monitoring_service_logs', sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_monitoring_service_logs_elasticsearch_synced'), 'monitoring_service_logs', ['elasticsearch_synced'], unique=False)
    
    # Add elasticsearch_synced column to monitoring_system_metrics table
    op.add_column('monitoring_system_metrics', sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_monitoring_system_metrics_elasticsearch_synced'), 'monitoring_system_metrics', ['elasticsearch_synced'], unique=False)


def downgrade():
    # Remove elasticsearch_synced column from monitoring_service_logs table
    op.drop_index(op.f('ix_monitoring_service_logs_elasticsearch_synced'), table_name='monitoring_service_logs')
    op.drop_column('monitoring_service_logs', 'elasticsearch_synced')
    
    # Remove elasticsearch_synced column from monitoring_system_metrics table
    op.drop_index(op.f('ix_monitoring_system_metrics_elasticsearch_synced'), table_name='monitoring_system_metrics')
    op.drop_column('monitoring_system_metrics', 'elasticsearch_synced')
