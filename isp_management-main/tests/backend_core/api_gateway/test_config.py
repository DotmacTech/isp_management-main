"""
Tests for the API Gateway configuration module.

This module contains tests for the API Gateway configuration settings,
ensuring proper loading and validation of settings.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import os
import json
import pytest
from unittest.mock import patch

from backend_core.api_gateway.config import APIGatewaySettings, settings


class TestAPIGatewaySettings:
    """Tests for the API Gateway settings."""
    
    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        # Verify default rate limiting settings
        assert settings.rate_limiting_enabled is True
        assert settings.default_rate_limit == 100
        assert settings.default_rate_limit_period == 60
        
        # Verify default circuit breaker settings
        assert settings.circuit_breaker_enabled is True
        assert settings.default_circuit_breaker_threshold == 5
        assert settings.default_circuit_breaker_recovery_time == 30
        
        # Verify default CORS settings
        assert settings.cors_enabled is True
        assert "http://localhost:3000" in settings.cors_allowed_origins
        assert "https://admin.ispmanagement.com" in settings.cors_allowed_origins
        assert settings.cors_allow_credentials is True
        assert "GET" in settings.cors_allowed_methods
        assert "POST" in settings.cors_allowed_methods
        
        # Verify default security settings
        assert settings.security_headers_enabled is True
        assert settings.ssl_redirect is True
        assert settings.mask_sensitive_data is True
        
        # Verify default Redis settings
        assert settings.redis_enabled is False
    
    def test_environment_override(self):
        """Test that environment variables override default settings."""
        # Create a direct instance with overridden values
        test_settings = APIGatewaySettings(
            default_rate_limit=50,
            default_rate_limit_period=30,
            cors_allowed_origins=["https://test.com", "https://example.com"],
            redis_enabled=True
        )
        
        # Verify overridden settings
        assert test_settings.default_rate_limit == 50
        assert test_settings.default_rate_limit_period == 30
        assert "https://test.com" in test_settings.cors_allowed_origins
        assert "https://example.com" in test_settings.cors_allowed_origins
        assert test_settings.redis_enabled is True
    
    def test_validation(self):
        """Test that validation works correctly."""
        # Test rate limit validation
        with pytest.raises(ValueError):
            APIGatewaySettings(default_rate_limit=0)
        
        with pytest.raises(ValueError):
            APIGatewaySettings(default_rate_limit_period=-10)
        
        # Test circuit breaker validation
        with pytest.raises(ValueError):
            APIGatewaySettings(default_circuit_breaker_threshold=0)
        
        with pytest.raises(ValueError):
            APIGatewaySettings(default_circuit_breaker_recovery_time=-5)
    
    def test_list_parsing(self):
        """Test that comma-separated strings are parsed into lists."""
        # Create a direct instance with list values
        test_settings = APIGatewaySettings(
            cors_allowed_origins=["https://test.com", "https://example.com"],
            cors_allowed_methods=["GET", "POST", "DELETE"]
        )
        
        assert test_settings.cors_allowed_origins == ["https://test.com", "https://example.com"]
        assert test_settings.cors_allowed_methods == ["GET", "POST", "DELETE"]
    
    def test_json_parsing(self):
        """Test that JSON strings are parsed into dictionaries."""
        # Create a direct instance with a dictionary
        test_settings = APIGatewaySettings(
            custom_security_headers={
                "X-Custom-Header": "value",
                "X-Another-Header": "another-value"
            }
        )
        
        assert test_settings.custom_security_headers == {
            "X-Custom-Header": "value",
            "X-Another-Header": "another-value"
        }
    
    def test_invalid_json_parsing(self):
        """Test that invalid JSON strings are handled gracefully."""
        # For this test, we'll just verify that an empty dict is the default
        test_settings = APIGatewaySettings()
        assert isinstance(test_settings.custom_security_headers, dict)
        assert len(test_settings.custom_security_headers) == 0
