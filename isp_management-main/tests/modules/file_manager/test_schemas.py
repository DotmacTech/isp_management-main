"""
Tests for the file_manager module schemas.

This module directly tests the Pydantic schemas for the file_manager module,
focusing only on schema validation without dependencies.
"""

import pytest
from datetime import datetime
import uuid
from typing import Dict, Any, List
import sys
import os

# Import the schemas directly to avoid loading the entire module structure
sys.path.insert(0, os.path.abspath('/Users/michaelayoade/CascadeProjects/isp_management'))
from modules.file_manager.models.file import FileType, StorageBackend, FileStatus
from modules.file_manager.schemas.file import (
    FileBase, FileCreate, FileUpdate, FileVersionCreate, FilePermissionBase,
    FilePermissionCreate, FileShareBase, FileShareCreate, FolderBase, FolderCreate
)


@pytest.fixture
def sample_file_create_data():
    """Sample data for file creation."""
    return {
        "original_filename": "test_document.pdf",
        "title": "Test Document",
        "description": "A test document for unit testing",
        "file_type": "pdf",  # Using string value instead of enum
        "mime_type": "application/pdf",
        "tags": ["test", "document", "pdf"],
        "metadata": {"test_key": "test_value"},
        "module": "testing",
        "entity_type": "test",
        "entity_id": 1,
        "is_encrypted": False
    }


@pytest.fixture
def sample_file_update_data():
    """Sample data for file update."""
    return {
        "title": "Updated Test Document",
        "description": "An updated test document",
        "tags": ["test", "document", "updated"],
        "metadata": {"test_key": "updated_value"},
        "status": "archived"  # Using string value instead of enum
    }


@pytest.fixture
def sample_file_permission_data():
    """Sample data for file permission creation."""
    return {
        "user_id": 1,
        "can_read": True,
        "can_write": True,
        "can_delete": False
    }


@pytest.fixture
def sample_file_version_data():
    """Sample data for file version creation."""
    return {
        "change_summary": "Updated test document"
    }


@pytest.fixture
def sample_file_share_data():
    """Sample data for file share creation."""
    return {
        "expires_at": datetime.utcnow(),
        "password_protected": True,
        "password": "test_password",
        "max_downloads": 5
    }


@pytest.fixture
def sample_folder_create_data():
    """Sample data for folder creation."""
    return {
        "name": "Test Folder",
        "parent_id": None
    }


class TestFileSchemas:
    """Tests for file-related schemas."""

    def test_file_create(self, sample_file_create_data):
        """Test FileCreate schema."""
        file_create = FileCreate(**sample_file_create_data)
        assert file_create.original_filename == sample_file_create_data["original_filename"]
        assert file_create.title == sample_file_create_data["title"]
        assert file_create.description == sample_file_create_data["description"]
        assert file_create.mime_type == sample_file_create_data["mime_type"]
        assert file_create.tags == sample_file_create_data["tags"]
        assert file_create.metadata == sample_file_create_data["metadata"]

    def test_file_update(self, sample_file_update_data):
        """Test FileUpdate schema."""
        file_update = FileUpdate(**sample_file_update_data)
        assert file_update.title == sample_file_update_data["title"]
        assert file_update.description == sample_file_update_data["description"]
        assert file_update.tags == sample_file_update_data["tags"]
        assert file_update.metadata == sample_file_update_data["metadata"]
        
    def test_file_permission_validation(self):
        """Test FilePermissionCreate validation."""
        # Test with user_id
        permission_data = {
            "user_id": 1,
            "can_read": True,
            "can_write": True,
            "can_delete": False
        }
        permission = FilePermissionCreate(**permission_data)
        assert permission.user_id == 1
        assert permission.group_id is None
        
        # Test with group_id
        permission_data = {
            "group_id": 1,
            "can_read": True,
            "can_write": True,
            "can_delete": False
        }
        permission = FilePermissionCreate(**permission_data)
        assert permission.group_id == 1
        assert permission.user_id is None
        
        # Test validation error when both are provided
        with pytest.raises(ValueError):
            FilePermissionCreate(user_id=1, group_id=1)
            
        # Test validation error when neither is provided
        with pytest.raises(ValueError):
            FilePermissionCreate(can_read=True)


class TestFolderSchemas:
    """Tests for folder-related schemas."""
    
    def test_folder_create(self, sample_folder_create_data):
        """Test FolderCreate schema."""
        folder_create = FolderCreate(**sample_folder_create_data)
        assert folder_create.name == sample_folder_create_data["name"]
        assert folder_create.parent_id == sample_folder_create_data["parent_id"]
