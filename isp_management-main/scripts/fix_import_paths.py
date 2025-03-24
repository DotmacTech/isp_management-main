#!/usr/bin/env python3
"""
Fix Import Paths

This script updates import paths in Python files to work with the standardized module structure.
It recursively searches through all Python files in the project and fixes import statements.

Usage:
    python fix_import_paths.py

"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Patterns to search for and replace
IMPORT_PATTERNS = [
    # Fix old-style imports from isp_management
    (r'from isp_management\.backend_core', r'from backend_core'),
    (r'from isp_management\.modules', r'from modules'),
    (r'import isp_management\.backend_core', r'import backend_core'),
    (r'import isp_management\.modules', r'import modules'),
    
    # Fix relative imports in modules
    (r'from \.\.(\.+)([a-zA-Z_]+) import', r'from modules.\2 import'),
    (r'from \.\. import ([a-zA-Z_]+)', r'from modules import \1'),
]

def fix_imports_in_file(file_path):
    """
    Fix import statements in a single Python file.
    
    Args:
        file_path: Path to the Python file to fix
    
    Returns:
        bool: True if the file was modified, False otherwise
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Apply all patterns
    for pattern, replacement in IMPORT_PATTERNS:
        content = re.sub(pattern, replacement, content)
    
    # Check if the file was modified
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    
    return False

def fix_imports_in_directory(directory_path, extensions=None):
    """
    Recursively fix import statements in all Python files in a directory.
    
    Args:
        directory_path: Path to the directory to process
        extensions: List of file extensions to process (default: ['.py'])
    
    Returns:
        int: Number of files modified
    """
    if extensions is None:
        extensions = ['.py']
    
    modified_files = 0
    
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    print(f"Fixed imports in {file_path}")
                    modified_files += 1
    
    return modified_files

def add_path_setup_to_test_files(test_dir):
    """
    Add path setup code to all test files to ensure proper imports.
    
    Args:
        test_dir: Path to the test directory
    
    Returns:
        int: Number of files modified
    """
    modified_files = 0
    
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py') and file.startswith('test_'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if path setup is already present
                if 'import sys' in content and 'sys.path.insert' in content:
                    continue
                
                # Add path setup at the beginning of the file
                path_setup = """import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

"""
                
                # Find the first import statement
                import_match = re.search(r'^(import|from)\s+', content, re.MULTILINE)
                if import_match:
                    # Insert path setup before the first import
                    pos = import_match.start()
                    new_content = content[:pos] + path_setup + content[pos:]
                else:
                    # No import statement found, add at the beginning after any docstring
                    docstring_end = re.search(r'""".*?"""\s*$', content, re.DOTALL)
                    if docstring_end:
                        pos = docstring_end.end()
                        new_content = content[:pos] + "\n" + path_setup + content[pos:]
                    else:
                        new_content = path_setup + content
                
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                print(f"Added path setup to {file_path}")
                modified_files += 1
    
    return modified_files

def fix_conftest_files(test_dir):
    """
    Fix conftest.py files in the test directory.
    
    Args:
        test_dir: Path to the test directory
    
    Returns:
        int: Number of files modified
    """
    modified_files = 0
    
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file == 'conftest.py':
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if path setup is already present
                if 'import sys' in content and 'sys.path.insert' in content:
                    continue
                
                # Add path setup at the beginning of the file
                path_setup = """import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

"""
                
                # Find the first import statement
                import_match = re.search(r'^(import|from)\s+', content, re.MULTILINE)
                if import_match:
                    # Insert path setup before the first import
                    pos = import_match.start()
                    new_content = content[:pos] + path_setup + content[pos:]
                else:
                    # No import statement found, add at the beginning after any docstring
                    docstring_end = re.search(r'""".*?"""\s*$', content, re.DOTALL)
                    if docstring_end:
                        pos = docstring_end.end()
                        new_content = content[:pos] + "\n" + path_setup + content[pos:]
                    else:
                        new_content = path_setup + content
                
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                print(f"Fixed conftest file: {file_path}")
                modified_files += 1
    
    return modified_files

