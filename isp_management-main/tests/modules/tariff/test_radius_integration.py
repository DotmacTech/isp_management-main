"""
Tests for the RADIUS integration in the Tariff Enforcement Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from modules.tariff.radius_integration import RadiusIntegration


@pytest.fixture
def radius_integration():
    """Fixture for RadiusIntegration instance."""
    with patch('modules.tariff.radius_integration.settings') as mock_settings:
        mock_settings.RADIUS_API_URL = "http://radius-api.test"
        mock_settings.RADIUS_API_KEY = "test-api-key"
        mock_settings.RADIUS_API_TIMEOUT = 5.0
        
        integration = RadiusIntegration()
        yield integration


@pytest.mark.asyncio
async def test_apply_policy_success(radius_integration):
    """Test applying a RADIUS policy successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {"status": "success", "message": "Policy applied"}
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.apply_policy("testuser", 123)
        
        # Verify the result
        assert result == {"status": "success", "message": "Policy applied"}
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://radius-api.test/users/testuser/policy",
            headers=radius_integration.headers,
            json={"policy_id": 123}
        )


@pytest.mark.asyncio
async def test_apply_policy_http_error(radius_integration):
    """Test applying a RADIUS policy with HTTP error."""
    # Mock the httpx AsyncClient
    mock_error = httpx.HTTPStatusError(
        "Error",
        request=MagicMock(),
        response=MagicMock()
    )
    mock_error.response.status_code = 404
    mock_error.response.text = "User not found"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=mock_error
        )
        
        # Verify that HTTPException is raised
        with pytest.raises(HTTPException) as excinfo:
            await radius_integration.apply_policy("testuser", 123)
        
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_bandwidth_limits_success(radius_integration):
    """Test updating bandwidth limits successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "status": "success", 
        "message": "Bandwidth limits updated"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.put = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.update_bandwidth_limits("testuser", 100, 50)
        
        # Verify the result
        assert result == {"status": "success", "message": "Bandwidth limits updated"}
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.put.assert_called_once_with(
            "http://radius-api.test/users/testuser/bandwidth",
            headers=radius_integration.headers,
            json={"download_speed": 100, "upload_speed": 50}
        )


@pytest.mark.asyncio
async def test_throttle_user_success(radius_integration):
    """Test throttling a user successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "status": "success", 
        "message": "User throttled"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.throttle_user("testuser", 10, 5)
        
        # Verify the result
        assert result == {"status": "success", "message": "User throttled"}
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://radius-api.test/users/testuser/throttle",
            headers=radius_integration.headers,
            json={
                "download_speed": 10, 
                "upload_speed": 5,
                "reason": "Data cap exceeded"
            }
        )


@pytest.mark.asyncio
async def test_unthrottle_user_success(radius_integration):
    """Test unthrottling a user successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "status": "success", 
        "message": "User unthrottled"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.unthrottle_user("testuser")
        
        # Verify the result
        assert result == {"status": "success", "message": "User unthrottled"}
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://radius-api.test/users/testuser/unthrottle",
            headers=radius_integration.headers,
            json={}
        )


@pytest.mark.asyncio
async def test_get_user_policy_success(radius_integration):
    """Test getting a user's policy successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "policy_id": 123,
        "policy_name": "Premium",
        "download_speed": 100,
        "upload_speed": 50
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.get_user_policy("testuser")
        
        # Verify the result
        assert result["policy_id"] == 123
        assert result["policy_name"] == "Premium"
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
            "http://radius-api.test/users/testuser/policy",
            headers=radius_integration.headers
        )


