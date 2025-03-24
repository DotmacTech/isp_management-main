"""
API endpoints for the File Manager module.

This module provides API endpoints for managing files and folders,
including uploading, downloading, and sharing files.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend_core.dependencies import get_db, get_current_user
from backend_core.models.user import User
from ..services.file_service import FileService
from ..schemas.file import (
    FileCreate, FileUpdate, FileResponse, FileVersionCreate, FilePermissionCreate,
    FilePermissionResponse, FileShareCreate, FileShareResponse, FolderCreate,
    FolderUpdate, FolderResponse, FileSearchParams
)
from ..models.file import FileType, StorageBackend, FileStatus

router = APIRouter()


@router.post("/files/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file_type: FileType = Form(...),
    module: Optional[str] = Form(None),
    entity_type: Optional[str] = Form(None),
    entity_id: Optional[int] = Form(None),
    folder_id: Optional[int] = Form(None),
    tags: Optional[List[str]] = Form(None),
    is_encrypted: bool = Form(False),
    storage_backend: Optional[StorageBackend] = Form(None),
    metadata: Optional[dict] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new file.
    """
    file_data = FileCreate(
        original_filename=file.filename,
        title=title,
        description=description,
        file_type=file_type,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        folder_id=folder_id,
        tags=tags or [],
        is_encrypted=is_encrypted,
        metadata=metadata or {}
    )
    
    file_service = FileService(db)
    return await file_service.create_file(
        file=file,
        file_data=file_data,
        user_id=current_user.id,
        storage_backend=storage_backend
    )


@router.get("/files/{file_id}", response_model=FileResponse)
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a file by ID.
    """
    file_service = FileService(db)
    return file_service.get_file(file_id=file_id, user_id=current_user.id)


@router.get("/files/by-uuid/{file_uuid}", response_model=FileResponse)
def get_file_by_uuid(
    file_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a file by UUID.
    """
    file_service = FileService(db)
    return file_service.get_file_by_uuid(file_uuid=file_uuid, user_id=current_user.id)


@router.get("/files/", response_model=List[FileResponse])
def list_files(
    skip: int = 0,
    limit: int = 100,
    filename: Optional[str] = None,
    file_type: Optional[FileType] = None,
    module: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    status: Optional[FileStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List files with optional filtering.
    """
    search_params = FileSearchParams(
        filename=filename,
        file_type=file_type,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        folder_id=folder_id,
        owner_id=owner_id,
        tags=tags,
        status=status
    )
    
    file_service = FileService(db)
    return file_service.list_files(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        search_params=search_params
    )


@router.put("/files/{file_id}", response_model=FileResponse)
def update_file(
    file_id: int,
    file_data: FileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a file's metadata.
    """
    file_service = FileService(db)
    return file_service.update_file(
        file_id=file_id,
        file_data=file_data,
        user_id=current_user.id
    )


@router.put("/files/{file_id}/content", response_model=FileResponse)
async def update_file_content(
    file_id: int,
    file: UploadFile = File(...),
    change_summary: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a file's content, creating a new version.
    """
    version_data = FileVersionCreate(
        change_summary=change_summary
    )
    
    file_service = FileService(db)
    return await file_service.update_file_content(
        file_id=file_id,
        file=file,
        version_data=version_data,
        user_id=current_user.id
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a file.
    """
    file_service = FileService(db)
    
    # Use background task for file deletion to avoid blocking the response
    background_tasks.add_task(
        file_service.delete_file,
        file_id=file_id,
        user_id=current_user.id
    )
    
    return {"message": "File deletion initiated"}


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a file.
    """
    file_service = FileService(db)
    file_data, filename, mime_type = await file_service.download_file(
        file_id=file_id,
        user_id=current_user.id
    )
    
    return StreamingResponse(
        file_data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Folder endpoints

@router.post("/folders/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new folder.
    """
    file_service = FileService(db)
    return file_service.create_folder(
        folder_data=folder_data,
        user_id=current_user.id
    )


@router.get("/folders/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a folder by ID.
    """
    file_service = FileService(db)
    return file_service.get_folder(
        folder_id=folder_id,
        user_id=current_user.id
    )


@router.get("/folders/", response_model=List[FolderResponse])
def list_folders(
    parent_id: Optional[int] = None,
    module: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List folders with optional filtering.
    """
    file_service = FileService(db)
    return file_service.list_folders(
        user_id=current_user.id,
        parent_id=parent_id,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit
    )


@router.put("/folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: int,
    folder_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a folder.
    """
    file_service = FileService(db)
    return file_service.update_folder(
        folder_id=folder_id,
        folder_data=folder_data,
        user_id=current_user.id
    )


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    recursive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a folder.
    """
    file_service = FileService(db)
    file_service.delete_folder(
        folder_id=folder_id,
        user_id=current_user.id,
        recursive=recursive
    )
    
    return {"message": "Folder deleted successfully"}


# Permission endpoints

@router.post("/files/{file_id}/permissions", response_model=FilePermissionResponse)
def set_file_permission(
    file_id: int,
    permission_data: FilePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Set permissions for a file.
    """
    file_service = FileService(db)
    return file_service.set_file_permission(
        file_id=file_id,
        permission_data=permission_data,
        user_id=current_user.id
    )


@router.delete("/files/{file_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file_permission(
    file_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove permissions for a file.
    """
    file_service = FileService(db)
    file_service.remove_file_permission(
        file_id=file_id,
        user_id_to_remove=user_id,
        requesting_user_id=current_user.id
    )
    
    return {"message": "Permission removed successfully"}


@router.get("/files/{file_id}/permissions", response_model=List[FilePermissionResponse])
def get_file_permissions(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all permissions for a file.
    """
    file_service = FileService(db)
    return file_service.get_file_permissions(
        file_id=file_id,
        user_id=current_user.id
    )


# Sharing endpoints

@router.post("/files/{file_id}/shares", response_model=FileShareResponse)
def create_file_share(
    file_id: int,
    share_data: FileShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a shareable link for a file.
    """
    file_service = FileService(db)
    return file_service.create_file_share(
        file_id=file_id,
        share_data=share_data,
        user_id=current_user.id
    )


@router.get("/shares/{share_id}", response_model=FileResponse)
def access_shared_file(
    share_id: str,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Access a file through a share link.
    """
    file_service = FileService(db)
    return file_service.access_shared_file(
        share_id=share_id,
        password=password
    )


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_file_share(
    share_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate a file share.
    """
    file_service = FileService(db)
    file_service.deactivate_file_share(
        share_id=share_id,
        user_id=current_user.id
    )
    
    return {"message": "Share deactivated successfully"}
