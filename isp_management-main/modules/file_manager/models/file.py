"""
File and document models for the File Manager module.

This module defines the database models for files, documents, and related entities
such as file versions, access permissions, and metadata.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from backend_core.database import Base
from backend_core.models import TimestampMixin


class FileType(str, enum.Enum):
    """Enumeration of file types."""
    DOCUMENT = "document"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    PDF = "pdf"
    ARCHIVE = "archive"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class StorageBackend(str, enum.Enum):
    """Enumeration of storage backends."""
    LOCAL = "local"
    S3 = "s3"
    DATABASE = "database"


class FileStatus(str, enum.Enum):
    """Enumeration of file statuses."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class File(Base, TimestampMixin):
    """
    Model for storing file metadata.
    
    This model stores metadata about files, including their location, type,
    and ownership information.
    """
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False, default=FileType.OTHER)
    mime_type = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=True)  # SHA-256 hash
    
    # Storage information
    storage_backend = Column(Enum(StorageBackend), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    
    # Metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)  # Flexible metadata storage
    tags = Column(JSONB, nullable=True)  # Array of tags
    
    # Status
    status = Column(Enum(FileStatus), nullable=False, default=FileStatus.ACTIVE)
    is_encrypted = Column(Boolean, default=False)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="files")
    
    # Module association (which module this file belongs to)
    module = Column(String(50), nullable=True)
    entity_type = Column(String(50), nullable=True)  # e.g., "ticket", "invoice", "customer"
    entity_id = Column(Integer, nullable=True)  # ID of the associated entity
    
    # Relationships
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    permissions = relationship("FilePermission", back_populates="file", cascade="all, delete-orphan")
    access_logs = relationship("FileAccessLog", back_populates="file", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('storage_backend', 'storage_path', name='uix_storage_location'),
    )
    
    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


class FileVersion(Base, TimestampMixin):
    """
    Model for storing file versions.
    
    This model tracks different versions of a file, allowing for version control
    and history tracking.
    """
    __tablename__ = "file_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    
    # Version information
    version_number = Column(Integer, nullable=False)
    storage_path = Column(String(1024), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=True)  # SHA-256 hash
    
    # Change information
    change_summary = Column(Text, nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    file = relationship("File", back_populates="versions")
    changed_by = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('file_id', 'version_number', name='uix_file_version'),
    )
    
    def __repr__(self):
        return f"<FileVersion(id={self.id}, file_id={self.file_id}, version={self.version_number})>"


class FilePermission(Base, TimestampMixin):
    """
    Model for storing file access permissions.
    
    This model defines who can access a file and what operations they can perform.
    """
    __tablename__ = "file_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    
    # Permission target
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    
    # Permission levels
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    
    # Relationships
    file = relationship("File", back_populates="permissions")
    user = relationship("User", foreign_keys=[user_id])
    group = relationship("Group", foreign_keys=[group_id])
    
    __table_args__ = (
        UniqueConstraint('file_id', 'user_id', name='uix_file_user_permission'),
        UniqueConstraint('file_id', 'group_id', name='uix_file_group_permission'),
    )
    
    def __repr__(self):
        target = f"user_id={self.user_id}" if self.user_id else f"group_id={self.group_id}"
        return f"<FilePermission(id={self.id}, file_id={self.file_id}, {target})>"


class FileAccessLog(Base):
    """
    Model for logging file access events.
    
    This model tracks when files are accessed, by whom, and what operations
    were performed.
    """
    __tablename__ = "file_access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    
    # Access information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    operation = Column(String(50), nullable=False)  # e.g., "read", "write", "delete"
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    details = Column(Text, nullable=True)
    
    # Relationships
    file = relationship("File", back_populates="access_logs")
    user = relationship("User")
    
    def __repr__(self):
        return f"<FileAccessLog(id={self.id}, file_id={self.file_id}, user_id={self.user_id}, operation='{self.operation}')>"


class FileShare(Base, TimestampMixin):
    """
    Model for tracking file shares.
    
    This model allows for sharing files with external users via links or email.
    """
    __tablename__ = "file_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    
    # Share information
    share_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Share settings
    expires_at = Column(DateTime, nullable=True)
    password_protected = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)
    max_downloads = Column(Integer, nullable=True)
    download_count = Column(Integer, default=0)
    
    # Relationships
    file = relationship("File")
    created_by = relationship("User")
    
    def __repr__(self):
        return f"<FileShare(id={self.id}, file_id={self.file_id}, token='{self.share_token}')>"


class Folder(Base, TimestampMixin):
    """
    Model for organizing files into folders.
    
    This model allows for hierarchical organization of files.
    """
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    parent = relationship("Folder", remote_side=[id], backref="children")
    owner = relationship("User")
    
    # Files in this folder (many-to-many relationship)
    files = relationship(
        "File",
        secondary="folder_files",
        backref="folders"
    )
    
    __table_args__ = (
        UniqueConstraint('parent_id', 'name', 'owner_id', name='uix_folder_name_parent_owner'),
    )
    
    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"


# Association table for folder-file relationship
folder_files = Base.metadata.tables.get('folder_files') or Table(
    'folder_files',
    Base.metadata,
    Column('folder_id', Integer, ForeignKey('folders.id'), primary_key=True),
    Column('file_id', Integer, ForeignKey('files.id'), primary_key=True)
)
