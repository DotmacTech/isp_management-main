"""
Storage service for the File Manager module.

This module provides services for storing and retrieving files from different
storage backends, including local filesystem and S3-compatible storage.
"""

import os
import shutil
import hashlib
import logging
import mimetypes
from typing import Optional, BinaryIO, Tuple, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException, status

from backend_core.config import settings
from ..models.file import StorageBackend, FileStatus

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for handling file storage operations.
    
    This service provides methods for storing, retrieving, and managing files
    across different storage backends.
    """
    
    def __init__(self):
        """Initialize the storage service."""
        # Set up local storage
        self.local_storage_path = settings.FILE_STORAGE_PATH
        os.makedirs(self.local_storage_path, exist_ok=True)
        
        # Set up S3 storage if configured
        self.s3_client = None
        self.s3_bucket = settings.S3_BUCKET_NAME if hasattr(settings, 'S3_BUCKET_NAME') else None
        
        if hasattr(settings, 'S3_ENDPOINT_URL') and settings.S3_ENDPOINT_URL:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION
            )
    
    async def store_file(
        self, 
        file: UploadFile, 
        storage_backend: StorageBackend,
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> Tuple[str, int, str, str]:
        """
        Store a file in the specified storage backend.
        
        Args:
            file: The file to store
            storage_backend: The storage backend to use
            module: Optional module identifier
            entity_type: Optional entity type
            entity_id: Optional entity ID
            
        Returns:
            Tuple containing (storage_path, file_size, checksum, mime_type)
        """
        if storage_backend == StorageBackend.LOCAL:
            return await self._store_file_local(file, module, entity_type, entity_id)
        elif storage_backend == StorageBackend.S3:
            return await self._store_file_s3(file, module, entity_type, entity_id)
        elif storage_backend == StorageBackend.DATABASE:
            raise NotImplementedError("Database storage is not yet implemented")
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
    
    async def _store_file_local(
        self, 
        file: UploadFile, 
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> Tuple[str, int, str, str]:
        """
        Store a file in the local filesystem.
        
        Args:
            file: The file to store
            module: Optional module identifier
            entity_type: Optional entity type
            entity_id: Optional entity ID
            
        Returns:
            Tuple containing (storage_path, file_size, checksum, mime_type)
        """
        # Generate a unique filename to avoid collisions
        file_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Create directory structure
        relative_path = self._get_relative_path(module, entity_type, entity_id)
        full_dir_path = os.path.join(self.local_storage_path, relative_path)
        os.makedirs(full_dir_path, exist_ok=True)
        
        # Full path for the file
        filename = f"{file_uuid}{file_extension}"
        full_file_path = os.path.join(full_dir_path, filename)
        relative_file_path = os.path.join(relative_path, filename)
        
        # Calculate checksum and size while saving
        sha256_hash = hashlib.sha256()
        file_size = 0
        
        # Save the file
        with open(full_file_path, "wb") as buffer:
            # Read in chunks to handle large files
            while content := await file.read(1024 * 1024):  # 1MB chunks
                sha256_hash.update(content)
                file_size += len(content)
                buffer.write(content)
        
        # Determine mime type
        mime_type = file.content_type
        if not mime_type or mime_type == "application/octet-stream":
            mime_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Reset file position for potential reuse
        await file.seek(0)
        
        return relative_file_path, file_size, sha256_hash.hexdigest(), mime_type
    
    async def _store_file_s3(
        self, 
        file: UploadFile, 
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> Tuple[str, int, str, str]:
        """
        Store a file in S3-compatible storage.
        
        Args:
            file: The file to store
            module: Optional module identifier
            entity_type: Optional entity type
            entity_id: Optional entity ID
            
        Returns:
            Tuple containing (storage_path, file_size, checksum, mime_type)
        """
        if not self.s3_client or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 storage is not properly configured"
            )
        
        # Generate a unique key to avoid collisions
        file_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Create S3 key
        relative_path = self._get_relative_path(module, entity_type, entity_id)
        s3_key = f"{relative_path}/{file_uuid}{file_extension}"
        
        # Calculate checksum and size while uploading
        sha256_hash = hashlib.sha256()
        file_size = 0
        file_content = await file.read()
        
        # Update hash and size
        sha256_hash.update(file_content)
        file_size = len(file_content)
        
        # Determine mime type
        mime_type = file.content_type
        if not mime_type or mime_type == "application/octet-stream":
            mime_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=mime_type
            )
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )
        
        # Reset file position for potential reuse
        await file.seek(0)
        
        return s3_key, file_size, sha256_hash.hexdigest(), mime_type
    
    def _get_relative_path(
        self, 
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> str:
        """
        Generate a relative path for storing a file.
        
        Args:
            module: Optional module identifier
            entity_type: Optional entity type
            entity_id: Optional entity ID
            
        Returns:
            Relative path for storing the file
        """
        # Get current date for organizing files
        today = datetime.now()
        date_path = f"{today.year}/{today.month:02d}/{today.day:02d}"
        
        # Build path based on provided parameters
        path_parts = []
        
        if module:
            path_parts.append(module)
        
        if entity_type:
            path_parts.append(entity_type)
            
            if entity_id:
                path_parts.append(str(entity_id))
        
        # Add date path
        path_parts.append(date_path)
        
        return os.path.join(*path_parts)
    
    async def retrieve_file(self, storage_backend: StorageBackend, storage_path: str) -> BinaryIO:
        """
        Retrieve a file from storage.
        
        Args:
            storage_backend: The storage backend where the file is stored
            storage_path: The path to the file in storage
            
        Returns:
            File-like object containing the file data
        """
        if storage_backend == StorageBackend.LOCAL:
            return self._retrieve_file_local(storage_path)
        elif storage_backend == StorageBackend.S3:
            return await self._retrieve_file_s3(storage_path)
        elif storage_backend == StorageBackend.DATABASE:
            raise NotImplementedError("Database storage is not yet implemented")
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
    
    def _retrieve_file_local(self, storage_path: str) -> BinaryIO:
        """
        Retrieve a file from local storage.
        
        Args:
            storage_path: The path to the file in storage
            
        Returns:
            File-like object containing the file data
        """
        full_path = os.path.join(self.local_storage_path, storage_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return open(full_path, "rb")
    
    async def _retrieve_file_s3(self, storage_path: str) -> BinaryIO:
        """
        Retrieve a file from S3 storage.
        
        Args:
            storage_path: The path to the file in storage
            
        Returns:
            File-like object containing the file data
        """
        if not self.s3_client or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 storage is not properly configured"
            )
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=storage_path
            )
            return response['Body']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
            else:
                logger.error(f"Error retrieving file from S3: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to retrieve file from S3: {str(e)}"
                )
    
    async def delete_file(self, storage_backend: StorageBackend, storage_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_backend: The storage backend where the file is stored
            storage_path: The path to the file in storage
            
        Returns:
            True if the file was deleted successfully, False otherwise
        """
        if storage_backend == StorageBackend.LOCAL:
            return self._delete_file_local(storage_path)
        elif storage_backend == StorageBackend.S3:
            return await self._delete_file_s3(storage_path)
        elif storage_backend == StorageBackend.DATABASE:
            raise NotImplementedError("Database storage is not yet implemented")
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
    
    def _delete_file_local(self, storage_path: str) -> bool:
        """
        Delete a file from local storage.
        
        Args:
            storage_path: The path to the file in storage
            
        Returns:
            True if the file was deleted successfully, False otherwise
        """
        full_path = os.path.join(self.local_storage_path, storage_path)
        
        if not os.path.exists(full_path):
            return False
        
        try:
            os.remove(full_path)
            return True
        except OSError as e:
            logger.error(f"Error deleting file from local storage: {e}")
            return False
    
    async def _delete_file_s3(self, storage_path: str) -> bool:
        """
        Delete a file from S3 storage.
        
        Args:
            storage_path: The path to the file in storage
            
        Returns:
            True if the file was deleted successfully, False otherwise
        """
        if not self.s3_client or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 storage is not properly configured"
            )
        
        try:
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=storage_path
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def get_download_url(self, storage_backend: StorageBackend, storage_path: str, filename: str) -> str:
        """
        Get a URL for downloading a file.
        
        Args:
            storage_backend: The storage backend where the file is stored
            storage_path: The path to the file in storage
            filename: The original filename
            
        Returns:
            URL for downloading the file
        """
        if storage_backend == StorageBackend.LOCAL:
            # For local files, we'll use the API endpoint
            return f"/api/files/download?path={storage_path}&filename={filename}"
        elif storage_backend == StorageBackend.S3:
            # Generate a pre-signed URL for S3 files
            if not self.s3_client or not self.s3_bucket:
                return ""
            
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.s3_bucket,
                        'Key': storage_path,
                        'ResponseContentDisposition': f'attachment; filename="{filename}"'
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
                return url
            except ClientError as e:
                logger.error(f"Error generating pre-signed URL: {e}")
                return ""
        else:
            return ""
    
    async def copy_file(
        self, 
        source_backend: StorageBackend, 
        source_path: str,
        target_backend: StorageBackend,
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> Tuple[str, int, str]:
        """
        Copy a file from one storage backend to another.
        
        Args:
            source_backend: The source storage backend
            source_path: The path to the file in the source storage
            target_backend: The target storage backend
            module: Optional module identifier for the target location
            entity_type: Optional entity type for the target location
            entity_id: Optional entity ID for the target location
            
        Returns:
            Tuple containing (target_path, file_size, checksum)
        """
        # Get the source file
        source_file = await self.retrieve_file(source_backend, source_path)
        
        # Determine the file extension and mime type
        file_extension = os.path.splitext(source_path)[1].lower()
        mime_type = mimetypes.guess_type(source_path)[0] or "application/octet-stream"
        
        # Generate a unique filename for the target
        file_uuid = str(uuid.uuid4())
        
        # Create target path
        relative_path = self._get_relative_path(module, entity_type, entity_id)
        
        if target_backend == StorageBackend.LOCAL:
            # Create directory structure
            full_dir_path = os.path.join(self.local_storage_path, relative_path)
            os.makedirs(full_dir_path, exist_ok=True)
            
            # Full path for the file
            filename = f"{file_uuid}{file_extension}"
            full_file_path = os.path.join(full_dir_path, filename)
            target_path = os.path.join(relative_path, filename)
            
            # Calculate checksum and size while saving
            sha256_hash = hashlib.sha256()
            file_size = 0
            
            # Save the file
            with open(full_file_path, "wb") as buffer:
                # Read in chunks to handle large files
                while content := source_file.read(1024 * 1024):  # 1MB chunks
                    sha256_hash.update(content)
                    file_size += len(content)
                    buffer.write(content)
            
            return target_path, file_size, sha256_hash.hexdigest()
            
        elif target_backend == StorageBackend.S3:
            if not self.s3_client or not self.s3_bucket:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="S3 storage is not properly configured"
                )
            
            # Create S3 key
            target_path = f"{relative_path}/{file_uuid}{file_extension}"
            
            # Read the entire file
            file_content = source_file.read()
            
            # Calculate checksum and size
            sha256_hash = hashlib.sha256(file_content)
            file_size = len(file_content)
            
            # Upload to S3
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=target_path,
                    Body=file_content,
                    ContentType=mime_type
                )
            except ClientError as e:
                logger.error(f"Error uploading file to S3: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to S3: {str(e)}"
                )
            
            return target_path, file_size, sha256_hash.hexdigest()
            
        else:
            raise ValueError(f"Unsupported target storage backend: {target_backend}")
    
    def get_preferred_storage_backend(self) -> StorageBackend:
        """
        Get the preferred storage backend based on configuration.
        
        Returns:
            The preferred storage backend
        """
        # Use S3 if properly configured
        if self.s3_client and self.s3_bucket:
            return StorageBackend.S3
        
        # Fall back to local storage
        return StorageBackend.LOCAL
