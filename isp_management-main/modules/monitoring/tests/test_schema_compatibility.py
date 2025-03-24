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

# Import all schema modules
from modules.monitoring.schemas import (
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
)


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


def test_create_model_instances():
    """Test that we can create instances of all models."""
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
    
    # Test a few specific models that we know should work
    # AlertSummary from alert.py
    alert_summary = alert.AlertSummary(
        total=10,
        active=5,
        acknowledged=2,
        resolved=2,
        closed=1,
        info=3,
        warning=4,
        error=2,
        critical=1,
        last_24h=8,
        last_7d=10
    )
    assert alert_summary.total == 10
    
    # PaginatedResponse from dashboard.py
    paginated_response = dashboard.PaginatedResponse(
        items=[],
        total=0,
        page=1,
        size=10,
        pages=0
    )
    assert paginated_response.page == 1
