"""
Tests for the Device Service in the Network Management Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from modules.network.models import Device, DeviceType, DeviceStatus
from modules.network.services import DeviceService
from modules.network.utils import test_device_connectivity


@pytest.fixture
def device_service():
    """Return a DeviceService instance."""
    return DeviceService()


@pytest.fixture
def mock_session():
    """Return a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_device(device_service, mock_session):
    """Test creating a device."""
    # Mock the execute method to return a result proxy with no rows
    mock_session.execute.return_value.scalars().first.return_value = None
    
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = 1
    mock_device.name = "Test Router"
    mock_device.hostname = "router1.test.com"
    mock_device.ip_address = "192.168.1.1"
    mock_device.device_type = DeviceType.ROUTER
    mock_device.status = DeviceStatus.ACTIVE
    mock_device.created_at = datetime.now()
    mock_device.updated_at = datetime.now()
    
    # Mock the add method
    mock_session.add = MagicMock()
    mock_session.add.return_value = None
    
    # Mock the flush method to set the id
    mock_session.flush = AsyncMock()
    
    # Patch the Device constructor to return our mock device
    with patch('modules.network.services.Device', return_value=mock_device):
        # Call create_device
        result = await device_service.create_device(
            session=mock_session,
            name="Test Router",
            hostname="router1.test.com",
            ip_address="192.168.1.1",
            device_type=DeviceType.ROUTER
        )
        
        # Check that the device was added to the session
        mock_session.add.assert_called_once()
        
        # Check that the returned device is our mock device
        assert result == mock_device
        assert result.name == "Test Router"
        assert result.hostname == "router1.test.com"
        assert result.ip_address == "192.168.1.1"
        assert result.device_type == DeviceType.ROUTER
        assert result.status == DeviceStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_device_duplicate_name(device_service, mock_session):
    """Test creating a device with a duplicate name."""
    # Mock the execute method to return a result proxy with a row
    mock_existing_device = MagicMock(spec=Device)
    mock_session.execute.return_value.scalars().first.return_value = mock_existing_device
    
    # Call create_device and expect an exception
    with pytest.raises(Exception) as excinfo:
        await device_service.create_device(
            session=mock_session,
            name="Test Router",
            hostname="router1.test.com",
            ip_address="192.168.1.1",
            device_type=DeviceType.ROUTER
        )
    
    # Check the exception message
    assert "Device with name 'Test Router' already exists" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_device(device_service, mock_session):
    """Test getting a device by ID."""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = 1
    mock_device.name = "Test Router"
    
    # Mock the execute method to return our mock device
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_device
    
    # Call get_device
    result = await device_service.get_device(mock_session, 1)
    
    # Check that execute was called with a select statement
    mock_session.execute.assert_called_once()
    
    # Check that the returned device is our mock device
    assert result == mock_device
    assert result.id == 1
    assert result.name == "Test Router"


@pytest.mark.asyncio
async def test_get_device_not_found(device_service, mock_session):
    """Test getting a device that doesn't exist."""
    # Mock the execute method to return None
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Call get_device and expect an exception
    with pytest.raises(Exception) as excinfo:
        await device_service.get_device(mock_session, 1)
    
    # Check the exception message
    assert "Device with ID 1 not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_update_device(device_service, mock_session):
    """Test updating a device."""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = 1
    mock_device.name = "Test Router"
    mock_device.hostname = "router1.test.com"
    mock_device.ip_address = "192.168.1.1"
    
    # Mock the execute method to return our mock device
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_device
    
    # Call update_device
    result = await device_service.update_device(
        session=mock_session,
        device_id=1,
        name="Updated Router",
        hostname="updated.test.com"
    )
    
    # Check that the device was updated
    assert result.name == "Updated Router"
    assert result.hostname == "updated.test.com"
    assert result.ip_address == "192.168.1.1"  # Should not have changed


@pytest.mark.asyncio
async def test_delete_device(device_service, mock_session):
    """Test deleting a device."""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = 1
    
    # Mock the execute method to return our mock device
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_device
    
    # Call delete_device
    await device_service.delete_device(mock_session, 1)
    
    # Check that delete was called
    mock_session.delete.assert_called_once_with(mock_device)


@pytest.mark.asyncio
async def test_get_device_status(device_service, mock_session):
    """Test getting device status."""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = 1
    mock_device.name = "Test Router"
    mock_device.hostname = "router1.test.com"
    mock_device.ip_address = "192.168.1.1"
    mock_device.status = DeviceStatus.ACTIVE
    mock_device.last_seen = datetime.now()
    
    # Mock the execute method to return our mock device
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_device
    
    # Mock the test_device_connectivity function
    with patch('modules.network.services.test_device_connectivity', return_value=True):
        # Call get_device_status
        result = await device_service.get_device_status(mock_session, 1)
        
        # Check the result
        assert result["id"] == 1
        assert result["name"] == "Test Router"
        assert result["status"] == DeviceStatus.ACTIVE
        assert "last_seen" in result
        assert result["reachable"] is True


@pytest.mark.asyncio
async def test_get_devices(device_service, mock_session):
    """Test getting a list of devices."""
    # Create mock devices
    mock_device1 = MagicMock(spec=Device)
    mock_device1.id = 1
    mock_device1.name = "Router 1"
    mock_device1.device_type = DeviceType.ROUTER
    
    mock_device2 = MagicMock(spec=Device)
    mock_device2.id = 2
    mock_device2.name = "Switch 1"
    mock_device2.device_type = DeviceType.SWITCH
    
    # Mock the execute method to return our mock devices
    mock_session.execute.return_value.scalars().all.return_value = [mock_device1, mock_device2]
    
    # Call get_devices
    result = await device_service.get_devices(mock_session)
    
    # Check the result
    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Router 1"
    assert result[1].id == 2
    assert result[1].name == "Switch 1"


@pytest.mark.asyncio
async def test_get_devices_with_filters(device_service, mock_session):
    """Test getting a list of devices with filters."""
    # Create mock devices
    mock_device1 = MagicMock(spec=Device)
    mock_device1.id = 1
    mock_device1.name = "Router 1"
    mock_device1.device_type = DeviceType.ROUTER
    
    # Mock the execute method to return our mock devices
    mock_session.execute.return_value.scalars().all.return_value = [mock_device1]
    
    # Call get_devices with filters
    result = await device_service.get_devices(
        session=mock_session,
        device_type=DeviceType.ROUTER,
        status=DeviceStatus.ACTIVE
    )
    
    # Check the result
    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].name == "Router 1"
    assert result[0].device_type == DeviceType.ROUTER
