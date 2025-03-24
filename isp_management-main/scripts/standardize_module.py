#!/usr/bin/env python3
"""
Module Standardization Script

This script helps automate the standardization of module structure in the ISP Management Platform.
It creates the standard directory structure and moves files to their appropriate locations.

Usage:
    python standardize_module.py <module_name>

Example:
    python standardize_module.py billing
"""

import os
import sys
import shutil
from pathlib import Path
import re


def create_directory_structure(module_path):
    """Create the standard directory structure for a module."""
    directories = ['api', 'config', 'models', 'schemas', 'services', 'utils']
    
    for directory in directories:
        dir_path = module_path / directory
        dir_path.mkdir(exist_ok=True)
        
        # Create __init__.py if it doesn't exist
        init_file = dir_path / '__init__.py'
        if not init_file.exists():
            with open(init_file, 'w') as f:
                f.write(f'"""\n{directory.capitalize()} for the {module_path.name} module.\n\nThis package contains {directory} for the {module_path.name} module.\n"""\n')


def create_api_init(module_path, module_name):
    """Create the API router initialization file."""
    api_init_path = module_path / 'api' / '__init__.py'
    
    content = f'''"""
API router initialization for {module_name} module.

This module provides the FastAPI router for {module_name} endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
'''
    
    with open(api_init_path, 'w') as f:
        f.write(content)


def update_module_init(module_path, module_name):
    """Update the module's main __init__.py file."""
    init_path = module_path / '__init__.py'
    
    content = f'''"""
Module initialization for {module_name}.

This module provides the functionality for {module_name}.
"""

from .api import router

__all__ = ["router"]
'''
    
    # Backup the original file if it exists
    if init_path.exists():
        backup_path = module_path / '__init__.py.bak'
        shutil.copy2(init_path, backup_path)
    
    with open(init_path, 'w') as f:
        f.write(content)


def move_endpoints_file(module_path):
    """Move the endpoints.py file to the api directory."""
    source_path = module_path / 'endpoints.py'
    target_path = module_path / 'api' / 'endpoints.py'
    
    if source_path.exists():
        # Create a backup
        backup_path = module_path / 'endpoints.py.bak'
        shutil.copy2(source_path, backup_path)
        
        # Read the content and update imports
        with open(source_path, 'r') as f:
            content = f.read()
        
        # Update relative imports
        content = re.sub(r'from \.' + module_path.name, r'from ..', content)
        
        # Write to the new location
        with open(target_path, 'w') as f:
            f.write(content)
        
        print(f"Moved endpoints.py to api/endpoints.py")
    else:
        print(f"No endpoints.py file found in {module_path}")


def move_config_file(module_path):
    """Move the config.py file to the config directory."""
    source_path = module_path / 'config.py'
    target_path = module_path / 'config' / 'settings.py'
    
    if source_path.exists():
        # Create a backup
        backup_path = module_path / 'config.py.bak'
        shutil.copy2(source_path, backup_path)
        
        # Read the content
        with open(source_path, 'r') as f:
            content = f.read()
        
        # Write to the new location
        with open(target_path, 'w') as f:
            f.write(content)
        
        print(f"Moved config.py to config/settings.py")
    else:
        print(f"No config.py file found in {module_path}")


def standardize_module(module_name):
    """Standardize the structure of a module."""
    base_path = Path(__file__).parent.parent
    module_path = base_path / 'modules' / module_name
    
    if not module_path.exists():
        print(f"Module {module_name} not found at {module_path}")
        return
    
    print(f"Standardizing module: {module_name}")
    
    # Create the directory structure
    create_directory_structure(module_path)
    
    # Move endpoints file
    move_endpoints_file(module_path)
    
    # Move config file
    move_config_file(module_path)
    
    # Create API init file
    create_api_init(module_path, module_name)
    
    # Update module init file
    update_module_init(module_path, module_name)
    
    print(f"Module {module_name} standardization completed.")
    print("Please review the changes and update any imports as needed.")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python standardize_module.py <module_name>")
        sys.exit(1)
    
    module_name = sys.argv[1]
    standardize_module(module_name)


if __name__ == '__main__':
    main()
