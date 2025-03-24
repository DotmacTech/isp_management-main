"""Add billing module enhancements

Revision ID: c8c4b27b3053
Revises: 05ae82c589d1
Create Date: 2025-03-14 06:21:10.279464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8c4b27b3053'
down_revision: Union[str, None] = '05ae82c589d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with billing module enhancements."""
    
    # Create discounts table
    op.create_table(
        'discounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('discount_type', sa.String(length=20), nullable=False),
        sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_percentage', sa.Boolean(), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create invoice_discounts table
    op.create_table(
        'invoice_discounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('discount_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['discount_id'], ['discounts.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create credit_notes table
    op.create_table(
        'credit_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('remaining_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create credit_note_applications table
    op.create_table(
        'credit_note_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('credit_note_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['credit_note_id'], ['credit_notes.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create tax_rates table
    op.create_table(
        'tax_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create invoice_taxes table
    op.create_table(
        'invoice_taxes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('tax_rate_id', sa.Integer(), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['tax_rate_id'], ['tax_rates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indices for better query performance
    op.create_index(op.f('ix_discounts_is_active'), 'discounts', ['is_active'], unique=False)
    op.create_index(op.f('ix_invoice_discounts_invoice_id'), 'invoice_discounts', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_credit_notes_user_id'), 'credit_notes', ['user_id'], unique=False)
    op.create_index(op.f('ix_credit_notes_status'), 'credit_notes', ['status'], unique=False)
    op.create_index(op.f('ix_credit_note_applications_invoice_id'), 'credit_note_applications', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_tax_rates_country'), 'tax_rates', ['country'], unique=False)
    op.create_index(op.f('ix_tax_rates_is_active'), 'tax_rates', ['is_active'], unique=False)
    op.create_index(op.f('ix_invoice_taxes_invoice_id'), 'invoice_taxes', ['invoice_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema by removing billing module enhancements."""
    # Drop tables in reverse order to avoid foreign key constraints
    op.drop_table('invoice_taxes')
    op.drop_table('tax_rates')
    op.drop_table('credit_note_applications')
    op.drop_table('credit_notes')
    op.drop_table('invoice_discounts')
    op.drop_table('discounts')
