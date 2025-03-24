"""
Tests for the IP Pool Service in the Network Management Module.
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

from modules.network.models import IPPool, IPPoolType, IPAddress, IPAddressStatus
from modules.network.ip_pool_service import IPPoolService


@pytest.fixture
def ip_pool_service():
    """Return an IPPoolService instance."""
    return IPPoolService()


@pytest.fixture
def mock_session():
    """Return a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_pool(ip_pool_service, mock_session):
    """Test creating an IP pool."""
    # Mock the execute method to return a result proxy with no rows
    mock_session.execute.return_value.scalars().first.return_value = None
    
    # Create a mock IP pool
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    mock_pool.network = "192.168.1.0/24"
    mock_pool.pool_type = IPPoolType.CUSTOMER
    mock_pool.gateway = "192.168.1.1"
    mock_pool.dns_servers = ["8.8.8.8", "8.8.4.4"]
    mock_pool.is_active = True
    mock_pool.created_at = datetime.now()
    mock_pool.updated_at = datetime.now()
    
    # Mock the add method
    mock_session.add = MagicMock()
    mock_session.add.return_value = None
    
    # Mock the flush method to set the id
    mock_session.flush = AsyncMock()
    
    # Patch the IPPool constructor to return our mock pool
    with patch('modules.network.ip_pool_service.IPPool', return_value=mock_pool):
        # Call create_pool
        result = await ip_pool_service.create_pool(
            session=mock_session,
            name="Test Pool",
            network="192.168.1.0/24",
            pool_type=IPPoolType.CUSTOMER,
            gateway="192.168.1.1",
            dns_servers=["8.8.8.8", "8.8.4.4"]
        )
        
        # Check that the pool was added to the session
        mock_session.add.assert_called_once()
        
        # Check that the returned pool is our mock pool
        assert result == mock_pool
        assert result.name == "Test Pool"
        assert result.network == "192.168.1.0/24"
        assert result.pool_type == IPPoolType.CUSTOMER
        assert result.gateway == "192.168.1.1"
        assert result.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert result.is_active is True


@pytest.mark.asyncio
async def test_create_pool_duplicate_name(ip_pool_service, mock_session):
    """Test creating an IP pool with a duplicate name."""
    # Mock the execute method to return a result proxy with a row
    mock_existing_pool = MagicMock(spec=IPPool)
    mock_session.execute.return_value.scalars().first.return_value = mock_existing_pool
    
    # Call create_pool and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.create_pool(
            session=mock_session,
            name="Test Pool",
            network="192.168.1.0/24",
            pool_type=IPPoolType.CUSTOMER
        )
    
    # Check the exception message
    assert "IP pool with name 'Test Pool' already exists" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_pool_invalid_network(ip_pool_service, mock_session):
    """Test creating an IP pool with an invalid network."""
    # Mock the execute method to return a result proxy with no rows
    mock_session.execute.return_value.scalars().first.return_value = None
    
    # Call create_pool with an invalid network and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.create_pool(
            session=mock_session,
            name="Test Pool",
            network="invalid_network",
            pool_type=IPPoolType.CUSTOMER
        )
    
    # Check the exception message
    assert "Invalid network format" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_pool(ip_pool_service, mock_session):
    """Test getting an IP pool by ID."""
    # Create a mock IP pool
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    
    # Mock the execute method to return our mock pool
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_pool
    
    # Call get_pool
    result = await ip_pool_service.get_pool(mock_session, 1)
    
    # Check that execute was called with a select statement
    mock_session.execute.assert_called_once()
    
    # Check that the returned pool is our mock pool
    assert result == mock_pool
    assert result.id == 1
    assert result.name == "Test Pool"


@pytest.mark.asyncio
async def test_get_pool_not_found(ip_pool_service, mock_session):
    """Test getting an IP pool that doesn't exist."""
    # Mock the execute method to return None
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Call get_pool and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.get_pool(mock_session, 1)
    
    # Check the exception message
    assert "IP pool with ID 1 not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_pools(ip_pool_service, mock_session):
    """Test getting a list of IP pools."""
    # Create mock IP pools
    mock_pool1 = MagicMock(spec=IPPool)
    mock_pool1.id = 1
    mock_pool1.name = "Customer Pool"
    mock_pool1.pool_type = IPPoolType.CUSTOMER
    
    mock_pool2 = MagicMock(spec=IPPool)
    mock_pool2.id = 2
    mock_pool2.name = "Infrastructure Pool"
    mock_pool2.pool_type = IPPoolType.INFRASTRUCTURE
    
    # Mock the execute method to return our mock pools
    mock_session.execute.return_value.scalars().all.return_value = [mock_pool1, mock_pool2]
    
    # Call get_pools
    result = await ip_pool_service.get_pools(mock_session)
    
    # Check the result
    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Customer Pool"
    assert result[1].id == 2
    assert result[1].name == "Infrastructure Pool"


