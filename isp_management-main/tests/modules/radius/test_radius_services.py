import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend_core.models import (
    User, RadiusProfile, RadiusAccounting, NasDevice, 
    NasVendorAttribute, RadiusBandwidthPolicy, RadiusProfileAttribute,
    RadiusCoALog
)
from modules.radius.schemas import (
    RadiusProfileCreate, RadiusProfileUpdate, 
    RadiusAuthRequest, RadiusAccountingStart, RadiusAccountingUpdate, RadiusAccountingStop,
    NasDeviceCreate, NasDeviceUpdate,
    NasVendorAttributeCreate, NasVendorAttributeUpdate,
    RadiusBandwidthPolicyCreate, RadiusBandwidthPolicyUpdate,
    RadiusProfileAttributeCreate, RadiusProfileAttributeUpdate,
    RadiusCoARequest
)
from modules.radius.services import RadiusService


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    return MagicMock(spec=Session)


@pytest.fixture
def radius_service(db_session):
    """Create a RadiusService instance with a mock database session."""
    return RadiusService(db_session)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        id=1,
        username="testuser",
        email="testuser@example.com",
        is_active=True
    )


@pytest.fixture
def mock_radius_profile():
    """Create a mock RADIUS profile for testing."""
    return RadiusProfile(
        id=1,
        user_id=1,
        username="testuser",
        password="hashed_password",
        service_type="Framed-User",
        simultaneous_use=1,
        interim_interval=300,
        session_timeout=3600,
        idle_timeout=1800,
        bandwidth_policy_id=1,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_nas_device():
    """Create a mock NAS device for testing."""
    return NasDevice(
        id=1,
        name="Test NAS",
        ip_address="192.168.1.1",
        type="Router",
        vendor="Mikrotik",
        model="RouterOS",
        secret="encrypted_secret",
        description="Test NAS device",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_bandwidth_policy():
    """Create a mock bandwidth policy for testing."""
    return RadiusBandwidthPolicy(
        id=1,
        name="Basic Plan",
        description="10 Mbps download, 2 Mbps upload",
        download_rate=10240,
        upload_rate=2048,
        burst_download_rate=15360,
        burst_upload_rate=3072,
        burst_threshold=10485760,
        burst_time=60,
        priority=5,
        time_based_limits=None,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_accounting_session():
    """Create a mock accounting session for testing."""
    return RadiusAccounting(
        id=1,
        profile_id=1,
        session_id="test_session_id",
        nas_id=1,
        nas_ip_address="192.168.1.1",
        nas_port_id="eth0",
        framed_ip_address="10.0.0.100",
        framed_protocol="PPP",
        acct_status_type="Start",
        acct_authentic="RADIUS",
        acct_session_time=0,
        acct_input_octets=0,
        acct_output_octets=0,
        acct_input_packets=0,
        acct_output_packets=0,
        acct_terminate_cause=None,
        start_time=datetime.utcnow(),
        update_time=None,
        stop_time=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestRadiusProfileManagement:
    """Test RADIUS profile management functionality."""

    def test_create_radius_profile(self, radius_service, db_session, mock_user):
        """Test creating a new RADIUS profile."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_user
        db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None  # No existing profile
        
        profile_data = RadiusProfileCreate(
            user_id=1,
            username="testuser",
            password="password123",
            service_type="Framed-User",
            simultaneous_use=1,
            interim_interval=300,
            session_timeout=3600,
            idle_timeout=1800,
            bandwidth_policy_id=1
        )
        
        # Act
        result = radius_service.create_radius_profile(profile_data)
        
        # Assert
        assert db_session.add.called
        assert db_session.commit.called
        assert result.username == "testuser"
        assert result.user_id == 1

    def test_create_radius_profile_user_not_found(self, radius_service, db_session):
        """Test creating a profile for a non-existent user."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        profile_data = RadiusProfileCreate(
            user_id=999,
            username="nonexistent",
            password="password123"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            radius_service.create_radius_profile(profile_data)
        
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail

    def test_create_radius_profile_duplicate_username(self, radius_service, db_session, mock_user, mock_radius_profile):
        """Test creating a profile with a duplicate username."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # User exists
            mock_radius_profile  # Username already exists
        ]
        
        profile_data = RadiusProfileCreate(
            user_id=1,
            username="testuser",
            password="password123"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            radius_service.create_radius_profile(profile_data)
        
        assert excinfo.value.status_code == 400
        assert "Username already exists" in excinfo.value.detail

    def test_get_radius_profile(self, radius_service, db_session, mock_radius_profile):
        """Test retrieving a RADIUS profile by ID."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        # Act
        result = radius_service.get_radius_profile(1)
        
        # Assert
        assert result == mock_radius_profile
        assert result.id == 1
        assert result.username == "testuser"

    def test_update_radius_profile(self, radius_service, db_session, mock_radius_profile):
        """Test updating a RADIUS profile."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        profile_data = RadiusProfileUpdate(
            service_type="Framed-User",
            simultaneous_use=2,
            session_timeout=7200,
            is_active=True
        )
        
        # Act
        result = radius_service.update_radius_profile(1, profile_data)
        
        # Assert
        assert db_session.commit.called
        assert result.simultaneous_use == 2
        assert result.session_timeout == 7200

    def test_delete_radius_profile(self, radius_service, db_session, mock_radius_profile):
        """Test deleting a RADIUS profile."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        # Act
        result = radius_service.delete_radius_profile(1)
        
        # Assert
        assert db_session.delete.called
        assert db_session.commit.called
        assert result is True


class TestRadiusAuthentication:
    """Test RADIUS authentication functionality."""

    def test_authenticate_user_success(self, radius_service, db_session, mock_radius_profile):
        """Test successful user authentication."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        # Mock password verification
        with patch('modules.radius.services.verify_password', return_value=True):
            auth_request = RadiusAuthRequest(
                username="testuser",
                password="password123",
                nas_ip_address="192.168.1.1"
            )
            
            # Act
            result = radius_service.authenticate_user(auth_request)
            
            # Assert
            assert result.status == "accept"
            assert "Authentication successful" in result.message
            assert "Service-Type" in result.attributes

    def test_authenticate_user_invalid_password(self, radius_service, db_session, mock_radius_profile):
        """Test authentication with invalid password."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        # Mock password verification
        with patch('modules.radius.services.verify_password', return_value=False):
            auth_request = RadiusAuthRequest(
                username="testuser",
                password="wrong_password",
                nas_ip_address="192.168.1.1"
            )
            
            # Act
            result = radius_service.authenticate_user(auth_request)
            
            # Assert
            assert result.status == "reject"
            assert "Invalid password" in result.message

    def test_authenticate_user_inactive_profile(self, radius_service, db_session, mock_radius_profile):
        """Test authentication with inactive profile."""
        # Arrange
        mock_radius_profile.is_active = False
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        
        auth_request = RadiusAuthRequest(
            username="testuser",
            password="password123",
            nas_ip_address="192.168.1.1"
        )
        
        # Act
        result = radius_service.authenticate_user(auth_request)
        
        # Assert
        assert result.status == "reject"
        assert "Profile is inactive" in result.message


class TestRadiusAccounting:
    """Test RADIUS accounting functionality."""

    def test_start_accounting_session(self, radius_service, db_session, mock_radius_profile):
        """Test starting an accounting session."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # No existing session
            mock_radius_profile  # Profile exists
        ]
        
        session_id = str(uuid.uuid4())
        accounting_data = RadiusAccountingStart(
            username="testuser",
            session_id=session_id,
            nas_ip_address="192.168.1.1",
            nas_port_id="eth0",
            framed_ip_address="10.0.0.100",
            framed_protocol="PPP",
            acct_status_type="Start",
            acct_authentic="RADIUS"
        )
        
        # Act
        result = radius_service.start_accounting_session(accounting_data)
        
        # Assert
        assert db_session.add.called
        assert db_session.commit.called
        assert result.session_id == session_id
        assert result.acct_status_type == "Start"

    def test_update_accounting_session(self, radius_service, db_session, mock_accounting_session):
        """Test updating an accounting session."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_accounting_session
        
        accounting_data = RadiusAccountingUpdate(
            username="testuser",
            session_id="test_session_id",
            nas_ip_address="192.168.1.1",
            acct_status_type="Interim-Update",
            acct_session_time=600,
            acct_input_octets=1024000,
            acct_output_octets=2048000,
            acct_input_packets=1000,
            acct_output_packets=2000
        )
        
        # Act
        result = radius_service.update_accounting_session(accounting_data)
        
        # Assert
        assert db_session.commit.called
        assert result.acct_status_type == "Interim-Update"
        assert result.acct_session_time == 600
        assert result.acct_input_octets == 1024000
        assert result.acct_output_octets == 2048000

    def test_stop_accounting_session(self, radius_service, db_session, mock_accounting_session):
        """Test stopping an accounting session."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_accounting_session
        
        accounting_data = RadiusAccountingStop(
            username="testuser",
            session_id="test_session_id",
            nas_ip_address="192.168.1.1",
            acct_status_type="Stop",
            acct_session_time=1200,
            acct_input_octets=2048000,
            acct_output_octets=4096000,
            acct_input_packets=2000,
            acct_output_packets=4000,
            acct_terminate_cause="User-Request"
        )
        
        # Act
        result = radius_service.stop_accounting_session(accounting_data)
        
        # Assert
        assert db_session.commit.called
        assert result.acct_status_type == "Stop"
        assert result.acct_session_time == 1200
        assert result.acct_terminate_cause == "User-Request"
        assert result.stop_time is not None


class TestNasDeviceManagement:
    """Test NAS device management functionality."""

    def test_create_nas_device(self, radius_service, db_session):
        """Test creating a new NAS device."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = None  # No existing device
        
        # Mock encryption
        with patch.object(radius_service, 'encrypt_secret', return_value="encrypted_secret"):
            device_data = NasDeviceCreate(
                name="Test NAS",
                ip_address="192.168.1.1",
                type="Router",
                vendor="Mikrotik",
                model="RouterOS",
                secret="test_secret",
                description="Test NAS device"
            )
            
            # Act
            result = radius_service.create_nas_device(device_data)
            
            # Assert
            assert db_session.add.called
            assert db_session.commit.called
            assert result.name == "Test NAS"
            assert result.ip_address == "192.168.1.1"
            assert result.secret == "encrypted_secret"

    def test_create_nas_device_duplicate_ip(self, radius_service, db_session, mock_nas_device):
        """Test creating a NAS device with duplicate IP address."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_nas_device
        
        device_data = NasDeviceCreate(
            name="Another NAS",
            ip_address="192.168.1.1",  # Same IP as mock_nas_device
            secret="test_secret"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            radius_service.create_nas_device(device_data)
        
        assert excinfo.value.status_code == 400
        assert "NAS device with this IP address already exists" in excinfo.value.detail

    def test_update_nas_device(self, radius_service, db_session, mock_nas_device):
        """Test updating a NAS device."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_nas_device
        
        # Mock encryption
        with patch.object(radius_service, 'encrypt_secret', return_value="new_encrypted_secret"):
            device_data = NasDeviceUpdate(
                name="Updated NAS",
                model="RouterOS 7.0",
                secret="new_secret"
            )
            
            # Act
            result = radius_service.update_nas_device(1, device_data)
            
            # Assert
            assert db_session.commit.called
            assert result.name == "Updated NAS"
            assert result.model == "RouterOS 7.0"
            assert result.secret == "new_encrypted_secret"


class TestBandwidthPolicyManagement:
    """Test bandwidth policy management functionality."""

    def test_create_bandwidth_policy(self, radius_service, db_session):
        """Test creating a new bandwidth policy."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = None  # No existing policy
        
        policy_data = RadiusBandwidthPolicyCreate(
            name="Basic Plan",
            description="10 Mbps download, 2 Mbps upload",
            download_rate=10240,
            upload_rate=2048,
            burst_download_rate=15360,
            burst_upload_rate=3072,
            burst_threshold=10485760,
            burst_time=60,
            priority=5,
            time_based_limits=None,
            is_active=True
        )
        
        # Act
        result = radius_service.create_bandwidth_policy(policy_data)
        
        # Assert
        assert db_session.add.called
        assert db_session.commit.called
        assert result.name == "Basic Plan"
        assert result.download_rate == 10240
        assert result.upload_rate == 2048

    def test_update_bandwidth_policy(self, radius_service, db_session, mock_bandwidth_policy):
        """Test updating a bandwidth policy."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_bandwidth_policy
        db_session.query.return_value.filter.return_value.all.return_value = []  # No profiles using this policy
        
        policy_data = RadiusBandwidthPolicyUpdate(
            name="Updated Plan",
            download_rate=20480,  # 20 Mbps
            upload_rate=5120,     # 5 Mbps
            priority=4
        )
        
        # Act
        result = radius_service.update_bandwidth_policy(1, policy_data)
        
        # Assert
        assert db_session.commit.called
        assert result.name == "Updated Plan"
        assert result.download_rate == 20480
        assert result.upload_rate == 5120
        assert result.priority == 4


class TestCoAFunctionality:
    """Test Change of Authorization (CoA) functionality."""

    def test_send_coa_request(self, radius_service, db_session, mock_nas_device, mock_radius_profile):
        """Test sending a CoA request."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_nas_device,     # NAS device exists
            mock_radius_profile  # Profile exists
        ]
        
        # Mock decryption
        with patch.object(radius_service, 'decrypt_secret', return_value="decrypted_secret"):
            coa_request = RadiusCoARequest(
                profile_id=1,
                nas_id=1,
                session_id="test_session_id",
                coa_type="update",
                attributes={"Session-Timeout": 7200}
            )
            
            # Act
            result = radius_service.send_coa_request(coa_request)
            
            # Assert
            assert db_session.add.called  # CoA log added
            assert db_session.commit.called
            assert result.profile_id == 1
            assert result.nas_id == 1
            assert result.session_id == "test_session_id"
            assert result.coa_type == "update"
            assert result.result == "success"

    def test_disconnect_user_session(self, radius_service, db_session, mock_accounting_session):
        """Test disconnecting a user session."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_accounting_session
        
        # Mock send_coa_request
        with patch.object(radius_service, 'send_coa_request') as mock_send_coa:
            mock_send_coa.return_value.result = "success"
            
            # Act
            result = radius_service.disconnect_user_session("test_session_id")
            
            # Assert
            assert mock_send_coa.called
            assert result is True

    def test_disconnect_user(self, radius_service, db_session, mock_radius_profile, mock_accounting_session):
        """Test disconnecting all sessions for a user."""
        # Arrange
        db_session.query.return_value.filter.return_value.first.return_value = mock_radius_profile
        db_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [mock_accounting_session]
        
        # Mock send_coa_request
        with patch.object(radius_service, 'send_coa_request') as mock_send_coa:
            mock_send_coa.return_value.result = "success"
            mock_send_coa.return_value.error_message = None
            
            # Act
            result = radius_service.disconnect_user("testuser")
            
            # Assert
            assert mock_send_coa.called
            assert result["total_sessions"] == 1
            assert result["successful_disconnects"] == 1
            assert result["failed_disconnects"] == 0
