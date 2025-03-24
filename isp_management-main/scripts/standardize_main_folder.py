#!/usr/bin/env python3
"""
Main Folder Standardization Script

This script standardizes the main folder structure of the ISP Management Platform.
It organizes the root directory according to best practices for maintainability and clarity.

Usage:
    python standardize_main_folder.py

"""

import os
import sys
import shutil
from pathlib import Path
import re

# Define the standard directory structure for the main folder
STANDARD_DIRECTORIES = {
    'api': 'Central API gateway and routing',
    'config': 'Application-wide configuration',
    'core': 'Core functionality and shared components',
    'docs': 'Documentation files',
    'migrations': 'Database migration scripts',
    'modules': 'Feature modules',
    'scripts': 'Utility and automation scripts',
    'static': 'Static assets',
    'templates': 'Template files',
    'tests': 'Test files and fixtures',
    'utils': 'Utility functions and helpers',
}

# Files that should be in the root directory
ROOT_FILES = [
    'README.md',
    'requirements.txt',
    'requirements-dev.txt',
    'requirements-test.txt',
    '.env.example',
    '.gitignore',
    'main.py',
    'conftest.py',
    'pytest.ini',
    'alembic.ini',
]

def create_directory_structure(base_path):
    """Create the standard directory structure for the main folder."""
    print("Creating standard directory structure...")
    
    for directory, description in STANDARD_DIRECTORIES.items():
        dir_path = base_path / directory
        
        # Create directory if it doesn't exist
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"Created directory: {directory}")
        
        # Create or update __init__.py with description
        init_file = dir_path / '__init__.py'
        with open(init_file, 'w') as f:
            f.write(f'"""\n{description}.\n\nThis package contains {directory} for the ISP Management Platform.\n"""\n')
            print(f"Updated __init__.py in {directory}")

def create_readme_if_missing(base_path):
    """Create README.md files in each standard directory if missing."""
    print("Creating README.md files in standard directories...")
    
    for directory, description in STANDARD_DIRECTORIES.items():
        dir_path = base_path / directory
        readme_path = dir_path / 'README.md'
        
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write(f'# {directory.capitalize()}\n\n{description}.\n\n')
                f.write(f'## Purpose\n\nThis directory contains {directory} for the ISP Management Platform.\n\n')
                f.write('## Structure\n\n```\n')
                f.write(f'{directory}/\n')
                f.write('├── ...\n')
                f.write('└── ...\n')
                f.write('```\n')
                print(f"Created README.md in {directory}")

def update_main_readme(base_path):
    """Update the main README.md with the standard directory structure."""
    print("Updating main README.md...")
    
    readme_path = base_path / 'README.md'
    
    if readme_path.exists():
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Check if the structure section already exists
        structure_section = "## Directory Structure"
        if structure_section in content:
            print("Structure section already exists in README.md, skipping update.")
            return
        
        # Add the structure section
        structure_content = f"\n\n{structure_section}\n\n"
        structure_content += "The ISP Management Platform follows a standardized directory structure:\n\n"
        structure_content += "```\n"
        structure_content += "isp_management/\n"
        
        # Add root files
        for file in sorted(ROOT_FILES):
            if (base_path / file).exists():
                structure_content += f"├── {file}\n"
        
        # Add directories
        for directory in sorted(STANDARD_DIRECTORIES.keys()):
            structure_content += f"├── {directory}/  # {STANDARD_DIRECTORIES[directory]}\n"
        
        structure_content += "```\n"
        
        # Append to the end of the README
        with open(readme_path, 'w') as f:
            f.write(content + structure_content)
            print("Updated README.md with directory structure")
    else:
        print("README.md not found, skipping update.")

def create_main_init(base_path):
    """Create or update the main __init__.py file."""
    print("Updating main __init__.py...")
    
    init_path = base_path / '__init__.py'
    
    content = '''"""
ISP Management Platform

This package provides a comprehensive solution for ISP management,
including customer management, billing, network monitoring, and more.
"""

__version__ = "1.0.0"
__author__ = "ISP Management Team"
'''
    
    with open(init_path, 'w') as f:
        f.write(content)
        print("Updated main __init__.py")

def standardize_main_folder():
    """Standardize the structure of the main folder."""
    base_path = Path(__file__).parent.parent
    
    print(f"Standardizing main folder structure at: {base_path}")
    
    # Create the directory structure
    create_directory_structure(base_path)
    
    # Create README.md files in each directory
    create_readme_if_missing(base_path)
    
    # Update the main README.md
    update_main_readme(base_path)
    
    # Create or update the main __init__.py
    create_main_init(base_path)
    
    print("Main folder standardization completed.")
    print("Please review the changes and update any imports as needed.")

if __name__ == '__main__':
    standardize_main_folder()
