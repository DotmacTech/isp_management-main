"""
Add elasticsearch_synced field to Configuration models.

Revision ID: add_config_elasticsearch_synced
Revises: config_management_tables
Create Date: 2025-03-14 17:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'add_config_elasticsearch_synced'
down_revision = 'config_management_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add elasticsearch_synced field to configuration table
    op.add_column(
        'configuration',
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add elasticsearch_synced field to configuration_history table
    op.add_column(
        'configuration_history',
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add elasticsearch_synced field to configuration_group table
    op.add_column(
        'configuration_group',
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    # Remove elasticsearch_synced field from configuration table
    op.drop_column('configuration', 'elasticsearch_synced')
    
    # Remove elasticsearch_synced field from configuration_history table
    op.drop_column('configuration_history', 'elasticsearch_synced')
    
    # Remove elasticsearch_synced field from configuration_group table
    op.drop_column('configuration_group', 'elasticsearch_synced')
