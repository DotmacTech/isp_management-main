"""Create network_nodes table

Revision ID: network_node_table
Revises: elasticsearch_sync_fields
Create Date: 2023-07-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'network_node_table'
down_revision = 'elasticsearch_sync_fields'  # Assuming the previous migration was for elasticsearch_sync_fields
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type for node_type
    node_type_enum = postgresql.ENUM('router', 'switch', 'access_point', 'server', 'firewall', 'load_balancer', 'other', 
                                    name='nodetype')
    node_type_enum.create(op.get_bind())
    
    # Create network_nodes table
    op.create_table('network_nodes',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False, index=True),
        sa.Column('type', sa.Enum('router', 'switch', 'access_point', 'server', 'firewall', 'load_balancer', 'other', 
                                name='nodetype'), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        
        # Hardware information
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('firmware_version', sa.String(50), nullable=True),
        
        # Network information
        sa.Column('mac_address', sa.String(17), nullable=True),
        sa.Column('subnet_mask', sa.String(45), nullable=True),
        sa.Column('gateway', sa.String(45), nullable=True),
        sa.Column('dns_servers', postgresql.JSONB, nullable=True),
        
        # Status information
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uptime', sa.Float, nullable=True),
        
        # Management information
        sa.Column('snmp_community', sa.String(50), nullable=True),
        sa.Column('snmp_version', sa.String(10), nullable=True),
        sa.Column('ssh_username', sa.String(50), nullable=True),
        sa.Column('ssh_port', sa.Integer, default=22),
        sa.Column('http_port', sa.Integer, nullable=True),
        sa.Column('https_port', sa.Integer, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )
    
    # Add index for faster lookups
    op.create_index('ix_network_nodes_ip_address', 'network_nodes', ['ip_address'])
    op.create_index('ix_network_nodes_type', 'network_nodes', ['type'])
    op.create_index('ix_network_nodes_is_active', 'network_nodes', ['is_active'])


def downgrade():
    # Drop table and indexes
    op.drop_index('ix_network_nodes_is_active', table_name='network_nodes')
    op.drop_index('ix_network_nodes_type', table_name='network_nodes')
    op.drop_index('ix_network_nodes_ip_address', table_name='network_nodes')
    op.drop_table('network_nodes')
    
    # Drop enum type
    op.execute('DROP TYPE nodetype')