@pytest.mark.asyncio
async def test_get_pools_with_filters(ip_pool_service, mock_session):
    """Test getting a list of IP pools with filters."""
    # Create mock IP pools
    mock_pool1 = MagicMock(spec=IPPool)
    mock_pool1.id = 1
    mock_pool1.name = "Customer Pool"
    mock_pool1.pool_type = IPPoolType.CUSTOMER
    
    # Mock the execute method to return our mock pools
    mock_session.execute.return_value.scalars().all.return_value = [mock_pool1]
    
    # Call get_pools with filters
    result = await ip_pool_service.get_pools(
        session=mock_session,
        pool_type=IPPoolType.CUSTOMER,
        is_active=True
    )
    
    # Check the result
    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].name == "Customer Pool"
    assert result[0].pool_type == IPPoolType.CUSTOMER


@pytest.mark.asyncio
async def test_allocate_ip(ip_pool_service, mock_session):
    """Test allocating an IP address from a pool."""
    # Create a mock IP pool
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    mock_pool.network = "192.168.1.0/24"
    mock_pool.is_active = True
    
    # Mock the execute method to return our mock pool
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_pool
    
    # Mock the execute method for IP address query to return no results
    mock_session.execute.return_value.scalars().all.return_value = []
    
    # Create a mock IP address
    mock_ip = MagicMock(spec=IPAddress)
    mock_ip.id = 1
    mock_ip.ip_address = "192.168.1.10"
    mock_ip.pool_id = 1
    mock_ip.status = IPAddressStatus.ALLOCATED
    mock_ip.assigned_to_id = 123
    mock_ip.assigned_to_type = "customer"
    
    # Mock the add method
    mock_session.add = MagicMock()
    mock_session.add.return_value = None
    
    # Mock the flush method to set the id
    mock_session.flush = AsyncMock()
    
    # Patch the IPAddress constructor to return our mock IP
    with patch('modules.network.ip_pool_service.IPAddress', return_value=mock_ip):
        # Call allocate_ip
        result = await ip_pool_service.allocate_ip(
            session=mock_session,
            pool_id=1,
            assigned_to_id=123,
            assigned_to_type="customer"
        )
        
        # Check that the IP was added to the session
        mock_session.add.assert_called_once()
        
        # Check that the returned IP is our mock IP
        assert result == mock_ip
        assert result.ip_address == "192.168.1.10"
        assert result.pool_id == 1
        assert result.status == IPAddressStatus.ALLOCATED
        assert result.assigned_to_id == 123
        assert result.assigned_to_type == "customer"


@pytest.mark.asyncio
async def test_allocate_specific_ip(ip_pool_service, mock_session):
    """Test allocating a specific IP address from a pool."""
    # Create a mock IP pool
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    mock_pool.network = "192.168.1.0/24"
    mock_pool.is_active = True
    
    # Mock the execute method to return our mock pool
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_pool
    
    # Mock the execute method for IP address query to return no results
    mock_session.execute.return_value.scalars().all.return_value = []
    
    # Create a mock IP address
    mock_ip = MagicMock(spec=IPAddress)
    mock_ip.id = 1
    mock_ip.ip_address = "192.168.1.20"
    mock_ip.pool_id = 1
    mock_ip.status = IPAddressStatus.ALLOCATED
    mock_ip.assigned_to_id = 123
    mock_ip.assigned_to_type = "customer"
    
    # Mock the add method
    mock_session.add = MagicMock()
    mock_session.add.return_value = None
    
    # Mock the flush method to set the id
    mock_session.flush = AsyncMock()
    
    # Patch the IPAddress constructor to return our mock IP
    with patch('modules.network.ip_pool_service.IPAddress', return_value=mock_ip):
        # Call allocate_ip with a specific IP
        result = await ip_pool_service.allocate_ip(
            session=mock_session,
            pool_id=1,
            assigned_to_id=123,
            assigned_to_type="customer",
            specific_ip="192.168.1.20"
        )
        
        # Check that the IP was added to the session
        mock_session.add.assert_called_once()
        
        # Check that the returned IP is our mock IP with the specific address
        assert result == mock_ip
        assert result.ip_address == "192.168.1.20"
        assert result.pool_id == 1
        assert result.status == IPAddressStatus.ALLOCATED
        assert result.assigned_to_id == 123
        assert result.assigned_to_type == "customer"


