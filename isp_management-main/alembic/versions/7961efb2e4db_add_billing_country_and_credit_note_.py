"""Add billing_country and credit note relationships

Revision ID: 7961efb2e4db
Revises: 9c4533e6d07c
Create Date: 2025-03-14 06:00:11.174384

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '7961efb2e4db'
down_revision = '9c4533e6d07c'
branch_labels = None
depends_on = None


def upgrade():
    # First add the column as nullable
    op.add_column('invoices', sa.Column('billing_country', sa.String(length=2), nullable=True))
    
    # Set default value for existing records
    op.execute(text("UPDATE invoices SET billing_country = 'GB' WHERE billing_country IS NULL"))
    
    # Then make it not nullable
    op.alter_column('invoices', 'billing_country',
                    existing_type=sa.String(length=2),
                    nullable=False)
    
    # Update credit_note_applications
    op.alter_column('credit_note_applications', 'credit_note_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('credit_note_applications', 'invoice_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    
    # Update credit_notes
    op.alter_column('credit_notes', 'user_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('credit_notes', 'reason',
                    existing_type=sa.TEXT(),
                    type_=sa.String(length=255),
                    existing_nullable=False)
    op.alter_column('credit_notes', 'status',
                    existing_type=sa.VARCHAR(length=32),
                    type_=sa.String(length=20),
                    existing_nullable=True)


def downgrade():
    # Remove billing_country column
    op.drop_column('invoices', 'billing_country')
    
    # Revert credit_note_applications changes
    op.alter_column('credit_note_applications', 'credit_note_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('credit_note_applications', 'invoice_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    
    # Revert credit_notes changes
    op.alter_column('credit_notes', 'user_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('credit_notes', 'reason',
                    existing_type=sa.String(length=255),
                    type_=sa.TEXT(),
                    existing_nullable=False)
    op.alter_column('credit_notes', 'status',
                    existing_type=sa.String(length=20),
                    type_=sa.VARCHAR(length=32),
                    existing_nullable=True)
