"""
Unit tests for the Tariff Enforcement Module's service layer.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.orm import Session

from modules.tariff.services import TariffService
from modules.tariff.schemas import (
    TariffPlanCreate, 
    TariffPlanUpdate,
    UserTariffPlanCreate,
    UserTariffPlanUpdate,
    UserUsageRecordCreate,
    FUPThresholdCheck,
    UsageCheckRequest
)
from backend_core.models import (
    TariffPlan,
    UserTariffPlan,
    UserUsageRecord,
    TariffPlanChange,
    TariffPolicyAction,
    User,
    RadiusProfile
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def tariff_service(mock_db):
    """Create a TariffService instance with a mock database."""
    service = TariffService(mock_db)
    service.radius_service = MagicMock()
    return service


@pytest.fixture
def sample_tariff_plan():
    """Create a sample tariff plan for testing."""
    return TariffPlan(
        id=1,
        name="Test Plan",
        description="A test tariff plan",
        price=Decimal("49.99"),
        billing_cycle="monthly",
        download_speed=50,
        upload_speed=10,
        data_cap=100 * 1024 * 1024 * 1024,  # 100 GB
        fup_threshold=80 * 1024 * 1024 * 1024,  # 80 GB
        throttle_speed_download=10,
        throttle_speed_upload=2,
        radius_policy_id=1,
        throttled_radius_policy_id=2,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True
    )


@pytest.fixture
def sample_user_tariff_plan(sample_user, sample_tariff_plan):
    """Create a sample user tariff plan for testing."""
    now = datetime.utcnow()
    cycle_end = now + timedelta(days=30)
    return UserTariffPlan(
        id=1,
        user_id=sample_user.id,
        tariff_plan_id=sample_tariff_plan.id,
        status="active",
        start_date=now,
        end_date=None,
        current_cycle_start=now,
        current_cycle_end=cycle_end,
        data_used=20 * 1024 * 1024 * 1024,  # 20 GB
        is_throttled=False,
        created_at=now,
        updated_at=now
    )


class TestTariffPlanManagement:
    """Tests for tariff plan management methods."""

    def test_create_tariff_plan(self, tariff_service, mock_db, sample_tariff_plan):
        """Test creating a new tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        plan_data = TariffPlanCreate(
            name="New Plan",
            description="A new tariff plan",
            price=Decimal("59.99"),
            billing_cycle="monthly",
            download_speed=100,
            upload_speed=20,
            data_cap=200 * 1024 * 1024 * 1024,  # 200 GB
            fup_threshold=160 * 1024 * 1024 * 1024  # 160 GB
        )
        
        # Execute
        result = tariff_service.create_tariff_plan(plan_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
        assert result is not None
        
    def test_create_tariff_plan_name_exists(self, tariff_service, mock_db, sample_tariff_plan):
        """Test creating a tariff plan with an existing name."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tariff_plan
        
        plan_data = TariffPlanCreate(
            name="Test Plan",  # Same name as sample_tariff_plan
            description="Another test plan",
            price=Decimal("39.99"),
            billing_cycle="monthly",
            download_speed=25,
            upload_speed=5
        )
        
        # Execute & Assert
        with pytest.raises(HTTPException) as excinfo:
            tariff_service.create_tariff_plan(plan_data)
        
        assert excinfo.value.status_code == 400
        assert "already exists" in excinfo.value.detail
    
    def test_get_tariff_plan(self, tariff_service, mock_db, sample_tariff_plan):
        """Test getting a tariff plan by ID."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tariff_plan
        
        # Execute
        result = tariff_service.get_tariff_plan(1)
        
        # Assert
        assert result == sample_tariff_plan
        mock_db.query.assert_called_once()
    
    def test_get_tariff_plan_not_found(self, tariff_service, mock_db):
        """Test getting a non-existent tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute & Assert
        with pytest.raises(HTTPException) as excinfo:
            tariff_service.get_tariff_plan(999)
        
        assert excinfo.value.status_code == 404
        assert "not found" in excinfo.value.detail
    
    def test_update_tariff_plan(self, tariff_service, mock_db, sample_tariff_plan):
        """Test updating a tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tariff_plan
        mock_db.commit.return_value = None
        
        update_data = TariffPlanUpdate(
            price=Decimal("54.99"),
            download_speed=75,
            upload_speed=15
        )
        
        # Execute
        result = tariff_service.update_tariff_plan(1, update_data)
        
        # Assert
        assert result == sample_tariff_plan
        assert result.price == Decimal("54.99")
        assert result.download_speed == 75
        assert result.upload_speed == 15
        mock_db.commit.assert_called_once()
    
    def test_delete_tariff_plan(self, tariff_service, mock_db, sample_tariff_plan):
        """Test deleting a tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tariff_plan
        mock_db.query.return_value.filter.return_value.count.return_value = 0  # No active users
        mock_db.commit.return_value = None
        
        # Execute
        result = tariff_service.delete_tariff_plan(1)
        
        # Assert
        assert result is True
        assert sample_tariff_plan.is_active is False
        mock_db.commit.assert_called_once()
    
    def test_delete_tariff_plan_with_users(self, tariff_service, mock_db, sample_tariff_plan):
        """Test deleting a tariff plan that has active users."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tariff_plan
        mock_db.query.return_value.filter.return_value.count.return_value = 5  # 5 active users
        
        # Execute & Assert
        with pytest.raises(HTTPException) as excinfo:
            tariff_service.delete_tariff_plan(1)
        
        assert excinfo.value.status_code == 400
        assert "active users" in excinfo.value.detail


class TestUserTariffPlanManagement:
    """Tests for user tariff plan management methods."""
    
    def test_assign_plan_to_user(self, tariff_service, mock_db, sample_user, sample_tariff_plan):
        """Test assigning a tariff plan to a user."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user,  # First query for user
            sample_tariff_plan,  # Second query for plan
            None  # Third query for existing plan (none found)
        ]
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        start_date = datetime.utcnow()
        assignment_data = UserTariffPlanCreate(
            user_id=sample_user.id,
            tariff_plan_id=sample_tariff_plan.id,
            status="active",
            start_date=start_date,
            end_date=None
        )
        
        # Execute
        result = tariff_service.assign_plan_to_user(assignment_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.tariff_plan_id == sample_tariff_plan.id
        assert result.status == "active"
        assert result.start_date == start_date
    
    def test_assign_plan_user_not_found(self, tariff_service, mock_db):
        """Test assigning a plan to a non-existent user."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        assignment_data = UserTariffPlanCreate(
            user_id=999,
            tariff_plan_id=1,
            status="active",
            start_date=datetime.utcnow(),
            end_date=None
        )
        
        # Execute & Assert
        with pytest.raises(HTTPException) as excinfo:
            tariff_service.assign_plan_to_user(assignment_data)
        
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail
    
    def test_assign_inactive_plan(self, tariff_service, mock_db, sample_user):
        """Test assigning an inactive plan to a user."""
        # Setup
        inactive_plan = MagicMock(spec=TariffPlan)
        inactive_plan.is_active = False
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user,  # First query for user
            inactive_plan  # Second query for plan (inactive)
        ]
        
        assignment_data = UserTariffPlanCreate(
            user_id=sample_user.id,
            tariff_plan_id=2,
            status="active",
            start_date=datetime.utcnow(),
            end_date=None
        )
        
        # Execute & Assert
        with pytest.raises(HTTPException) as excinfo:
            tariff_service.assign_plan_to_user(assignment_data)
        
        assert excinfo.value.status_code == 400
        assert "inactive tariff plan" in excinfo.value.detail
    
    def test_get_user_tariff_plan(self, tariff_service, mock_db, sample_user_tariff_plan):
        """Test getting a user's active tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user_tariff_plan
        
        # Execute
        result = tariff_service.get_user_tariff_plan(sample_user_tariff_plan.user_id)
        
        # Assert
        assert result == sample_user_tariff_plan
        mock_db.query.assert_called_once()
    
    def test_update_user_tariff_plan(self, tariff_service, mock_db, sample_user_tariff_plan):
        """Test updating a user's tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user_tariff_plan
        mock_db.commit.return_value = None
        
        update_data = UserTariffPlanUpdate(
            status="suspended",
            end_date=datetime.utcnow() + timedelta(days=15)
        )
        
        # Execute
        result = tariff_service.update_user_tariff_plan(sample_user_tariff_plan.id, update_data)
        
        # Assert
        assert result == sample_user_tariff_plan
        assert result.status == "suspended"
        assert result.end_date is not None
        mock_db.commit.assert_called_once()
    
    def test_cancel_user_tariff_plan(self, tariff_service, mock_db, sample_user_tariff_plan):
        """Test cancelling a user's tariff plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user_tariff_plan
        mock_db.commit.return_value = None
        
        # Execute
        result = tariff_service.cancel_user_tariff_plan(sample_user_tariff_plan.user_id)
        
        # Assert
        assert result is True
        assert sample_user_tariff_plan.status == "cancelled"
        assert sample_user_tariff_plan.end_date is not None
        mock_db.commit.assert_called_once()
        tariff_service.radius_service.disconnect_user.assert_called_once_with(sample_user_tariff_plan.user_id)


class TestUsageTracking:
    """Tests for usage tracking and policy enforcement methods."""
    
    def test_record_usage(self, tariff_service, mock_db, sample_user_tariff_plan):
        """Test recording usage data."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user_tariff_plan
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock the _check_policy_triggers method
        tariff_service._check_policy_triggers = MagicMock()
        
        usage_data = UserUsageRecordCreate(
            user_tariff_plan_id=sample_user_tariff_plan.id,
            download_bytes=1000000000,  # 1 GB
            upload_bytes=200000000,  # 200 MB
            source="radius",
            session_id="TEST-SESSION-123"
        )
        
        initial_data_used = sample_user_tariff_plan.data_used
        
        # Execute
        result = tariff_service.record_usage(usage_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
        assert result is not None
        assert result.download_bytes == usage_data.download_bytes
        assert result.upload_bytes == usage_data.upload_bytes
        assert result.total_bytes == usage_data.download_bytes + usage_data.upload_bytes
        assert sample_user_tariff_plan.data_used == initial_data_used + result.total_bytes
        tariff_service._check_policy_triggers.assert_called_once_with(sample_user_tariff_plan)
    
    def test_check_fup_threshold_not_exceeded(self, tariff_service, mock_db, sample_user, sample_tariff_plan, sample_user_tariff_plan):
        """Test checking FUP threshold when not exceeded."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan
        ]
        
        # Set usage below threshold
        sample_user_tariff_plan.data_used = sample_tariff_plan.fup_threshold - 1000000000  # 1 GB below threshold
        
        check_data = FUPThresholdCheck(
            user_id=sample_user.id,
            current_usage_bytes=sample_user_tariff_plan.data_used
        )
        
        # Execute
        result = tariff_service.check_fup_threshold(check_data)
        
        # Assert
        assert result.threshold_exceeded is False
        assert result.action is None
    
    def test_check_fup_threshold_exceeded(self, tariff_service, mock_db, sample_user, sample_tariff_plan, sample_user_tariff_plan):
        """Test checking FUP threshold when exceeded."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan
        ]
        
        # Set usage above threshold
        sample_user_tariff_plan.data_used = sample_tariff_plan.fup_threshold + 1000000000  # 1 GB above threshold
        
        check_data = FUPThresholdCheck(
            user_id=sample_user.id,
            current_usage_bytes=sample_user_tariff_plan.data_used
        )
        
        # Execute
        result = tariff_service.check_fup_threshold(check_data)
        
        # Assert
        assert result.threshold_exceeded is True
        assert result.action == "throttle"
    
    def test_check_usage(self, tariff_service, mock_db, sample_user, sample_tariff_plan, sample_user_tariff_plan):
        """Test checking a user's usage against their plan limits."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan
        ]
        
        # Mock the record_usage method
        tariff_service.record_usage = MagicMock()
        
        check_data = UsageCheckRequest(
            user_id=sample_user.id,
            download_bytes=500000000,  # 500 MB
            upload_bytes=100000000,  # 100 MB
            session_id="TEST-SESSION-123"
        )
        
        # Execute
        result = tariff_service.check_usage(check_data)
        
        # Assert
        assert result.user_id == sample_user.id
        assert result.tariff_plan_id == sample_tariff_plan.id
        assert result.plan_name == sample_tariff_plan.name
        assert result.status == "ok"  # Not throttled or suspended
        assert result.current_usage == sample_user_tariff_plan.data_used
        assert result.data_cap == sample_tariff_plan.data_cap
        assert result.percentage_used == (sample_user_tariff_plan.data_used / sample_tariff_plan.data_cap) * 100
        assert len(result.actions_triggered) == 0  # No actions triggered
        assert result.message is not None
        
        # If download_bytes or upload_bytes > 0, record_usage should be called
        if check_data.download_bytes > 0 or check_data.upload_bytes > 0:
            tariff_service.record_usage.assert_called_once()
    
    def test_reset_usage_cycle(self, tariff_service, mock_db, sample_user_tariff_plan, sample_tariff_plan):
        """Test resetting a user's usage cycle."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan (used in _calculate_cycle_end)
        ]
        mock_db.commit.return_value = None
        
        # Set user as throttled
        sample_user_tariff_plan.is_throttled = True
        sample_user_tariff_plan.throttled_at = datetime.utcnow() - timedelta(days=1)
        sample_user_tariff_plan.data_used = 90 * 1024 * 1024 * 1024  # 90 GB
        
        # Mock the _remove_throttling method
        tariff_service._remove_throttling = MagicMock()
        
        # Execute
        result = tariff_service.reset_usage_cycle(sample_user_tariff_plan.user_id)
        
        # Assert
        assert result is True
        assert sample_user_tariff_plan.data_used == 0
        assert sample_user_tariff_plan.is_throttled is False
        assert sample_user_tariff_plan.throttled_at is None
        assert sample_user_tariff_plan.current_cycle_start is not None
        assert sample_user_tariff_plan.current_cycle_end is not None
        tariff_service._remove_throttling.assert_called_once()
        mock_db.commit.assert_called_once()