@pytest.mark.asyncio
async def test_allocate_ip_pool_not_found(ip_pool_service, mock_session):
    """Test allocating an IP address from a non-existent pool."""
    # Mock the execute method to return None
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Call allocate_ip and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.allocate_ip(
            session=mock_session,
            pool_id=1,
            assigned_to_id=123,
            assigned_to_type="customer"
        )
    
    # Check the exception message
    assert "IP pool with ID 1 not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_allocate_ip_pool_inactive(ip_pool_service, mock_session):
    """Test allocating an IP address from an inactive pool."""
    # Create a mock IP pool that is inactive
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    mock_pool.is_active = False
    
    # Mock the execute method to return our mock pool
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_pool
    
    # Call allocate_ip and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.allocate_ip(
            session=mock_session,
            pool_id=1,
            assigned_to_id=123,
            assigned_to_type="customer"
        )
    
    # Check the exception message
    assert "IP pool is not active" in str(excinfo.value)


@pytest.mark.asyncio
async def test_release_ip(ip_pool_service, mock_session):
    """Test releasing an allocated IP address."""
    # Create a mock IP address
    mock_ip = MagicMock(spec=IPAddress)
    mock_ip.id = 1
    mock_ip.ip_address = "192.168.1.10"
    mock_ip.pool_id = 1
    mock_ip.status = IPAddressStatus.ALLOCATED
    mock_ip.assigned_to_id = 123
    mock_ip.assigned_to_type = "customer"
    
    # Mock the execute method to return our mock IP
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_ip
    
    # Call release_ip
    result = await ip_pool_service.release_ip(
        session=mock_session,
        ip_address="192.168.1.10"
    )
    
    # Check that the IP status was updated
    assert result.status == IPAddressStatus.AVAILABLE
    assert result.assigned_to_id is None
    assert result.assigned_to_type is None


@pytest.mark.asyncio
async def test_release_ip_not_found(ip_pool_service, mock_session):
    """Test releasing a non-existent IP address."""
    # Mock the execute method to return None
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Call release_ip and expect an exception
    with pytest.raises(Exception) as excinfo:
        await ip_pool_service.release_ip(
            session=mock_session,
            ip_address="192.168.1.10"
        )
    
    # Check the exception message
    assert "IP address 192.168.1.10 not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_pool_usage(ip_pool_service, mock_session):
    """Test getting pool usage statistics."""
    # Create a mock IP pool
    mock_pool = MagicMock(spec=IPPool)
    mock_pool.id = 1
    mock_pool.name = "Test Pool"
    mock_pool.network = "192.168.1.0/24"
    
    # Mock the execute method to return our mock pool
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_pool
    
    # Create mock IP addresses
    mock_ip1 = MagicMock(spec=IPAddress)
    mock_ip1.ip_address = "192.168.1.10"
    mock_ip1.status = IPAddressStatus.ALLOCATED
    
    mock_ip2 = MagicMock(spec=IPAddress)
    mock_ip2.ip_address = "192.168.1.11"
    mock_ip2.status = IPAddressStatus.ALLOCATED
    
    mock_ip3 = MagicMock(spec=IPAddress)
    mock_ip3.ip_address = "192.168.1.12"
    mock_ip3.status = IPAddressStatus.RESERVED
    
    # Mock the execute method for IP addresses to return our mock IPs
    mock_session.execute.return_value.scalars().all.return_value = [mock_ip1, mock_ip2, mock_ip3]
    
    # Patch the calculate_subnet_utilization function
    with patch('modules.network.ip_pool_service.calculate_subnet_utilization') as mock_calc:
        mock_calc.return_value = {
            'subnet': '192.168.1.0/24',
            'total_ips': 256,
            'usable_ips': 254,
            'used_ips': 3,
            'free_ips': 251,
            'utilization_percent': 1.18
        }
        
        # Call get_pool_usage
        result = await ip_pool_service.get_pool_usage(mock_session, 1)
        
        # Check the result
        assert result['subnet'] == '192.168.1.0/24'
        assert result['total_ips'] == 256
        assert result['usable_ips'] == 254
        assert result['used_ips'] == 3
        assert result['free_ips'] == 251
        assert result['utilization_percent'] == 1.18
        assert result['allocated_ips'] == 2
        assert result['reserved_ips'] == 1
