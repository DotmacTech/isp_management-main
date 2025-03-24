#!/usr/bin/env python3
"""
Standardize All Modules Script

This script applies the standardization process to all modules in the ISP Management Platform.
It uses the standardize_module.py script to standardize each module's structure.

Usage:
    python standardize_all_modules.py

"""

import os
import sys
import subprocess
from pathlib import Path

# Modules to standardize
# Note: monitoring is already standardized
MODULES = [
    'auth',
    'billing',
    'crm',
    'crm_ticketing',
    'customer',
    'network',
    'radius',
    'reseller',
    'service_activation',
    'tariff',
    'ai_chatbot',
    'business_intelligence',
    'communications',
    'config_management',
    'file_manager',
    'integration_management'
]

def main():
    """Main function to standardize all modules."""
    script_path = Path(__file__).parent / 'standardize_module.py'
    
    if not script_path.exists():
        print(f"Error: Standardization script not found at {script_path}")
        sys.exit(1)
    
    print(f"Starting standardization of all modules...")
    
    for module in MODULES:
        print(f"\n{'='*50}")
        print(f"Standardizing module: {module}")
        print(f"{'='*50}")
        
        # Run the standardization script for this module
        result = subprocess.run(
            [sys.executable, str(script_path), module],
            capture_output=True,
            text=True
        )
        
        # Print the output
        print(result.stdout)
        
        if result.stderr:
            print(f"Errors encountered:")
            print(result.stderr)
        
        print(f"Completed standardization for {module}")
    
    print("\nAll modules have been standardized.")
    print("Please review the changes and update any imports as needed.")
    print("Remember to test each module to ensure functionality is preserved.")

if __name__ == '__main__':
    main()
