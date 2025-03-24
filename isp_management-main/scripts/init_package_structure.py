#!/usr/bin/env python3
"""
Initialize Package Structure

This script ensures that all standardized directories are properly recognized as Python packages
by creating or updating __init__.py files where needed.

Usage:
    python init_package_structure.py

"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


def ensure_init_file(directory_path):
    """
    Ensure that a directory has an __init__.py file.
    If the file doesn't exist, create it with a basic docstring.
    """
    init_file = directory_path / "__init__.py"
    
    if not init_file.exists():
        dir_name = directory_path.name
        parent_name = directory_path.parent.name
        
        # Create a descriptive docstring based on the directory name
        if parent_name == "modules":
            docstring = f'"""\n{dir_name.capitalize()} module for the ISP Management Platform.\n"""\n'
        else:
            docstring = f'"""\n{dir_name.capitalize()} package for the {parent_name} module.\n"""\n'
        
        # Write the __init__.py file
        with open(init_file, "w") as f:
            f.write(docstring)
        
        print(f"Created {init_file}")
        return True
    
    return False


def ensure_module_structure(module_path):
    """
    Ensure that a module has the standardized directory structure
    and that all directories are properly recognized as Python packages.
    """
    # Standard subdirectories for each module
    standard_dirs = [
        "api",
        "config",
        "models",
        "schemas",
        "services",
        "utils"
    ]
    
    # Ensure the module itself has an __init__.py
    module_init_created = ensure_init_file(module_path)
    
    # Ensure each standard subdirectory exists and has an __init__.py
    for subdir in standard_dirs:
        subdir_path = module_path / subdir
        
        # Create the directory if it doesn't exist
        if not subdir_path.exists():
            subdir_path.mkdir(exist_ok=True)
            print(f"Created directory {subdir_path}")
        
        # Ensure the subdirectory has an __init__.py
        ensure_init_file(subdir_path)
    
    return module_init_created


def ensure_tests_structure(tests_path):
    """
    Ensure that the tests directory structure matches the module structure
    and that all test directories are properly recognized as Python packages.
    """
    # Ensure the tests directory has an __init__.py
    ensure_init_file(tests_path)
    
    # Create a modules directory in tests if it doesn't exist
    modules_test_path = tests_path / "modules"
    if not modules_test_path.exists():
        modules_test_path.mkdir(exist_ok=True)
        print(f"Created directory {modules_test_path}")
    
    # Ensure the modules test directory has an __init__.py
    ensure_init_file(modules_test_path)
    
    # Get all module directories
    modules_path = project_root / "modules"
    module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    # Ensure each module has a corresponding test directory
    for module_dir in module_dirs:
        module_name = module_dir.name
        module_test_path = modules_test_path / module_name
        
        # Create the module test directory if it doesn't exist
        if not module_test_path.exists():
            module_test_path.mkdir(exist_ok=True)
            print(f"Created test directory {module_test_path}")
        
        # Ensure the module test directory has an __init__.py
        ensure_init_file(module_test_path)


def initialize_package_structure():
    """
    Initialize the package structure for the entire project.
    """
    print("Initializing package structure...")
    
    # Ensure the root directory has an __init__.py
    root_init_created = ensure_init_file(project_root)
    if root_init_created:
        print("Created root __init__.py")
    
    # Ensure the modules directory has an __init__.py
    modules_path = project_root / "modules"
    modules_init_created = ensure_init_file(modules_path)
    if modules_init_created:
        print("Created modules __init__.py")
    
    # Get all module directories
    module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    # Ensure each module has the standardized structure
    for module_dir in module_dirs:
        module_init_created = ensure_module_structure(module_dir)
        if module_init_created:
            print(f"Created {module_dir.name} __init__.py")
    
    # Ensure the tests directory structure matches the module structure
    tests_path = project_root / "tests"
    ensure_tests_structure(tests_path)
    
    print("Package structure initialization complete.")


if __name__ == "__main__":
    initialize_package_structure()
