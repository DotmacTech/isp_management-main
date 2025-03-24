"""Add user sessions and audit logs tables

Revision ID: 001
Revises: 
Create Date: 2023-11-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('access_token', sa.String(512), nullable=True),
        sa.Column('refresh_token', sa.String(512), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('device_info', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('last_active_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),
        sa.Column('termination_reason', sa.String(50), nullable=True),
        sa.Column('mfa_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('mfa_verified_at', sa.DateTime(), nullable=True),
        sa.Column('remember_device', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_id'), 'user_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_user_sessions_is_active'), 'user_sessions', ['is_active'], unique=False)

    # Create mfa_device_tokens table
    op.create_table(
        'mfa_device_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('device_info', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mfa_device_tokens_id'), 'mfa_device_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_mfa_device_tokens_user_id'), 'mfa_device_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_mfa_device_tokens_token'), 'mfa_device_tokens', ['token'], unique=True)

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, default='info'),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_username'), 'audit_logs', ['username'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)

    # Add new fields to users table for MFA and security
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('mfa_secret', sa.String(32), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login_ip', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('email_verification_token_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('password_reset_token_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    # Drop columns from users table
    op.drop_column('users', 'password_reset_token_expires_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_token_expires_at')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')

    # Drop audit_logs table and indexes
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_username'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    # Drop mfa_device_tokens table and indexes
    op.drop_index(op.f('ix_mfa_device_tokens_token'), table_name='mfa_device_tokens')
    op.drop_index(op.f('ix_mfa_device_tokens_user_id'), table_name='mfa_device_tokens')
    op.drop_index(op.f('ix_mfa_device_tokens_id'), table_name='mfa_device_tokens')
    op.drop_table('mfa_device_tokens')

    # Drop user_sessions table and indexes
    op.drop_index(op.f('ix_user_sessions_is_active'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_session_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
