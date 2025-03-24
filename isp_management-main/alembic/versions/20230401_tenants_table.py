"""
Tenants Table Migration

Revision ID: 20230401_tenants_table
Revises: 05ae82c589d1
Create Date: 2023-04-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20230401_tenants_table'
down_revision = '05ae82c589d1'  # Updated to point to the initial schema migration
branch_labels = None
depends_on = None


def upgrade():
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
    
    # Create indices for better query performance
    op.create_index(op.f('ix_tenants_name'), 'tenants', ['name'], unique=True)
    op.create_index(op.f('ix_tenants_domain'), 'tenants', ['domain'], unique=True)
    op.create_index(op.f('ix_tenants_subscription_plan'), 'tenants', ['subscription_plan'], unique=False)
    op.create_index(op.f('ix_tenants_is_active'), 'tenants', ['is_active'], unique=False)


def downgrade():
    # Drop tenants table
    op.drop_table('tenants')
