# File Manager & Document Handling Module

A comprehensive file management system for the ISP Management Platform, providing centralized document storage, access control, and version tracking.

## Features

- **Secure Document Storage**: Store files with encryption options for sensitive documents
- **Multiple Storage Backends**: Support for local filesystem and S3-compatible storage
- **Role-Based Access Control**: Fine-grained permissions for file operations
- **Version Tracking**: Track file versions with change history
- **File Sharing**: Generate shareable links with optional password protection and expiration
- **Folder Management**: Organize files in hierarchical folder structures
- **Search Capabilities**: Search files by metadata, content, and tags
- **Audit Logging**: Track all file access and modifications
- **Elasticsearch Integration**: Index file metadata and content for advanced search capabilities

## Setup

### Environment Variables

Configure the module by setting the following environment variables:

```
# Local storage settings
FILE_MANAGER_LOCAL_STORAGE_PATH=./storage/files

# S3 storage settings
FILE_MANAGER_S3_BUCKET_NAME=isp-management-files
FILE_MANAGER_S3_ACCESS_KEY=your-access-key
FILE_MANAGER_S3_SECRET_KEY=your-secret-key
FILE_MANAGER_S3_ENDPOINT_URL=https://s3.amazonaws.com
FILE_MANAGER_S3_REGION=us-east-1

# File upload settings
FILE_MANAGER_MAX_UPLOAD_SIZE=104857600
FILE_MANAGER_ALLOWED_EXTENSIONS=.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.jpg,.jpeg,.png,.gif

# Security settings
FILE_MANAGER_ENCRYPT_FILES=False
FILE_MANAGER_ENCRYPTION_KEY=your-encryption-key

# Elasticsearch integration
FILE_MANAGER_ENABLE_ELASTICSEARCH=False
FILE_MANAGER_ELASTICSEARCH_INDEX=isp_management_files

# Default storage backend (local or s3)
FILE_MANAGER_DEFAULT_STORAGE_BACKEND=local

# Temporary directory for file processing
FILE_MANAGER_TEMP_DIR=/tmp/isp_management_files
```

### Database Migration

Run the database migration to create the necessary tables:

```bash
alembic upgrade head
```

## API Endpoints

### File Operations

- `POST /file-manager/files/`: Upload a new file
- `GET /file-manager/files/{file_id}`: Get file details
- `GET /file-manager/files/by-uuid/{file_uuid}`: Get file details by UUID
- `GET /file-manager/files/`: List files with optional filtering
- `PUT /file-manager/files/{file_id}`: Update file metadata
- `PUT /file-manager/files/{file_id}/content`: Update file content (create new version)
- `DELETE /file-manager/files/{file_id}`: Delete a file
- `GET /file-manager/files/{file_id}/download`: Download a file

### Folder Operations

- `POST /file-manager/folders/`: Create a new folder
- `GET /file-manager/folders/{folder_id}`: Get folder details
- `GET /file-manager/folders/`: List folders with optional filtering
- `PUT /file-manager/folders/{folder_id}`: Update folder metadata
- `DELETE /file-manager/folders/{folder_id}`: Delete a folder

### Permission Operations

- `POST /file-manager/files/{file_id}/permissions`: Set file permissions
- `DELETE /file-manager/files/{file_id}/permissions/{user_id}`: Remove file permissions
- `GET /file-manager/files/{file_id}/permissions`: Get file permissions

### Sharing Operations

- `POST /file-manager/files/{file_id}/shares`: Create a shareable link
- `GET /file-manager/shares/{share_id}`: Access a shared file
- `DELETE /file-manager/shares/{share_id}`: Deactivate a file share

## Integration with Other Modules

### Accessing Files from Other Modules

To access files from other modules, use the `module`, `entity_type`, and `entity_id` parameters when creating or querying files. For example:

```python
# Create a file associated with a customer
file_data = FileCreate(
    original_filename="contract.pdf",
    title="Customer Contract",
    file_type=FileType.DOCUMENT,
    module="crm",
    entity_type="customer",
    entity_id=customer_id,
    tags=["contract", "legal"]
)

# Query files for a specific customer
files = file_service.list_files(
    user_id=current_user.id,
    search_params=FileSearchParams(
        module="crm",
        entity_type="customer",
        entity_id=customer_id
    )
)
```

### Background Tasks

The module includes several Celery tasks for background processing:

- `cleanup_expired_shares`: Clean up expired file shares
- `cleanup_temporary_files`: Remove temporary files
- `sync_file_access_logs_to_elasticsearch`: Sync access logs to Elasticsearch
- `process_file_for_indexing`: Extract and index file content
- `cleanup_deleted_files`: Permanently delete files marked as deleted

## Security Considerations

- Files can be encrypted at rest using the `is_encrypted` flag
- Access control is enforced at the API level for all file operations
- All file access is logged for audit purposes
- Shared links can be protected with passwords and expiration dates

## Performance Optimization

- Files are stored with optimized paths based on their module and entity
- Elasticsearch integration provides fast search capabilities
- Background tasks handle resource-intensive operations asynchronously
- Pagination is implemented for all list endpoints
