"""
File service for the File Manager module.

This module provides services for managing files, including creation, retrieval,
updates, and deletion, as well as handling file permissions and versions.
"""

import os
import logging
from typing import List, Optional, Dict, Any, BinaryIO, Tuple
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from backend_core.config import settings
from ..models.file import (
    File, FileVersion, FilePermission, FileAccessLog, FileShare, Folder,
    FileType, StorageBackend, FileStatus
)
from ..schemas.file import (
    FileCreate, FileUpdate, FileVersionCreate, FilePermissionCreate,
    FileShareCreate, FolderCreate, FolderUpdate, FileSearchParams
)
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class FileService:
    """
    Service for managing files and related operations.
    
    This service provides methods for creating, retrieving, updating, and deleting
    files, as well as managing file permissions, versions, and other related entities.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the file service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.storage_service = StorageService()
    
    async def create_file(
        self, 
        file: UploadFile, 
        file_data: FileCreate,
        user_id: int,
        storage_backend: Optional[StorageBackend] = None
    ) -> File:
        """
        Create a new file.
        
        Args:
            file: The file to upload
            file_data: Metadata for the file
            user_id: ID of the user creating the file
            storage_backend: Optional storage backend to use
            
        Returns:
            The created file object
        """
        # Determine storage backend if not specified
        if storage_backend is None:
            storage_backend = self.storage_service.get_preferred_storage_backend()
        
        # Store the file
        storage_path, size_bytes, checksum, mime_type = await self.storage_service.store_file(
            file=file,
            storage_backend=storage_backend,
            module=file_data.module,
            entity_type=file_data.entity_type,
            entity_id=file_data.entity_id
        )
        
        # Create the file record
        db_file = File(
            filename=os.path.basename(storage_path),
            original_filename=file_data.original_filename,
            file_type=file_data.file_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
            storage_backend=storage_backend,
            storage_path=storage_path,
            title=file_data.title,
            description=file_data.description,
            metadata=file_data.metadata,
            tags=file_data.tags,
            status=FileStatus.ACTIVE,
            is_encrypted=file_data.is_encrypted,
            owner_id=user_id,
            module=file_data.module,
            entity_type=file_data.entity_type,
            entity_id=file_data.entity_id
        )
        
        self.db.add(db_file)
        self.db.flush()
        
        # Create initial version
        db_version = FileVersion(
            file_id=db_file.id,
            version_number=1,
            storage_path=storage_path,
            size_bytes=size_bytes,
            checksum=checksum,
            change_summary="Initial version",
            changed_by_id=user_id
        )
        
        self.db.add(db_version)
        
        # Create default permission for owner
        db_permission = FilePermission(
            file_id=db_file.id,
            user_id=user_id,
            can_read=True,
            can_write=True,
            can_delete=True
        )
        
        self.db.add(db_permission)
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="create",
            success=True
        )
        
        self.db.commit()
        self.db.refresh(db_file)
        
        return db_file
    
    def get_file(self, file_id: int, user_id: int) -> File:
        """
        Get a file by ID.
        
        Args:
            file_id: ID of the file to retrieve
            user_id: ID of the user requesting the file
            
        Returns:
            The file object
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file"
            )
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="read",
            success=True
        )
        
        return db_file
    
    def get_file_by_uuid(self, file_uuid: str, user_id: int) -> File:
        """
        Get a file by UUID.
        
        Args:
            file_uuid: UUID of the file to retrieve
            user_id: ID of the user requesting the file
            
        Returns:
            The file object
        """
        # Get the file
        db_file = self.db.query(File).filter(File.uuid == file_uuid).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file"
            )
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="read",
            success=True
        )
        
        return db_file
    
    def list_files(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search_params: Optional[FileSearchParams] = None
    ) -> List[File]:
        """
        List files with optional filtering.
        
        Args:
            user_id: ID of the user requesting the files
            skip: Number of records to skip
            limit: Maximum number of records to return
            search_params: Optional search parameters
            
        Returns:
            List of file objects
        """
        # Start with a base query for files
        query = self.db.query(File)
        
        # Filter by files the user has permission to read
        # This includes files owned by the user and files with explicit permissions
        query = query.filter(
            or_(
                File.owner_id == user_id,
                File.id.in_(
                    self.db.query(FilePermission.file_id)
                    .filter(
                        and_(
                            FilePermission.user_id == user_id,
                            FilePermission.can_read == True
                        )
                    )
                )
            )
        )
        
        # Apply search filters if provided
        if search_params:
            if search_params.filename:
                query = query.filter(File.filename.ilike(f"%{search_params.filename}%"))
            
            if search_params.file_type:
                query = query.filter(File.file_type == search_params.file_type)
            
            if search_params.module:
                query = query.filter(File.module == search_params.module)
            
            if search_params.entity_type:
                query = query.filter(File.entity_type == search_params.entity_type)
            
            if search_params.entity_id:
                query = query.filter(File.entity_id == search_params.entity_id)
            
            if search_params.owner_id:
                query = query.filter(File.owner_id == search_params.owner_id)
            
            if search_params.tags:
                for tag in search_params.tags:
                    query = query.filter(File.tags.contains([tag]))
            
            if search_params.created_after:
                query = query.filter(File.created_at >= search_params.created_after)
            
            if search_params.created_before:
                query = query.filter(File.created_at <= search_params.created_before)
            
            if search_params.status:
                query = query.filter(File.status == search_params.status)
        
        # Apply pagination
        files = query.order_by(desc(File.created_at)).offset(skip).limit(limit).all()
        
        # Log access for each file
        for file in files:
            self._log_file_access(
                file_id=file.id,
                user_id=user_id,
                operation="list",
                success=True
            )
        
        return files
        
    def update_file(self, file_id: int, file_data: FileUpdate, user_id: int) -> File:
        """
        Update a file's metadata.
        
        Args:
            file_id: ID of the file to update
            file_data: New metadata for the file
            user_id: ID of the user updating the file
            
        Returns:
            The updated file object
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this file"
            )
        
        # Update fields
        if file_data.title is not None:
            db_file.title = file_data.title
        
        if file_data.description is not None:
            db_file.description = file_data.description
        
        if file_data.tags is not None:
            db_file.tags = file_data.tags
        
        if file_data.metadata is not None:
            db_file.metadata = file_data.metadata
        
        if file_data.status is not None:
            db_file.status = file_data.status
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="update",
            success=True
        )
        
        self.db.commit()
        self.db.refresh(db_file)
        
        return db_file
    
    async def update_file_content(
        self, 
        file_id: int, 
        file: UploadFile, 
        version_data: FileVersionCreate,
        user_id: int
    ) -> File:
        """
        Update a file's content, creating a new version.
        
        Args:
            file_id: ID of the file to update
            file: The new file content
            version_data: Metadata for the new version
            user_id: ID of the user updating the file
            
        Returns:
            The updated file object
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this file"
            )
        
        # Get the latest version number
        latest_version = self.db.query(FileVersion)\
            .filter(FileVersion.file_id == db_file.id)\
            .order_by(desc(FileVersion.version_number))\
            .first()
        
        new_version_number = latest_version.version_number + 1 if latest_version else 1
        
        # Store the new file
        storage_path, size_bytes, checksum, mime_type = await self.storage_service.store_file(
            file=file,
            storage_backend=db_file.storage_backend,
            module=db_file.module,
            entity_type=db_file.entity_type,
            entity_id=db_file.entity_id
        )
        
        # Create new version
        db_version = FileVersion(
            file_id=db_file.id,
            version_number=new_version_number,
            storage_path=storage_path,
            size_bytes=size_bytes,
            checksum=checksum,
            change_summary=version_data.change_summary,
            changed_by_id=user_id
        )
        
        self.db.add(db_version)
        
        # Update file metadata
        db_file.size_bytes = size_bytes
        db_file.checksum = checksum
        db_file.storage_path = storage_path
        db_file.updated_at = datetime.utcnow()
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="update_content",
            success=True
        )
        
        self.db.commit()
        self.db.refresh(db_file)
        
        return db_file
    
    async def delete_file(self, file_id: int, user_id: int) -> bool:
        """
        Delete a file.
        
        Args:
            file_id: ID of the file to delete
            user_id: ID of the user deleting the file
            
        Returns:
            True if the file was deleted successfully
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "delete"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this file"
            )
        
        # Delete the file from storage
        success = await self.storage_service.delete_file(
            storage_backend=db_file.storage_backend,
            storage_path=db_file.storage_path
        )
        
        if not success:
            logger.warning(f"Failed to delete file {db_file.id} from storage")
        
        # Delete all versions from storage
        for version in db_file.versions:
            if version.storage_path != db_file.storage_path:
                await self.storage_service.delete_file(
                    storage_backend=db_file.storage_backend,
                    storage_path=version.storage_path
                )
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="delete",
            success=True
        )
        
        # Delete the file record
        self.db.delete(db_file)
        self.db.commit()
        
        return True
    
    async def download_file(self, file_id: int, user_id: int) -> Tuple[BinaryIO, str, str]:
        """
        Download a file.
        
        Args:
            file_id: ID of the file to download
            user_id: ID of the user downloading the file
            
        Returns:
            Tuple containing (file_data, filename, mime_type)
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check permissions
        if not self._check_file_permission(db_file.id, user_id, "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to download this file"
            )
        
        # Get the file data
        file_data = await self.storage_service.retrieve_file(
            storage_backend=db_file.storage_backend,
            storage_path=db_file.storage_path
        )
        
        # Log access
        self._log_file_access(
            file_id=db_file.id,
            user_id=user_id,
            operation="download",
            success=True
        )
        
        return file_data, db_file.original_filename, db_file.mime_type
    
    def _check_file_permission(self, file_id: int, user_id: int, permission_type: str) -> bool:
        """
        Check if a user has permission to perform an operation on a file.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            permission_type: Type of permission to check ("read", "write", "delete")
            
        Returns:
            True if the user has permission, False otherwise
        """
        # Get the file
        db_file = self.db.query(File).filter(File.id == file_id).first()
        
        if not db_file:
            return False
        
        # File owner has all permissions
        if db_file.owner_id == user_id:
            return True
        
        # Check explicit permissions
        permission = self.db.query(FilePermission)\
            .filter(FilePermission.file_id == file_id, FilePermission.user_id == user_id)\
            .first()
        
        if permission:
            if permission_type == "read" and permission.can_read:
                return True
            elif permission_type == "write" and permission.can_write:
                return True
            elif permission_type == "delete" and permission.can_delete:
                return True
        
        # Check group permissions
        # TODO: Implement group permission checks
        
        return False
    
    def _log_file_access(
        self, 
        file_id: int, 
        user_id: int, 
        operation: str, 
        success: bool,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log a file access event.
        
        Args:
            file_id: ID of the file
            user_id: ID of the user
            operation: Type of operation performed
            success: Whether the operation was successful
            details: Optional details about the operation
            ip_address: Optional IP address of the user
            user_agent: Optional user agent of the user
        """
        log_entry = FileAccessLog(
            file_id=file_id,
            user_id=user_id,
            operation=operation,
            success=success,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(log_entry)
        self.db.commit()