class TestPolicyEnforcement:
    """Tests for policy enforcement methods."""
    
    def test_apply_throttling(self, tariff_service, mock_db, sample_user, sample_tariff_plan):
        """Test applying throttling to a user's connection."""
        # Setup
        radius_profile = MagicMock(spec=RadiusProfile)
        radius_profile.id = 1
        radius_profile.user_id = sample_user.id
        radius_profile.bandwidth_policy_id = sample_tariff_plan.radius_policy_id
        
        mock_db.query.return_value.filter.return_value.first.return_value = radius_profile
        mock_db.commit.return_value = None
        
        # Mock active sessions
        active_session = MagicMock()
        active_session.nas_id = 1
        active_session.session_id = "TEST-SESSION-123"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [active_session]
        
        # Execute
        tariff_service._apply_throttling(sample_user.id, sample_tariff_plan)
        
        # Assert
        assert radius_profile.original_bandwidth_policy_id == sample_tariff_plan.radius_policy_id
        assert radius_profile.bandwidth_policy_id == sample_tariff_plan.throttled_radius_policy_id
        mock_db.commit.assert_called_once()
        tariff_service.radius_service.send_coa_request.assert_called_once()
    
    def test_remove_throttling(self, tariff_service, mock_db, sample_user, sample_tariff_plan):
        """Test removing throttling from a user's connection."""
        # Setup
        radius_profile = MagicMock(spec=RadiusProfile)
        radius_profile.id = 1
        radius_profile.user_id = sample_user.id
        radius_profile.bandwidth_policy_id = sample_tariff_plan.throttled_radius_policy_id
        radius_profile.original_bandwidth_policy_id = sample_tariff_plan.radius_policy_id
        
        mock_db.query.return_value.filter.return_value.first.return_value = radius_profile
        mock_db.commit.return_value = None
        
        # Mock active sessions
        active_session = MagicMock()
        active_session.nas_id = 1
        active_session.session_id = "TEST-SESSION-123"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [active_session]
        
        # Execute
        tariff_service._remove_throttling(sample_user.id, sample_tariff_plan)
        
        # Assert
        assert radius_profile.bandwidth_policy_id == sample_tariff_plan.radius_policy_id
        assert radius_profile.original_bandwidth_policy_id is None
        mock_db.commit.assert_called_once()
        tariff_service.radius_service.send_coa_request.assert_called_once()
    
    def test_block_user(self, tariff_service, mock_db, sample_user):
        """Test blocking a user's connection."""
        # Setup
        radius_profile = MagicMock(spec=RadiusProfile)
        radius_profile.id = 1
        radius_profile.user_id = sample_user.id
        radius_profile.is_active = True
        
        mock_db.query.return_value.filter.return_value.first.return_value = radius_profile
        mock_db.commit.return_value = None
        
        # Execute
        tariff_service._block_user(sample_user.id)
        
        # Assert
        assert radius_profile.is_active is False
        mock_db.commit.assert_called_once()
        tariff_service.radius_service.disconnect_user.assert_called_once_with(sample_user.id)
    
    def test_calculate_overage_fee(self, tariff_service, mock_db, sample_user_tariff_plan, sample_tariff_plan):
        """Test calculating overage fees."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan
        ]
        
        # Set plan features with overage rate
        sample_tariff_plan.features = {"overage_rate": 10.0}  # $10 per GB
        
        # Set usage above data cap
        usage_mb = 120 * 1024  # 120 GB in MB
        data_cap_mb = sample_tariff_plan.data_cap / (1024 * 1024)  # Convert bytes to MB
        overage_mb = usage_mb - data_cap_mb
        overage_gb = overage_mb / 1024
        expected_fee = overage_gb * 10.0
        
        # Execute
        result = tariff_service.calculate_overage_fee(sample_user_tariff_plan.user_id, usage_mb)
        
        # Assert
        assert result == expected_fee
    
    def test_calculate_overage_fee_unlimited_plan(self, tariff_service, mock_db, sample_user_tariff_plan, sample_tariff_plan):
        """Test calculating overage fees for an unlimited plan."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_user_tariff_plan,  # First query for user plan
            sample_tariff_plan  # Second query for tariff plan
        ]
        
        # Set plan as unlimited
        sample_tariff_plan.data_cap = None
        
        # Execute
        result = tariff_service.calculate_overage_fee(sample_user_tariff_plan.user_id, 150 * 1024)  # 150 GB in MB
        
        # Assert
        assert result == 0.0  # No overage fee for unlimited plans
