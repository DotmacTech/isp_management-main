"""
Configuration and fixtures for integration tests.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import sys
import pytest
from unittest.mock import MagicMock
from decimal import Decimal

# Create mock modules for dependencies
mock_logging = MagicMock()
mock_logging.get_logger = MagicMock(return_value=MagicMock())

# Create mock settings
mock_settings = MagicMock()
mock_settings.RADIUS_API_URL = "http://radius-api.example.com"
mock_settings.RADIUS_API_KEY = "test-radius-key"
mock_settings.BILLING_API_URL = "http://billing-api.example.com"
mock_settings.BILLING_API_KEY = "test-billing-key"
mock_settings.API_TIMEOUT = 10.0

# Create mock config module
mock_config = MagicMock()
mock_config.settings = mock_settings

# Create mock auth service
mock_auth_service = MagicMock()
mock_auth_service.get_password_hash = MagicMock(return_value="hashed_password")
mock_auth_service.verify_password = MagicMock(return_value=True)

# Create mock models
mock_models = MagicMock()

# Create mock db
mock_db = MagicMock()

# Create mock radius service
mock_radius_service = MagicMock()
mock_radius_service.RadiusService = MagicMock()

# Create mock backend core
mock_backend_core = MagicMock()
mock_backend_core.logging = mock_logging
mock_backend_core.models = mock_models
mock_backend_core.db = mock_db
mock_backend_core.config = mock_config
mock_backend_core.auth_service = mock_auth_service

# Create mock isp_management
mock_isp_management = MagicMock()
mock_isp_management.backend_core = mock_backend_core

# Add mock modules to sys.modules
sys.modules['isp_management'] = mock_isp_management
sys.modules['isp_management.backend_core'] = mock_backend_core
sys.modules['isp_management.backend_core.logging'] = mock_logging
sys.modules['isp_management.backend_core.models'] = mock_models
sys.modules['isp_management.backend_core.db'] = mock_db
sys.modules['isp_management.backend_core.config'] = mock_config
sys.modules['isp_management.backend_core.auth_service'] = mock_auth_service

# Create mock for radius module
sys.modules['modules'] = MagicMock()
sys.modules['modules.radius'] = MagicMock()
sys.modules['modules.radius.services'] = mock_radius_service

# Create mock tariff schemas
class MockTariffPlan:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockUserTariffPlan:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockUsageRecord:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Create mock tariff models
mock_tariff_models = {
    'TariffPlan': MockTariffPlan,
    'UserTariffPlan': MockUserTariffPlan,
    'UsageRecord': MockUsageRecord,
}

# Add mock tariff models to modules
mock_tariff_module = MagicMock()
for name, model in mock_tariff_models.items():
    setattr(mock_tariff_module, name, model)

sys.modules['modules.tariff.models'] = mock_tariff_module

@pytest.fixture
def mock_db_session():
    """Mock the database session."""
    mock_session = MagicMock()
    
    # Mock query results
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    
    # Mock add and commit
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock()
    
    return mock_session

@pytest.fixture
def mock_radius_integration():
    """Mock the RadiusIntegration class."""
    mock = MagicMock()
    mock.apply_policy = MagicMock(return_value={"status": "success"})
    mock.update_bandwidth = MagicMock(return_value={"status": "success"})
    mock.throttle_user = MagicMock(return_value={"status": "success"})
    return mock

@pytest.fixture
def mock_billing_integration():
    """Mock the BillingIntegration class."""
    mock = MagicMock()
    mock.create_invoice_item = MagicMock(return_value={"status": "success", "invoice_item_id": 123})
    mock.calculate_prorated_amount = MagicMock(return_value={
        "prorated_refund": Decimal("15.00"),
        "prorated_charge": Decimal("30.00"),
        "net_charge": Decimal("15.00")
    })
    return mock