@pytest.mark.asyncio
async def test_get_user_usage_success(radius_integration):
    """Test getting a user's usage successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "total_download": 1024,
        "total_upload": 512,
        "total_usage": 1536
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await radius_integration.get_user_usage(
            "testuser", 
            start_date="2023-01-01", 
            end_date="2023-01-31"
        )
        
        # Verify the result
        assert result["total_download"] == 1024
        assert result["total_upload"] == 512
        assert result["total_usage"] == 1536
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
            "http://radius-api.test/users/testuser/usage",
            headers=radius_integration.headers,
            params={"start_date": "2023-01-01", "end_date": "2023-01-31"}
        )


@pytest.mark.asyncio
async def test_sync_policy_with_tariff_plan_normal(radius_integration):
    """Test syncing policy with tariff plan in normal mode."""
    # Mock the apply_policy and update_bandwidth_limits methods
    radius_integration.apply_policy = AsyncMock()
    radius_integration.update_bandwidth_limits = AsyncMock(
        return_value={"status": "success"}
    )
    
    tariff_plan = {
        "name": "Premium Plan",
        "radius_policy_id": 123,
        "download_speed": 100,
        "upload_speed": 50,
        "throttled_radius_policy_id": 456,
        "throttle_speed_download": 10,
        "throttle_speed_upload": 5
    }
    
    result = await radius_integration.sync_policy_with_tariff_plan(
        "testuser", 
        tariff_plan,
        is_throttled=False
    )
    
    # Verify the method calls
    radius_integration.apply_policy.assert_called_once_with("testuser", 123)
    radius_integration.update_bandwidth_limits.assert_called_once_with(
        "testuser", 100, 50
    )
    
    # Verify the result
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_sync_policy_with_tariff_plan_throttled(radius_integration):
    """Test syncing policy with tariff plan in throttled mode."""
    # Mock the apply_policy and update_bandwidth_limits methods
    radius_integration.apply_policy = AsyncMock()
    radius_integration.update_bandwidth_limits = AsyncMock(
        return_value={"status": "success"}
    )
    
    tariff_plan = {
        "name": "Premium Plan",
        "radius_policy_id": 123,
        "download_speed": 100,
        "upload_speed": 50,
        "throttled_radius_policy_id": 456,
        "throttle_speed_download": 10,
        "throttle_speed_upload": 5
    }
    
    result = await radius_integration.sync_policy_with_tariff_plan(
        "testuser", 
        tariff_plan,
        is_throttled=True
    )
    
    # Verify the method calls
    radius_integration.apply_policy.assert_called_once_with("testuser", 456)
    radius_integration.update_bandwidth_limits.assert_called_once_with(
        "testuser", 10, 5
    )
    
    # Verify the result
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_bulk_sync_policies_success(radius_integration):
    """Test bulk syncing policies successfully."""
    # Mock the sync_policy_with_tariff_plan method
    radius_integration.sync_policy_with_tariff_plan = AsyncMock(
        return_value={"status": "success"}
    )
    
    user_plans = [
        {
            "user_id": 1,
            "username": "user1",
            "tariff_plan": {
                "name": "Basic Plan",
                "radius_policy_id": 101,
                "download_speed": 50,
                "upload_speed": 25
            },
            "is_throttled": False
        },
        {
            "user_id": 2,
            "username": "user2",
            "tariff_plan": {
                "name": "Premium Plan",
                "radius_policy_id": 102,
                "download_speed": 100,
                "upload_speed": 50
            },
            "is_throttled": True
        }
    ]
    
    result = await radius_integration.bulk_sync_policies(user_plans)
    
    # Verify the method calls
    assert radius_integration.sync_policy_with_tariff_plan.call_count == 2
    
    # Verify the result
    assert result["total"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0
    assert len(result["failures"]) == 0


@pytest.mark.asyncio
async def test_bulk_sync_policies_with_failures(radius_integration):
    """Test bulk syncing policies with some failures."""
    # Mock the sync_policy_with_tariff_plan method to succeed for first user and fail for second
    async def mock_sync(*args, **kwargs):
        if args[0] == "user1":
            return {"status": "success"}
        else:
            raise Exception("Test error")
    
    radius_integration.sync_policy_with_tariff_plan = AsyncMock(side_effect=mock_sync)
    
    user_plans = [
        {
            "user_id": 1,
            "username": "user1",
            "tariff_plan": {
                "name": "Basic Plan",
                "radius_policy_id": 101,
                "download_speed": 50,
                "upload_speed": 25
            },
            "is_throttled": False
        },
        {
            "user_id": 2,
            "username": "user2",
            "tariff_plan": {
                "name": "Premium Plan",
                "radius_policy_id": 102,
                "download_speed": 100,
                "upload_speed": 50
            },
            "is_throttled": True
        }
    ]
    
    result = await radius_integration.bulk_sync_policies(user_plans)
    
    # Verify the result
    assert result["total"] == 2
    assert result["successful"] == 1
    assert result["failed"] == 1
    assert len(result["failures"]) == 1
    assert result["failures"][0]["user_id"] == 2
    assert result["failures"][0]["username"] == "user2"
    assert "Test error" in result["failures"][0]["error"]
