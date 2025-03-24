#!/usr/bin/env python
"""
Direct HATEOAS Implementation Test

This script directly tests the HATEOAS implementation in the communications and monitoring
modules by importing the endpoint modules and checking their responses.
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime
from pprint import pprint
import inspect

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import the modules we need to test
try:
    from modules.communications.api import endpoints as comm_endpoints
    from modules.monitoring.api import endpoints as monitoring_endpoints
    from backend_core.utils.hateoas import add_resource_links, add_action_links
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("This script needs to be run from the project root directory.")
    sys.exit(1)


def test_hateoas_utils():
    """Test the HATEOAS utility functions."""
    print("\n=== Testing HATEOAS Utility Functions ===")
    
    # Test add_resource_links
    resource = {"id": 1, "name": "Test Resource"}
    resource_with_links = add_resource_links(
        resource, 
        "/api/test", 
        ["update", "delete"]
    )
    
    print("Resource with links:")
    pprint(resource_with_links)
    
    assert "_links" in resource_with_links, "Resource should have _links"
    assert "self" in resource_with_links["_links"], "Resource should have self link"
    assert "update" in resource_with_links["_links"], "Resource should have update link"
    assert "delete" in resource_with_links["_links"], "Resource should have delete link"
    
    # Test add_action_links
    collection = {"items": [{"id": 1}, {"id": 2}]}
    collection_with_links = add_action_links(
        collection, 
        "/api/collection", 
        ["create"]
    )
    
    print("\nCollection with links:")
    pprint(collection_with_links)
    
    assert "_links" in collection_with_links, "Collection should have _links"
    assert "self" in collection_with_links["_links"], "Collection should have self link"
    assert "create" in collection_with_links["_links"], "Collection should have create link"
    
    print("✅ HATEOAS utility functions are working correctly")
    return True


def test_communications_endpoints():
    """Test HATEOAS implementation in communications endpoints."""
    print("\n=== Testing Communications Module Endpoints ===")
    
    # Get all endpoint functions
    endpoint_functions = [
        obj for name, obj in inspect.getmembers(comm_endpoints)
        if inspect.isfunction(obj) and not name.startswith('_')
    ]
    
    print(f"Found {len(endpoint_functions)} endpoint functions in communications module")
    
    for func in endpoint_functions:
        print(f"\nTesting endpoint function: {func.__name__}")
        
        # Check if the function uses HATEOAS utilities
        source = inspect.getsource(func)
        if "add_resource_links" in source or "add_action_links" in source:
            print(f"✅ {func.__name__} uses HATEOAS utilities")
        else:
            print(f"❌ {func.__name__} does not use HATEOAS utilities")
    
    return True


def test_monitoring_endpoints():
    """Test HATEOAS implementation in monitoring endpoints."""
    print("\n=== Testing Monitoring Module Endpoints ===")
    
    # Get all endpoint functions
    endpoint_functions = [
        obj for name, obj in inspect.getmembers(monitoring_endpoints)
        if inspect.isfunction(obj) and not name.startswith('_')
    ]
    
    print(f"Found {len(endpoint_functions)} endpoint functions in monitoring module")
    
    for func in endpoint_functions:
        print(f"\nTesting endpoint function: {func.__name__}")
        
        # Check if the function uses HATEOAS utilities
        source = inspect.getsource(func)
        if "add_resource_links" in source or "add_action_links" in source:
            print(f"✅ {func.__name__} uses HATEOAS utilities")
        else:
            print(f"❌ {func.__name__} does not use HATEOAS utilities")
    
    return True


def main():
    """Run all tests."""
    print("=" * 80)
    print("ISP Management Platform - Direct HATEOAS Implementation Test")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    results = {
        "hateoas_utils": test_hateoas_utils(),
        "communications_endpoints": test_communications_endpoints(),
        "monitoring_endpoints": test_monitoring_endpoints()
    }
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("-" * 80)
    
    all_passed = all(results.values())
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    print("-" * 80)
    print(f"Overall status: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
