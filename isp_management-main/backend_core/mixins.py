"""
SQLAlchemy model mixins for common functionality.

This module provides reusable mixins that can be applied to SQLAlchemy models
to add common functionality such as timestamps, soft deletion, and auditing.
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns to a model.
    
    These timestamps are automatically set when the model is created or updated.
    """
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """
    Mixin that adds soft deletion capability to a model.
    
    Instead of actually deleting records from the database, this sets a
    deleted flag and deleted_at timestamp.
    """
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    def soft_delete(self):
        """Mark the record as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()


class AuditMixin:
    """
    Mixin that adds audit fields to track who created and last modified a record.
    
    These fields need to be populated by the application when creating or updating records.
    """
    
    created_by_id = Column(Integer, nullable=True)
    updated_by_id = Column(Integer, nullable=True)
    
    @declared_attr
    def created_by(cls):
        """Relationship to the user who created this record."""
        return relationship("User", foreign_keys=[cls.created_by_id])
    
    @declared_attr
    def updated_by(cls):
        """Relationship to the user who last updated this record."""
        return relationship("User", foreign_keys=[cls.updated_by_id])


class VersionMixin:
    """
    Mixin that adds versioning capability to a model.
    
    This keeps track of the version number of a record, which is incremented
    on each update.
    """
    
    version = Column(Integer, default=1, nullable=False)
    
    def increment_version(self):
        """Increment the version number of this record."""
        self.version += 1
