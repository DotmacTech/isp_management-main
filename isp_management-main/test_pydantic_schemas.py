#!/usr/bin/env python
"""
Standalone script to test Pydantic v2 schema compatibility.

This script directly imports and checks all schema files in the monitoring module
to ensure they are compatible with Pydantic v2.
"""

import os
import sys
import inspect
from typing import List, Dict, Any, Type, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pydantic import BaseModel, ConfigDict, field_validator

# Import all schema modules directly
from modules.monitoring.schemas import alert
from modules.monitoring.schemas import alert_configuration
from modules.monitoring.schemas import alert_history
from modules.monitoring.schemas import dashboard
from modules.monitoring.schemas import log_retention
from modules.monitoring.schemas import log_retention_policy
from modules.monitoring.schemas import log_search
from modules.monitoring.schemas import metric_record
from modules.monitoring.schemas import metric_search
from modules.monitoring.schemas import network_node
from modules.monitoring.schemas import pagination
from modules.monitoring.schemas import service_availability
from modules.monitoring.schemas import service_log
from modules.monitoring.schemas import system_health
from modules.monitoring.schemas import system_metric


def get_all_models_from_module(module) -> List[Type[BaseModel]]:
    """Get all Pydantic models from a module."""
    return [
        obj for _, obj in inspect.getmembers(module)
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj != BaseModel
    ]


def test_module_has_pydantic_models(module):
    """Test that each module has at least one Pydantic model."""
    models = get_all_models_from_module(module)
    if len(models) == 0:
        print(f"❌ Module {module.__name__} should have at least one Pydantic model")
        return False
    print(f"✅ Module {module.__name__} has {len(models)} Pydantic models")
    return True


def test_models_use_configdict(module):
    """Test that models use ConfigDict instead of class Config."""
    models = get_all_models_from_module(module)
    all_passed = True
    
    for model in models:
        # Skip models that don't need ORM mode
        if not hasattr(model, 'model_config') and not hasattr(model, 'Config'):
            continue
        
        # Check if model uses ConfigDict
        if hasattr(model, 'Config'):
            print(f"❌ Model {model.__name__} in {module.__name__} uses class Config instead of model_config = ConfigDict()")
            all_passed = False
            continue
        
        if hasattr(model, 'model_config'):
            if not isinstance(model.model_config, dict):
                print(f"❌ Model {model.__name__} in {module.__name__} should use model_config = ConfigDict()")
                all_passed = False
                continue
    
    if all_passed:
        print(f"✅ All models in {module.__name__} use ConfigDict correctly")
    
    return all_passed


def test_models_use_from_attributes(module):
    """Test that models use from_attributes instead of orm_mode."""
    models = get_all_models_from_module(module)
    all_passed = True
    
    for model in models:
        # Skip models that don't need ORM mode
        if not hasattr(model, 'model_config'):
            continue
        
        # If model_config has from_attributes, it should be a boolean
        if 'from_attributes' in model.model_config:
            if not isinstance(model.model_config['from_attributes'], bool):
                print(f"❌ Model {model.__name__} in {module.__name__} should use from_attributes as a boolean")
                all_passed = False
                continue
        
        # Ensure orm_mode is not used
        if 'orm_mode' in model.model_config:
            print(f"❌ Model {model.__name__} in {module.__name__} uses orm_mode instead of from_attributes")
            all_passed = False
            continue
    
    if all_passed:
        print(f"✅ All models in {module.__name__} use from_attributes correctly")
    
    return all_passed


def test_models_use_field_validator(module):
    """Test that models use field_validator instead of validator."""
    all_passed = True
    
    # Check module source code for validator usage
    module_source = inspect.getsource(module)
    if "from pydantic import validator" in module_source:
        print(f"❌ Module {module.__name__} imports validator instead of field_validator")
        all_passed = False
    
    # Check if any model methods use the @validator decorator
    models = get_all_models_from_module(module)
    for model in models:
        for name, method in inspect.getmembers(model, inspect.isfunction):
            source = inspect.getsource(method)
            if "@validator" in source:
                print(f"❌ Method {name} in model {model.__name__} in {module.__name__} uses @validator instead of @field_validator")
                all_passed = False
    
    if all_passed:
        print(f"✅ All models in {module.__name__} use field_validator correctly")
    
    return all_passed


def main():
    """Run all tests."""
    modules = [
        alert,
        alert_configuration,
        alert_history,
        dashboard,
        log_retention,
        log_retention_policy,
        log_search,
        metric_record,
        metric_search,
        network_node,
        pagination,
        service_availability,
        service_log,
        system_health,
        system_metric
    ]
    
    print("=== Testing Pydantic v2 Schema Compatibility ===")
    
    # Test that each module has Pydantic models
    print("\n=== Testing that each module has Pydantic models ===")
    all_modules_have_models = all(test_module_has_pydantic_models(module) for module in modules)
    
    # Test that models use ConfigDict
    print("\n=== Testing that models use ConfigDict ===")
    all_models_use_configdict = all(test_models_use_configdict(module) for module in modules)
    
    # Test that models use from_attributes
    print("\n=== Testing that models use from_attributes ===")
    all_models_use_from_attributes = all(test_models_use_from_attributes(module) for module in modules)
    
    # Test that models use field_validator
    print("\n=== Testing that models use field_validator ===")
    all_models_use_field_validator = all(test_models_use_field_validator(module) for module in modules)
    
    # Summary
    print("\n=== Summary ===")
    if all_modules_have_models and all_models_use_configdict and all_models_use_from_attributes and all_models_use_field_validator:
        print("✅ All tests passed! All schemas are compatible with Pydantic v2.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
