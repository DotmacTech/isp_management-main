"""
Standalone script to validate Pydantic 2 compatibility of our schema changes.

This script recreates the essential parts of our schemas to test the Pydantic 2 syntax changes
without requiring the entire application context.
"""

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict

# Mock enums to avoid importing from the actual models
class FileType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    OTHER = "other"

class FileStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

# Recreation of the updated schemas with Pydantic 2 syntax
class FileBase(BaseModel):
    """Base schema for files."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Example File",
                "description": "This is an example file",
                "tags": ["example", "file"],
                "metadata": {"key": "value"}
            }
        }
    )

class FileCreate(FileBase):
    """Schema for creating files."""
    original_filename: str
    file_type: FileType = FileType.OTHER
    mime_type: str
    module: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    is_encrypted: bool = False

class FileUpdate(FileBase):
    """Schema for updating files."""
    status: Optional[FileStatus] = None

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
        if self.user_id is None and self.group_id is None:
            raise ValueError('Either user_id or group_id must be provided')
        
        if self.user_id is not None and self.group_id is not None:
            raise ValueError('Only one of user_id or group_id can be provided')
            
        return self

class ResponseModel(BaseModel):
    """Example response model with from_attributes=True."""
    id: int
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

def validate_pydantic2_features():
    """Validate the key Pydantic 2 features we updated."""
    print("Validating Pydantic 2 Features")
    print("=============================")
    
    # 1. Test ConfigDict for model configuration
    print("\n1. Testing ConfigDict for model configuration")
    try:
        file = FileBase(title="Test File")
        print(f"✅ ConfigDict works: {file.title}")
        # Check that the schema_extra is correctly set
        schema = FileBase.model_json_schema()
        if "example" in schema:
            print(f"✅ json_schema_extra works: example present in schema")
        else:
            print(f"❌ json_schema_extra not working: example missing from schema")
    except Exception as e:
        print(f"❌ ConfigDict failed: {str(e)}")
    
    # 2. Test model_validator replacement for validator
    print("\n2. Testing model_validator")
    try:
        # Valid permission with only user_id
        perm1 = FilePermissionCreate(user_id=1)
        print(f"✅ Valid permission with user_id: {perm1.user_id}")
        
        # Valid permission with only group_id
        perm2 = FilePermissionCreate(group_id=2)
        print(f"✅ Valid permission with group_id: {perm2.group_id}")
        
        # Test validation error when both are provided
        try:
            invalid_perm = FilePermissionCreate(user_id=1, group_id=1)
            print(f"❌ Validation should have failed for both user_id and group_id")
        except ValueError as ve:
            print(f"✅ model_validator correctly rejected both user_id and group_id: {str(ve)}")
            
        # Test validation error when neither is provided
        try:
            invalid_perm = FilePermissionCreate()
            print(f"❌ Validation should have failed for missing user_id/group_id")
        except ValueError as ve:
            print(f"✅ model_validator correctly rejected missing user_id/group_id: {str(ve)}")
    except Exception as e:
        print(f"❌ model_validator failed: {str(e)}")
    
    # 3. Test from_attributes replacement for orm_mode
    print("\n3. Testing from_attributes (replacement for orm_mode)")
    try:
        # Mock an ORM object with __dict__ attributes
        class MockORMObject:
            def __init__(self):
                self.id = 1
                self.name = "Test Object"
                self.created_at = datetime.utcnow()
        
        orm_obj = MockORMObject()
        
        # Convert ORM object to Pydantic model
        response = ResponseModel.model_validate(orm_obj)
        print(f"✅ from_attributes works: {response.id}, {response.name}")
    except Exception as e:
        print(f"❌ from_attributes failed: {str(e)}")
    
    print("\n=============================")
    print("Pydantic 2 Validation Complete!")

if __name__ == "__main__":
    validate_pydantic2_features()
