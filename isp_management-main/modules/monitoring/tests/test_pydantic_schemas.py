"""
Tests for Pydantic v2 schema compatibility.

This module tests that all schema models in the monitoring module
are compatible with Pydantic v2, particularly checking:
1. ConfigDict usage instead of class Config
2. from_attributes instead of orm_mode
3. field_validator instead of validator
"""

import pytest
import inspect
from typing import List, Dict, Any, Type, Optional

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


@pytest.mark.parametrize("module", [
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
])
def test_module_has_pydantic_models(module):
    """Test that each module has at least one Pydantic model."""
    models = get_all_models_from_module(module)
    assert len(models) > 0, f"Module {module.__name__} should have at least one Pydantic model"


@pytest.mark.parametrize("module", [
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
])
def test_models_use_configdict(module):
    """Test that models use ConfigDict instead of class Config."""
    models = get_all_models_from_module(module)
    
    for model in models:
        # Skip models that don't need ORM mode
        if not hasattr(model, 'model_config') and not hasattr(model, 'Config'):
            continue
        
        # Check if model uses ConfigDict
        if hasattr(model, 'Config'):
            assert False, f"Model {model.__name__} in {module.__name__} uses class Config instead of model_config = ConfigDict()"
        
        if hasattr(model, 'model_config'):
            assert isinstance(model.model_config, dict), f"Model {model.__name__} in {module.__name__} should use model_config = ConfigDict()"


def test_models_use_from_attributes():
    """Test that models use from_attributes instead of orm_mode."""
    # Get all models from all modules
    all_modules = [
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
    
    for module in all_modules:
        models = get_all_models_from_module(module)
        
        for model in models:
            # Skip models that don't need ORM mode
            if not hasattr(model, 'model_config'):
                continue
            
            # If model_config has from_attributes, it should be a boolean
            if 'from_attributes' in model.model_config:
                assert isinstance(model.model_config['from_attributes'], bool), \
                    f"Model {model.__name__} in {module.__name__} should use from_attributes as a boolean"
            
            # Ensure orm_mode is not used
            assert 'orm_mode' not in model.model_config, \
                f"Model {model.__name__} in {module.__name__} uses orm_mode instead of from_attributes"


def test_models_use_field_validator():
    """Test that models use field_validator instead of validator."""
    # Get all models from all modules
    all_modules = [
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
    
    for module in all_modules:
        # Check module source code for validator usage
        module_source = inspect.getsource(module)
        assert "from pydantic import validator" not in module_source, \
            f"Module {module.__name__} imports validator instead of field_validator"
        
        # Check if any model methods use the @validator decorator
        models = get_all_models_from_module(module)
        for model in models:
            for name, method in inspect.getmembers(model, inspect.isfunction):
                source = inspect.getsource(method)
                assert "@validator" not in source, \
                    f"Method {name} in model {model.__name__} in {module.__name__} uses @validator instead of @field_validator"