def create_module_init_files():
    """
    Create proper __init__.py files for all modules with router imports.
    
    Returns:
        int: Number of files created or modified
    """
    modules_dir = project_root / 'modules'
    modified_files = 0
    
    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith('__'):
            continue
        
        # Create or update the module's __init__.py
        init_file = module_dir / '__init__.py'
        api_dir = module_dir / 'api'
        api_init_file = api_dir / '__init__.py'
        
        # If the module has an API directory with a router, update the module's __init__.py
        if api_dir.exists() and api_init_file.exists():
            with open(api_init_file, 'r') as f:
                api_init_content = f.read()
            
            # Check if the API init file defines a router
            if 'router' in api_init_content:
                # Create or update the module's __init__.py to import and expose the router
                init_content = f'''"""
{module_dir.name.capitalize()} module for the ISP Management Platform.
"""

# Import and expose the API router
from .api import router

__all__ = ['router']
'''
                
                # Only write if the file doesn't exist or has different content
                if not init_file.exists():
                    with open(init_file, 'w') as f:
                        f.write(init_content)
                    print(f"Created module __init__.py: {init_file}")
                    modified_files += 1
                else:
                    with open(init_file, 'r') as f:
                        current_content = f.read()
                    
                    if current_content != init_content:
                        with open(init_file, 'w') as f:
                            f.write(init_content)
                        print(f"Updated module __init__.py: {init_file}")
                        modified_files += 1
    
    return modified_files

def fix_auth_service_imports():
    """
    Fix imports in the auth_service.py file.
    
    Returns:
        bool: True if the file was modified, False otherwise
    """
    auth_service_file = project_root / 'backend_core' / 'auth_service.py'
    
    if not auth_service_file.exists():
        print(f"Auth service file not found: {auth_service_file}")
        return False
    
    with open(auth_service_file, 'r') as f:
        content = f.read()
    
    # Check if the function is already defined
    if 'get_current_user_with_permissions' not in content:
        # Add the missing function
        new_function = '''

async def get_current_user_with_permissions(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    required_permissions: List[str] = None
) -> User:
    """
    Verify the token and check if the user has the required permissions.
    
    Args:
        token: The JWT token
        db: Database session
        required_permissions: List of permission strings required to access the endpoint
        
    Returns:
        User: The authenticated user with the required permissions
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't have the required permissions
    """
    user = await get_current_active_user(token, db)
    
    if required_permissions:
        user_permissions = get_user_permissions(user.id, db)
        
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
    
    return user
'''
        
        # Add the new function after the get_current_active_user function
        pattern = r'async def get_current_active_user\([^)]*\):[^}]*?\n\s*return user'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            pos = match.end()
            new_content = content[:pos] + new_function + content[pos:]
            
            with open(auth_service_file, 'w') as f:
                f.write(new_content)
            
            print(f"Added get_current_user_with_permissions function to {auth_service_file}")
            return True
    
    return False

def main():
    """
    Main function to fix import paths in the project.
    """
    print("=== Fixing Import Paths ===")
    
    # Fix imports in the modules directory
    modules_dir = project_root / 'modules'
    modules_modified = fix_imports_in_directory(modules_dir)
    print(f"Fixed imports in {modules_modified} module files")
    
    # Fix imports in the tests directory
    tests_dir = project_root / 'tests'
    tests_modified = fix_imports_in_directory(tests_dir)
    print(f"Fixed imports in {tests_modified} test files")
    
    # Add path setup to test files
    test_files_modified = add_path_setup_to_test_files(tests_dir)
    print(f"Added path setup to {test_files_modified} test files")
    
    # Fix conftest files
    conftest_files_modified = fix_conftest_files(tests_dir)
    print(f"Fixed {conftest_files_modified} conftest files")
    
    # Create proper module __init__.py files
    module_inits_modified = create_module_init_files()
    print(f"Created or updated {module_inits_modified} module __init__.py files")
    
    # Fix auth service imports
    auth_service_modified = fix_auth_service_imports()
    if auth_service_modified:
        print("Fixed auth_service.py")
    
    print("Import path fixing complete.")


if __name__ == "__main__":
    main()
