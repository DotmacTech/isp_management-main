"""
Pydantic schemas for the File Manager module.

This module defines the Pydantic schemas for file-related operations,
including file creation, updates, and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union, ClassVar
from pydantic import BaseModel, Field, field_validator, model_validator, AnyHttpUrl, constr, ConfigDict
import uuid

from ..models.file import FileType, StorageBackend, FileStatus


class FileBase(BaseModel):
    """Base schema for file data."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class FileCreate(FileBase):
    """Schema for file creation."""
    original_filename: str
    file_type: FileType = FileType.OTHER
    mime_type: str
    module: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    is_encrypted: bool = False
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original_filename": "invoice_2023.pdf",
                "title": "Invoice for January 2023",
                "description": "Monthly invoice for customer XYZ",
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "tags": ["invoice", "billing", "2023"],
                "metadata": {"customer_id": 123, "invoice_number": "INV-2023-001"},
                "module": "billing",
                "entity_type": "invoice",
                "entity_id": 456,
                "is_encrypted": False
            }
        }
    )


class FileUpdate(FileBase):
    """Schema for file updates."""
    status: Optional[FileStatus] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Invoice for January 2023",
                "description": "Updated monthly invoice for customer XYZ",
                "tags": ["invoice", "billing", "2023", "updated"],
                "metadata": {"customer_id": 123, "invoice_number": "INV-2023-001-REV"},
                "status": "archived"
            }
        }
    )


class FileVersionCreate(BaseModel):
    """Schema for creating a new file version."""
    change_summary: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "change_summary": "Updated pricing information"
            }
        }
    )


class FileVersionResponse(BaseModel):
    """Schema for file version response."""
    id: int
    file_id: int
    version_number: int
    size_bytes: int
    checksum: Optional[str]
    change_summary: Optional[str]
    changed_by_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FilePermissionBase(BaseModel):
    """Base schema for file permissions."""
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False


class FilePermissionCreate(FilePermissionBase):
    """Schema for creating file permissions."""
    user_id: Optional[int] = None
    group_id: Optional[int] = None
    
    @model_validator(mode='after')
    def validate_permission_target(self) -> 'FilePermissionCreate':
        """Validate that either user_id or group_id is provided, but not both."""
        user_id = self.user_id
        group_id = self.group_id
        
        if user_id is None and group_id is None:
            raise ValueError('Either user_id or group_id must be provided')
        
        if user_id is not None and group_id is not None:
            raise ValueError('Only one of user_id or group_id can be provided')
            
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 123,
                "can_read": True,
                "can_write": True,
                "can_delete": False
            }
        }
    )


class FilePermissionResponse(FilePermissionBase):
    """Schema for file permission response."""
    id: int
    file_id: int
    user_id: Optional[int]
    group_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FileShareBase(BaseModel):
    """Base schema for file shares."""
    expires_at: Optional[datetime] = None
    password_protected: bool = False
    password: Optional[str] = None
    max_downloads: Optional[int] = None


class FileShareCreate(FileShareBase):
    """Schema for creating a file share."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expires_at": "2023-12-31T23:59:59",
                "password_protected": True,
                "password": "securepassword",
                "max_downloads": 5
            }
        }
    )


class FileShareResponse(BaseModel):
    """Schema for file share response."""
    id: int
    file_id: int
    share_token: uuid.UUID
    created_by_id: int
    expires_at: Optional[datetime]
    password_protected: bool
    max_downloads: Optional[int]
    download_count: int
    created_at: datetime
    updated_at: datetime
    share_url: str
    
    model_config = ConfigDict(from_attributes=True)


class FileResponse(FileBase):
    """Schema for file response."""
    id: int
    uuid: uuid.UUID
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    size_bytes: int
    checksum: Optional[str]
    storage_backend: StorageBackend
    status: FileStatus
    is_encrypted: bool
    owner_id: int
    module: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    download_url: str
    
    model_config = ConfigDict(from_attributes=True)


class FileDetailResponse(FileResponse):
    """Schema for detailed file response."""
    versions: List[FileVersionResponse] = []
    permissions: List[FilePermissionResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class FolderBase(BaseModel):
    """Base schema for folders."""
    name: str
    parent_id: Optional[int] = None


class FolderCreate(FolderBase):
    """Schema for folder creation."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Invoices",
                "parent_id": 1
            }
        }
    )


class FolderUpdate(BaseModel):
    """Schema for folder updates."""
    name: Optional[str] = None
    parent_id: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "2023 Invoices"
            }
        }
    )


class FolderResponse(FolderBase):
    """Schema for folder response."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FolderDetailResponse(FolderResponse):
    """Schema for detailed folder response."""
    files: List[FileResponse] = []
    children: List['FolderResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)


class FileSearchParams(BaseModel):
    """Schema for file search parameters."""
    filename: Optional[str] = None
    file_type: Optional[FileType] = None
    module: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    owner_id: Optional[int] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    status: Optional[FileStatus] = FileStatus.ACTIVE
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "invoice",
                "file_type": "pdf",
                "module": "billing",
                "tags": ["invoice", "2023"],
                "created_after": "2023-01-01T00:00:00",
                "status": "active"
            }
        }
    )


# Add self-reference for nested folders
FolderDetailResponse.update_forward_refs()
