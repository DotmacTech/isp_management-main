"""
AI Chatbot Integration Module database migration.

Revision ID: ai_chatbot_integration
Revises: 05ae82c589d1
Create Date: 2025-03-15 06:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ai_chatbot_integration'
<<<<<<< HEAD
down_revision = '05ae82c589d1'  # Changed to point to the initial schema migration
=======
down_revision = 'c8c4b27b3053'  # Adjust this to your actual previous migration
>>>>>>> 7e0a2fe (Saving local changes before pulling)
branch_labels = None
depends_on = None


def upgrade():
    # Create chatbot_queries table
    op.create_table(
        'chatbot_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('context_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('intent', sa.String(length=100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('entities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('ai_service_name', sa.String(length=50), nullable=True),
        sa.Column('ai_model_version', sa.String(length=50), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatbot_queries_id'), 'chatbot_queries', ['id'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_user_id'), 'chatbot_queries', ['user_id'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_tenant_id'), 'chatbot_queries', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_intent'), 'chatbot_queries', ['intent'], unique=False)
    op.create_index(op.f('ix_chatbot_queries_created_at'), 'chatbot_queries', ['created_at'], unique=False)

    # Create chatbot_feedback table
    op.create_table(
        'chatbot_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('is_helpful', sa.Boolean(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['query_id'], ['chatbot_queries.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatbot_feedback_id'), 'chatbot_feedback', ['id'], unique=False)
    op.create_index(op.f('ix_chatbot_feedback_query_id'), 'chatbot_feedback', ['query_id'], unique=False)
    op.create_index(op.f('ix_chatbot_feedback_user_id'), 'chatbot_feedback', ['user_id'], unique=False)
    op.create_index(op.f('ix_chatbot_feedback_rating'), 'chatbot_feedback', ['rating'], unique=False)

    # Create chatbot_actions table
    op.create_table(
        'chatbot_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('module_name', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['query_id'], ['chatbot_queries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatbot_actions_id'), 'chatbot_actions', ['id'], unique=False)
    op.create_index(op.f('ix_chatbot_actions_query_id'), 'chatbot_actions', ['query_id'], unique=False)
    op.create_index(op.f('ix_chatbot_actions_action_type'), 'chatbot_actions', ['action_type'], unique=False)
    op.create_index(op.f('ix_chatbot_actions_module_name'), 'chatbot_actions', ['module_name'], unique=False)

    # Create ai_service_configs table
    op.create_table(
        'ai_service_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('service_url', sa.String(length=255), nullable=False),
        sa.Column('api_key', sa.String(length=255), nullable=False),
        sa.Column('model_name', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('config_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_service_configs_id'), 'ai_service_configs', ['id'], unique=False)
    op.create_index(op.f('ix_ai_service_configs_tenant_id'), 'ai_service_configs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_ai_service_configs_service_name'), 'ai_service_configs', ['service_name'], unique=False)
    op.create_index(op.f('ix_ai_service_configs_is_active'), 'ai_service_configs', ['is_active'], unique=False)

    # Add relationships to User model
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS chatbot_queries_relationship_added BOOLEAN DEFAULT FALSE;
    """)
    
    # Add relationships to Tenant model
    op.execute("""
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS chatbot_queries_relationship_added BOOLEAN DEFAULT FALSE;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS ai_service_configs_relationship_added BOOLEAN DEFAULT FALSE;
    """)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('ai_service_configs')
    op.drop_table('chatbot_actions')
    op.drop_table('chatbot_feedback')
    op.drop_table('chatbot_queries')
    
    # Remove relationship columns
    op.execute("""
    ALTER TABLE users DROP COLUMN IF EXISTS chatbot_queries_relationship_added;
    """)
    
    op.execute("""
    ALTER TABLE tenants DROP COLUMN IF EXISTS chatbot_queries_relationship_added;
    ALTER TABLE tenants DROP COLUMN IF EXISTS ai_service_configs_relationship_added;
    """)
