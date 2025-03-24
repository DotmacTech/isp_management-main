"""
Targeted test script for FilePermissionCreate schema validation.

This script directly tests the FilePermissionCreate schema's model_validator
which we updated as part of the Pydantic 2 migration.
"""

import os
import sys
from typing import Optional

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import just the specific schema we need to test
from modules.file_manager.schemas.file import FilePermissionCreate


def test_file_permission_validation():
    """Test all validation cases for FilePermissionCreate."""
    print("Testing FilePermissionCreate Validation Cases")
    print("=" * 50)
    
    # Test Case 1: Valid - Only user_id provided
    print("\nTest Case 1: Valid - Only user_id provided")
    try:
        perm = FilePermissionCreate(user_id=1, can_read=True, can_write=True)
        print(f"✅ PASS: Created permission with user_id={perm.user_id}")
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
    
    # Test Case 2: Valid - Only group_id provided
    print("\nTest Case 2: Valid - Only group_id provided")
    try:
        perm = FilePermissionCreate(group_id=2, can_read=True)
        print(f"✅ PASS: Created permission with group_id={perm.group_id}")
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
    
    # Test Case 3: Invalid - Both user_id and group_id provided
    print("\nTest Case 3: Invalid - Both user_id and group_id provided")
    try:
        perm = FilePermissionCreate(user_id=1, group_id=2)
        print(f"❌ FAIL: Validation should have rejected both user_id and group_id")
    except ValueError as e:
        print(f"✅ PASS: Correctly rejected with error: {str(e)}")
    except Exception as e:
        print(f"❓ UNEXPECTED ERROR: {str(e)}")
    
    # Test Case 4: Invalid - Neither user_id nor group_id provided
    print("\nTest Case 4: Invalid - Neither user_id nor group_id provided")
    try:
        perm = FilePermissionCreate(can_read=True)
        print(f"❌ FAIL: Validation should have rejected missing user_id/group_id")
    except ValueError as e:
        print(f"✅ PASS: Correctly rejected with error: {str(e)}")
    except Exception as e:
        print(f"❓ UNEXPECTED ERROR: {str(e)}")
    
    print("\n" + "=" * 50)
    

if __name__ == "__main__":
    test_file_permission_validation()
