"""
Tests for the schemas in the Communications module.

This module contains tests for the Pydantic schemas defined in the
ISP Management Platform's Communications module.
"""

import pytest
from modules.communications.schemas import ExternalServiceCreate

def test_external_service_create_schema():
    """Test that the ExternalServiceCreate schema exists and can be instantiated."""
    # Create instance of ExternalServiceCreate
    service_data = ExternalServiceCreate(
        name="Test SMS Service",
        service_type="sms",
        config={
            "api_key": "test_key",
            "api_secret": "test_secret",
            "sender_id": "TEST"
        }
    )
    
    # Check attributes
    assert service_data.name == "Test SMS Service"
    assert service_data.service_type == "sms"
    assert service_data.config["api_key"] == "test_key"
    assert service_data.is_active is True  # Default value
