#!/usr/bin/env python
"""
Comprehensive validation script for Pydantic v2 schema compatibility.

This script imports and checks schema files across multiple modules
to ensure they are compatible with Pydantic v2 standards.
"""

import os
import sys
import inspect
import importlib
from typing import List, Dict, Any, Type, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pydantic import BaseModel, ConfigDict, field_validator

# Modules to check (path, module_name)
MODULES_TO_CHECK = [
    ('modules.auth.schemas', 'auth'),
    ('modules.billing.schemas', 'billing'),
    ('modules.billing.api.schemas', 'billing.api'),
    ('modules.radius.schemas', 'radius'),
    ('modules.monitoring.schemas', 'monitoring'),
    ('modules.service_activation.schemas', 'service_activation'),
    ('modules.reseller.schemas', 'reseller'),
    ('backend_core.schemas', 'backend_core')
]


def get_all_models_from_module(module) -> List[Type[BaseModel]]:
    """Get all Pydantic models from a module."""
    return [
        obj for _, obj in inspect.getmembers(module)
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj != BaseModel
    ]


def test_module_has_pydantic_models(module_name, module):
    """Test that the module has at least one Pydantic model."""
    models = get_all_models_from_module(module)
    if len(models) == 0:
        print(f"❌ Module {module_name} should have at least one Pydantic model")
        return False
    print(f"✅ Module {module_name} has {len(models)} Pydantic models")
    return True


def test_models_use_configdict(module_name, module):
    """Test that models use ConfigDict instead of class Config."""
    models = get_all_models_from_module(module)
    all_passed = True
    
    for model in models:
        # Skip models that don't need configuration
        if not hasattr(model, 'model_config') and not hasattr(model, 'Config'):
            continue
        
        # Check if model uses ConfigDict
        if hasattr(model, 'Config'):
            print(f"❌ Model {model.__name__} in {module_name} uses class Config instead of model_config = ConfigDict()")
            all_passed = False
            continue
    
    if all_passed:
        print(f"✅ All models in {module_name} use ConfigDict correctly")
    
    return all_passed


def test_models_use_from_attributes(module_name, module):
    """Test that models use from_attributes instead of orm_mode."""
    models = get_all_models_from_module(module)
    all_passed = True
    
    for model in models:
        # Skip models that don't need ORM mode
        if not hasattr(model, 'model_config'):
            continue
        
        # If model_config has from_attributes, it should be a boolean or inside ConfigDict
        if isinstance(model.model_config, dict) and 'from_attributes' in model.model_config:
            if not isinstance(model.model_config['from_attributes'], bool):
                print(f"❌ Model {model.__name__} in {module_name} should use from_attributes as a boolean")
                all_passed = False
                continue
        
        # Ensure orm_mode is not used
        if isinstance(model.model_config, dict) and 'orm_mode' in model.model_config:
            print(f"❌ Model {model.__name__} in {module_name} uses orm_mode instead of from_attributes")
            all_passed = False
            continue
    
    if all_passed:
        print(f"✅ All models in {module_name} use from_attributes correctly")
    
    return all_passed


def test_models_use_field_validator(module_name, module):
    """Test that models use field_validator instead of validator."""
    all_passed = True
    
    # Check module source code for validator usage
    try:
        module_source = inspect.getsource(module)
        if "from pydantic import validator" in module_source or "import validator" in module_source:
            print(f"❌ Module {module_name} imports validator instead of field_validator")
            all_passed = False
    except (TypeError, OSError):
        # Skip if we can't get the source
        pass
    
    # Check if any model methods use the @validator decorator
    models = get_all_models_from_module(module)
    for model in models:
        for name, method in inspect.getmembers(model, inspect.isfunction):
            try:
                source = inspect.getsource(method)
                if "@validator" in source:
                    print(f"❌ Method {name} in model {model.__name__} in {module_name} uses @validator instead of @field_validator")
                    all_passed = False
            except (TypeError, OSError):
                # Skip if we can't get the source
                pass
    
    if all_passed:
        print(f"✅ All models in {module_name} use field_validator correctly")
    
    return all_passed


def main():
    """Run all tests on all specified modules."""
    print("=== Testing Pydantic v2 Schema Compatibility ===")
    
    all_tests_passed = True
    
    for module_path, module_name in MODULES_TO_CHECK:
        print(f"\n=== Testing module: {module_name} ===")
        
        try:
            module = importlib.import_module(module_path)
            
            # Test that the module has Pydantic models
            has_models = test_module_has_pydantic_models(module_name, module)
            
            if has_models:
                # Test that models use ConfigDict
                configdict_test = test_models_use_configdict(module_name, module)
                
                # Test that models use from_attributes
                from_attr_test = test_models_use_from_attributes(module_name, module)
                
                # Test that models use field_validator
                field_val_test = test_models_use_field_validator(module_name, module)
                
                if not all([configdict_test, from_attr_test, field_val_test]):
                    all_tests_passed = False
            else:
                all_tests_passed = False
                
        except ImportError as e:
            print(f"❌ Could not import module {module_path}: {e}")
            all_tests_passed = False
            continue
    
    # Summary
    print("\n=== Summary ===")
    if all_tests_passed:
        print("✅ All tests passed! All schemas are compatible with Pydantic v2.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
