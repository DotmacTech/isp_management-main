"""
Celery tasks for the File Manager module.

This module provides Celery tasks for handling asynchronous file operations,
including background processing, cleanup, and Elasticsearch integration.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from backend_core.database import get_db_session
from backend_core.services.elasticsearch_client import ElasticsearchClient
from .models.file import File, FileAccessLog, FileShare, FileStatus
from .config import file_manager_settings
from .services.storage_service import StorageService

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_shares():
    """
    Clean up expired file shares.
    
    This task deactivates shares that have expired or reached their maximum access count.
    """
    logger.info("Starting cleanup of expired file shares")
    
    with get_db_session() as db:
        # Find expired shares
        expired_shares = db.query(FileShare).filter(
            FileShare.is_active == True,
            FileShare.expires_at.isnot(None),
            FileShare.expires_at < datetime.utcnow()
        ).all()
        
        # Find shares that have reached max access count
        max_access_shares = db.query(FileShare).filter(
            FileShare.is_active == True,
            FileShare.max_access_count.isnot(None),
            FileShare.access_count >= FileShare.max_access_count
        ).all()
        
        # Deactivate expired shares
        for share in expired_shares + max_access_shares:
            share.is_active = False
            logger.info(f"Deactivated expired share {share.id} for file {share.file_id}")
        
        db.commit()
    
    logger.info(f"Completed cleanup of expired file shares. Deactivated {len(expired_shares) + len(max_access_shares)} shares.")


@shared_task
def cleanup_temporary_files():
    """
    Clean up temporary files.
    
    This task removes temporary files that are older than a specified threshold.
    """
    logger.info("Starting cleanup of temporary files")
    
    temp_dir = file_manager_settings.TEMP_DIR
    threshold = datetime.now() - timedelta(days=1)  # Remove files older than 1 day
    
    if not os.path.exists(temp_dir):
        logger.info(f"Temporary directory {temp_dir} does not exist")
        return
    
    count = 0
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        # Check file age
        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_modified < threshold:
            try:
                os.remove(file_path)
                count += 1
                logger.debug(f"Removed temporary file {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove temporary file {file_path}: {str(e)}")
    
    logger.info(f"Completed cleanup of temporary files. Removed {count} files.")


@shared_task
def sync_file_access_logs_to_elasticsearch(batch_size: int = 100):
    """
    Sync file access logs to Elasticsearch.
    
    Args:
        batch_size: Number of logs to process in each batch
    """
    if not file_manager_settings.ENABLE_ELASTICSEARCH:
        logger.info("Elasticsearch integration is disabled. Skipping sync.")
        return
    
    logger.info("Starting sync of file access logs to Elasticsearch")
    
    es_client = ElasticsearchClient()
    index_name = file_manager_settings.ELASTICSEARCH_INDEX
    
    with get_db_session() as db:
        # Get logs that haven't been synced yet
        logs = db.query(FileAccessLog).filter(
            FileAccessLog.elasticsearch_synced == False
        ).limit(batch_size).all()
        
        if not logs:
            logger.info("No file access logs to sync")
            return
        
        # Prepare logs for bulk indexing
        actions = []
        for log in logs:
            # Get file details
            file = db.query(File).filter(File.id == log.file_id).first()
            
            if not file:
                logger.warning(f"File {log.file_id} not found for log {log.id}")
                log.elasticsearch_synced = True
                continue
            
            # Create document
            doc = {
                "file_id": log.file_id,
                "file_name": file.filename,
                "file_type": file.file_type,
                "user_id": log.user_id,
                "operation": log.operation,
                "timestamp": log.timestamp.isoformat(),
                "success": log.success,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "module": file.module,
                "entity_type": file.entity_type,
                "entity_id": file.entity_id
            }
            
            actions.append({
                "_index": index_name,
                "_id": str(log.id),
                "_source": doc
            })
        
        # Bulk index to Elasticsearch
        if actions:
            success, failed = es_client.bulk_index(actions)
            
            # Mark successfully indexed logs as synced
            for log in logs:
                if str(log.id) not in failed:
                    log.elasticsearch_synced = True
            
            db.commit()
            
            logger.info(f"Synced {success} file access logs to Elasticsearch. Failed: {len(failed)}")
    
    logger.info("Completed sync of file access logs to Elasticsearch")


@shared_task
def process_file_for_indexing(file_id: int):
    """
    Process a file for indexing in Elasticsearch.
    
    This task extracts text content from files (where possible) and indexes it in Elasticsearch
    for full-text search capabilities.
    
    Args:
        file_id: ID of the file to process
    """
    if not file_manager_settings.ENABLE_ELASTICSEARCH:
        logger.info("Elasticsearch integration is disabled. Skipping indexing.")
        return
    
    logger.info(f"Starting processing of file {file_id} for indexing")
    
    with get_db_session() as db:
        file = db.query(File).filter(File.id == file_id).first()
        
        if not file:
            logger.warning(f"File {file_id} not found")
            return
        
        # Skip processing for certain file types
        if file.file_type not in ['document', 'text']:
            logger.info(f"Skipping indexing for file type {file.file_type}")
            return
        
        storage_service = StorageService()
        es_client = ElasticsearchClient()
        index_name = file_manager_settings.ELASTICSEARCH_INDEX + "_content"
        
        try:
            # Retrieve file content
            file_data = await storage_service.retrieve_file(
                storage_backend=file.storage_backend,
                storage_path=file.storage_path
            )
            
            # Extract text content (implementation depends on file type)
            text_content = extract_text_from_file(file_data, file.mime_type)
            
            if text_content:
                # Create document
                doc = {
                    "file_id": file.id,
                    "file_name": file.filename,
                    "file_type": file.file_type,
                    "mime_type": file.mime_type,
                    "title": file.title,
                    "description": file.description,
                    "tags": file.tags,
                    "content": text_content,
                    "owner_id": file.owner_id,
                    "module": file.module,
                    "entity_type": file.entity_type,
                    "entity_id": file.entity_id,
                    "created_at": file.created_at.isoformat(),
                    "updated_at": file.updated_at.isoformat()
                }
                
                # Index to Elasticsearch
                es_client.index_document(index_name, str(file.id), doc)
                
                logger.info(f"Successfully indexed content for file {file_id}")
            else:
                logger.warning(f"No text content extracted from file {file_id}")
        
        except Exception as e:
            logger.error(f"Failed to process file {file_id} for indexing: {str(e)}")
    
    logger.info(f"Completed processing of file {file_id} for indexing")


def extract_text_from_file(file_data, mime_type: str) -> Optional[str]:
    """
    Extract text content from a file.
    
    Args:
        file_data: File data
        mime_type: MIME type of the file
        
    Returns:
        Extracted text content or None if extraction is not possible
    """
    # TODO: Implement text extraction based on file type
    # This would typically use libraries like PyPDF2 for PDFs,
    # python-docx for Word documents, etc.
    
    # For now, return None to indicate no extraction
    return None


@shared_task
def cleanup_deleted_files(days_to_keep: int = 30):
    """
    Permanently delete files that have been marked as deleted for a specified period.
    
    Args:
        days_to_keep: Number of days to keep deleted files before permanent deletion
    """
    logger.info(f"Starting cleanup of deleted files older than {days_to_keep} days")
    
    threshold = datetime.utcnow() - timedelta(days=days_to_keep)
    
    with get_db_session() as db:
        # Find files marked as deleted before the threshold
        files_to_delete = db.query(File).filter(
            File.status == FileStatus.DELETED,
            File.updated_at < threshold
        ).all()
        
        if not files_to_delete:
            logger.info("No deleted files to clean up")
            return
        
        storage_service = StorageService()
        count = 0
        
        for file in files_to_delete:
            try:
                # Delete file from storage
                success = await storage_service.delete_file(
                    storage_backend=file.storage_backend,
                    storage_path=file.storage_path
                )
                
                if success:
                    # Delete all versions from storage
                    for version in file.versions:
                        if version.storage_path != file.storage_path:
                            await storage_service.delete_file(
                                storage_backend=file.storage_backend,
                                storage_path=version.storage_path
                            )
                    
                    # Delete file record
                    db.delete(file)
                    count += 1
                    logger.info(f"Permanently deleted file {file.id}")
                else:
                    logger.warning(f"Failed to delete file {file.id} from storage")
            
            except Exception as e:
                logger.error(f"Error deleting file {file.id}: {str(e)}")
        
        db.commit()
        
        logger.info(f"Completed cleanup of deleted files. Permanently deleted {count} files.")
