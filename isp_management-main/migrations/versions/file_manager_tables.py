"""
Create File Manager module tables.

Revision ID: file_manager_tables
Revises: 
Create Date: 2023-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic
revision = 'file_manager_tables'
down_revision = None  # Update this to the previous migration ID when integrating
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    file_type_enum = postgresql.ENUM(
        'document', 'image', 'video', 'audio', 'archive', 'other',
        name='file_type_enum'
    )
    file_type_enum.create(op.get_bind())
    
    storage_backend_enum = postgresql.ENUM(
        'local', 's3',
        name='storage_backend_enum'
    )
    storage_backend_enum.create(op.get_bind())
    
    file_status_enum = postgresql.ENUM(
        'active', 'archived', 'deleted',
        name='file_status_enum'
    )
    file_status_enum.create(op.get_bind())
    
    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    
    # Create files table
    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.Enum('document', 'image', 'video', 'audio', 'archive', 'other', name='file_type_enum'), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('storage_backend', sa.Enum('local', 's3', name='storage_backend_enum'), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.Enum('active', 'archived', 'deleted', name='file_status_enum'), nullable=False),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('folder_id', sa.Integer(), nullable=True),
        sa.Column('module', sa.String(length=50), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    
    # Create file_versions table
    op.create_table(
        'file_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id', 'version_number', name='uix_file_version')
    )
    
    # Create file_permissions table
    op.create_table(
        'file_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('can_read', sa.Boolean(), nullable=False, default=True),
        sa.Column('can_write', sa.Boolean(), nullable=False, default=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id', 'user_id', name='uix_file_user_permission')
    )
    
    # Create file_access_logs table
    op.create_table(
        'file_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('elasticsearch_synced', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create file_shares table
    op.create_table(
        'file_shares',
        sa.Column('id', sa.String(length=36), nullable=False, default=lambda: str(uuid.uuid4())),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_access_count', sa.Integer(), nullable=True),
        sa.Column('password', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_files_owner_id'), 'files', ['owner_id'], unique=False)
    op.create_index(op.f('ix_files_folder_id'), 'files', ['folder_id'], unique=False)
    op.create_index(op.f('ix_files_module'), 'files', ['module'], unique=False)
    op.create_index(op.f('ix_files_entity_type'), 'files', ['entity_type'], unique=False)
    op.create_index(op.f('ix_files_entity_id'), 'files', ['entity_id'], unique=False)
    op.create_index(op.f('ix_files_status'), 'files', ['status'], unique=False)
    
    op.create_index(op.f('ix_folders_parent_id'), 'folders', ['parent_id'], unique=False)
    op.create_index(op.f('ix_folders_owner_id'), 'folders', ['owner_id'], unique=False)
    op.create_index(op.f('ix_folders_module'), 'folders', ['module'], unique=False)
    op.create_index(op.f('ix_folders_entity_type'), 'folders', ['entity_type'], unique=False)
    op.create_index(op.f('ix_folders_entity_id'), 'folders', ['entity_id'], unique=False)
    
    op.create_index(op.f('ix_file_versions_file_id'), 'file_versions', ['file_id'], unique=False)
    op.create_index(op.f('ix_file_permissions_file_id'), 'file_permissions', ['file_id'], unique=False)
    op.create_index(op.f('ix_file_permissions_user_id'), 'file_permissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_file_access_logs_file_id'), 'file_access_logs', ['file_id'], unique=False)
    op.create_index(op.f('ix_file_access_logs_user_id'), 'file_access_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_file_shares_file_id'), 'file_shares', ['file_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_file_shares_file_id'), table_name='file_shares')
    op.drop_index(op.f('ix_file_access_logs_user_id'), table_name='file_access_logs')
    op.drop_index(op.f('ix_file_access_logs_file_id'), table_name='file_access_logs')
    op.drop_index(op.f('ix_file_permissions_user_id'), table_name='file_permissions')
    op.drop_index(op.f('ix_file_permissions_file_id'), table_name='file_permissions')
    op.drop_index(op.f('ix_file_versions_file_id'), table_name='file_versions')
    
    op.drop_index(op.f('ix_folders_entity_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_entity_type'), table_name='folders')
    op.drop_index(op.f('ix_folders_module'), table_name='folders')
    op.drop_index(op.f('ix_folders_owner_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_parent_id'), table_name='folders')
    
    op.drop_index(op.f('ix_files_status'), table_name='files')
    op.drop_index(op.f('ix_files_entity_id'), table_name='files')
    op.drop_index(op.f('ix_files_entity_type'), table_name='files')
    op.drop_index(op.f('ix_files_module'), table_name='files')
    op.drop_index(op.f('ix_files_folder_id'), table_name='files')
    op.drop_index(op.f('ix_files_owner_id'), table_name='files')
    
    # Drop tables
    op.drop_table('file_shares')
    op.drop_table('file_access_logs')
    op.drop_table('file_permissions')
    op.drop_table('file_versions')
    op.drop_table('files')
    op.drop_table('folders')
    
    # Drop enum types
    op.execute('DROP TYPE file_status_enum')
    op.execute('DROP TYPE storage_backend_enum')
    op.execute('DROP TYPE file_type_enum')
