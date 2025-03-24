"""Add configuration management tables

Revision ID: config_management_tables
Create Date: 2025-03-14 17:08:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'config_management_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    config_environment = postgresql.ENUM('development', 'testing', 'staging', 'production', 'all', 
                                         name='configenvironment', create_type=True)
    config_environment.create(op.get_bind())
    
    config_category = postgresql.ENUM('system', 'security', 'network', 'billing', 'monitoring', 
                                      'notification', 'integration', 'custom', 
                                      name='configcategory', create_type=True)
    config_category.create(op.get_bind())
    
    # Create configurations table
    op.create_table(
        'configurations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('environment', sa.Enum('development', 'testing', 'staging', 'production', 'all', 
                                        name='configenvironment'), nullable=False, default='all'),
        sa.Column('category', sa.Enum('system', 'security', 'network', 'billing', 'monitoring', 
                                     'notification', 'integration', 'custom', 
                                     name='configcategory'), nullable=False, default='system'),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=False),
        sa.Column('validation_schema', sa.JSON(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_by', sa.String(50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('key', 'environment', 'is_active', name='uix_config_key_env_active')
    )
    
    # Create configuration_history table
    op.create_table(
        'configuration_history',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('configuration_id', sa.String(50), sa.ForeignKey('configurations.id'), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('environment', sa.Enum('development', 'testing', 'staging', 'production', 'all', 
                                        name='configenvironment'), nullable=False),
        sa.Column('category', sa.Enum('system', 'security', 'network', 'billing', 'monitoring', 
                                     'notification', 'integration', 'custom', 
                                     name='configcategory'), nullable=False),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.text('NOW()'))
    )
    
    # Create configuration_groups table
    op.create_table(
        'configuration_groups',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_by', sa.String(50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    
    # Create configuration_group_items table
    op.create_table(
        'configuration_group_items',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('group_id', sa.String(50), sa.ForeignKey('configuration_groups.id'), nullable=False),
        sa.Column('configuration_id', sa.String(50), sa.ForeignKey('configurations.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.text('NOW()')),
        sa.UniqueConstraint('group_id', 'configuration_id', name='uix_config_group_item')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_configurations_key', 'configurations', ['key'])
    op.create_index('ix_configurations_environment', 'configurations', ['environment'])
    op.create_index('ix_configurations_category', 'configurations', ['category'])
    op.create_index('ix_configurations_is_active', 'configurations', ['is_active'])
    op.create_index('ix_configuration_history_configuration_id', 'configuration_history', ['configuration_id'])
    op.create_index('ix_configuration_history_key', 'configuration_history', ['key'])
    op.create_index('ix_configuration_history_created_at', 'configuration_history', ['created_at'])
    op.create_index('ix_configuration_groups_name', 'configuration_groups', ['name'])
    op.create_index('ix_configuration_group_items_group_id', 'configuration_group_items', ['group_id'])
    op.create_index('ix_configuration_group_items_configuration_id', 'configuration_group_items', ['configuration_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_configuration_group_items_configuration_id', table_name='configuration_group_items')
    op.drop_index('ix_configuration_group_items_group_id', table_name='configuration_group_items')
    op.drop_index('ix_configuration_groups_name', table_name='configuration_groups')
    op.drop_index('ix_configuration_history_created_at', table_name='configuration_history')
    op.drop_index('ix_configuration_history_key', table_name='configuration_history')
    op.drop_index('ix_configuration_history_configuration_id', table_name='configuration_history')
    op.drop_index('ix_configurations_is_active', table_name='configurations')
    op.drop_index('ix_configurations_category', table_name='configurations')
    op.drop_index('ix_configurations_environment', table_name='configurations')
    op.drop_index('ix_configurations_key', table_name='configurations')
    
    # Drop tables
    op.drop_table('configuration_group_items')
    op.drop_table('configuration_groups')
    op.drop_table('configuration_history')
    op.drop_table('configurations')
    
    # Drop enum types
    op.execute('DROP TYPE configcategory')
    op.execute('DROP TYPE configenvironment')
