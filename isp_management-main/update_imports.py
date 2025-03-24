#!/usr/bin/env python3
import os
import re

def update_imports_in_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Replace imports
    updated_content = re.sub(
        r'from backend_core\.', 
        'from isp_management.backend_core.', 
        content
    )
    updated_content = re.sub(
        r'from modules\.', 
        'from isp_management.modules.', 
        updated_content
    )
    
    if content != updated_content:
        with open(file_path, 'w') as file:
            file.write(updated_content)
        print(f"Updated imports in {file_path}")

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports_in_file(file_path)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modules_dir = os.path.join(base_dir, 'modules')
    backend_core_dir = os.path.join(base_dir, 'backend_core')
    tests_dir = os.path.join(base_dir, 'tests')
    
    process_directory(modules_dir)
    process_directory(backend_core_dir)
    process_directory(tests_dir)
    
    print("Import paths updated successfully!")
