"""
Simple script to validate file_manager schemas with Pydantic 2.

This script creates sample data and validates it against the schemas
to ensure Pydantic 2 compatibility without running a full test suite.
"""

import os
import sys
from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the schemas and models directly
from modules.file_manager.models.file import FileType, StorageBackend, FileStatus
from modules.file_manager.schemas.file import (
    FileCreate, FileUpdate, FilePermissionCreate, FileVersionCreate,
    FileShareCreate, FolderCreate, FolderUpdate
)

def validate_schemas():
    """Validate all schemas with sample data."""
    print("Testing File Manager Schemas with Pydantic 2")
    print("=" * 50)
    
    # Sample data for testing
    file_create_data = {
        "original_filename": "test_document.pdf",
        "title": "Test Document",
        "description": "A test document for validation",
        "file_type": "pdf",  # Using string value
        "mime_type": "application/pdf",
        "tags": ["test", "document", "pdf"],
        "metadata": {"test_key": "test_value"},
        "module": "testing",
        "entity_type": "test",
        "entity_id": 1,
        "is_encrypted": False
    }
    
    file_update_data = {
        "title": "Updated Test Document",
        "description": "An updated test document",
        "tags": ["test", "document", "updated"],
        "metadata": {"test_key": "updated_value"},
        "status": "archived"  # Using string value
    }
    
    file_permission_data = {
        "user_id": 1,
        "can_read": True,
        "can_write": True,
        "can_delete": False
    }
    
    file_version_data = {
        "change_summary": "Updated test document"
    }
    
    file_share_data = {
        "expires_at": datetime.utcnow(),
        "password_protected": True,
        "password": "test_password",
        "max_downloads": 5
    }
    
    folder_create_data = {
        "name": "Test Folder",
        "parent_id": None
    }
    
    folder_update_data = {
        "name": "Updated Test Folder"
    }
    
    # Test FileCreate schema
    print("\nTesting FileCreate schema...")
    try:
        file_create = FileCreate(**file_create_data)
        print(f"✅ FileCreate validation passed")
        print(f"   title: {file_create.title}")
        print(f"   file_type: {file_create.file_type}")
    except Exception as e:
        print(f"❌ FileCreate validation failed: {str(e)}")
    
    # Test FileUpdate schema
    print("\nTesting FileUpdate schema...")
    try:
        file_update = FileUpdate(**file_update_data)
        print(f"✅ FileUpdate validation passed")
        print(f"   title: {file_update.title}")
        print(f"   status: {file_update.status}")
    except Exception as e:
        print(f"❌ FileUpdate validation failed: {str(e)}")
    
    # Test FilePermissionCreate schema
    print("\nTesting FilePermissionCreate schema...")
    try:
        file_permission = FilePermissionCreate(**file_permission_data)
        print(f"✅ FilePermissionCreate validation passed")
        print(f"   user_id: {file_permission.user_id}")
        print(f"   can_write: {file_permission.can_write}")
        
        # Test validation logic
        try:
            invalid_permission = FilePermissionCreate(user_id=1, group_id=1)
            print(f"❌ Validation should have failed for both user_id and group_id")
        except ValueError as ve:
            print(f"✅ Correctly rejected both user_id and group_id: {str(ve)}")
            
        try:
            invalid_permission = FilePermissionCreate(can_read=True)
            print(f"❌ Validation should have failed for missing user_id/group_id")
        except ValueError as ve:
            print(f"✅ Correctly rejected missing user_id/group_id: {str(ve)}")
    except Exception as e:
        print(f"❌ FilePermissionCreate validation failed: {str(e)}")
    
    # Test FileVersionCreate schema
    print("\nTesting FileVersionCreate schema...")
    try:
        file_version = FileVersionCreate(**file_version_data)
        print(f"✅ FileVersionCreate validation passed")
        print(f"   change_summary: {file_version.change_summary}")
    except Exception as e:
        print(f"❌ FileVersionCreate validation failed: {str(e)}")
    
    # Test FileShareCreate schema
    print("\nTesting FileShareCreate schema...")
    try:
        file_share = FileShareCreate(**file_share_data)
        print(f"✅ FileShareCreate validation passed")
        print(f"   password_protected: {file_share.password_protected}")
        print(f"   max_downloads: {file_share.max_downloads}")
    except Exception as e:
        print(f"❌ FileShareCreate validation failed: {str(e)}")
    
    # Test FolderCreate schema
    print("\nTesting FolderCreate schema...")
    try:
        folder_create = FolderCreate(**folder_create_data)
        print(f"✅ FolderCreate validation passed")
        print(f"   name: {folder_create.name}")
    except Exception as e:
        print(f"❌ FolderCreate validation failed: {str(e)}")
    
    # Test FolderUpdate schema
    print("\nTesting FolderUpdate schema...")
    try:
        folder_update = FolderUpdate(**folder_update_data)
        print(f"✅ FolderUpdate validation passed")
        print(f"   name: {folder_update.name}")
    except Exception as e:
        print(f"❌ FolderUpdate validation failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Schema validation complete!")

if __name__ == "__main__":
    validate_schemas()
