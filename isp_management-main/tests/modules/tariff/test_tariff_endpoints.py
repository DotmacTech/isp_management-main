"""
Integration tests for the Tariff Enforcement Module's API endpoints.
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

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from modules.tariff.endpoints import router as tariff_router
from modules.tariff.services import TariffService
from modules.tariff.schemas import (
    TariffPlanCreate,
    TariffPlanUpdate,
    UserTariffPlanCreate,
    UserTariffPlanUpdate,
    UserUsageRecordCreate
)
from backend_core.models import (
    TariffPlan,
    UserTariffPlan,
    UserUsageRecord,
    User
)
from backend_core.auth.dependencies import get_current_active_user, get_current_admin_user


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    app = FastAPI()
    app.include_router(tariff_router)
    
    # Override the dependencies
    app.dependency_overrides[get_current_active_user] = lambda: User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    
    app.dependency_overrides[get_current_admin_user] = lambda: User(
        id=1,
        username="adminuser",
        email="admin@example.com",
        is_active=True,
        is_admin=True
    )
    
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_tariff_service():
    """Create a mock TariffService."""
    return MagicMock(spec=TariffService)


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
def sample_user_tariff_plan():
    """Create a sample user tariff plan for testing."""
    now = datetime.utcnow()
    cycle_end = now + timedelta(days=30)
    return UserTariffPlan(
        id=1,
        user_id=1,
        tariff_plan_id=1,
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


class TestTariffPlanEndpoints:
    """Tests for tariff plan management endpoints."""
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_get_all_tariff_plans(self, mock_service_class, client, sample_tariff_plan):
        """Test getting all tariff plans."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.get_all_tariff_plans.return_value = [sample_tariff_plan]
        
        # Execute
        response = client.get("/tariff/plans")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == sample_tariff_plan.id
        assert data[0]["name"] == sample_tariff_plan.name
        mock_service.get_all_tariff_plans.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_get_tariff_plan(self, mock_service_class, client, sample_tariff_plan):
        """Test getting a specific tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.get_tariff_plan.return_value = sample_tariff_plan
        
        # Execute
        response = client.get(f"/tariff/plans/{sample_tariff_plan.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tariff_plan.id
        assert data["name"] == sample_tariff_plan.name
        mock_service.get_tariff_plan.assert_called_once_with(sample_tariff_plan.id)
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_create_tariff_plan(self, mock_service_class, client, sample_tariff_plan):
        """Test creating a new tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.create_tariff_plan.return_value = sample_tariff_plan
        
        plan_data = {
            "name": "New Plan",
            "description": "A new tariff plan",
            "price": 59.99,
            "billing_cycle": "monthly",
            "download_speed": 100,
            "upload_speed": 20,
            "data_cap": 200 * 1024 * 1024 * 1024,  # 200 GB
            "fup_threshold": 160 * 1024 * 1024 * 1024  # 160 GB
        }
        
        # Execute
        response = client.post("/tariff/plans", json=plan_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == sample_tariff_plan.id
        assert data["name"] == sample_tariff_plan.name
        mock_service.create_tariff_plan.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_update_tariff_plan(self, mock_service_class, client, sample_tariff_plan):
        """Test updating a tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.update_tariff_plan.return_value = sample_tariff_plan
        
        update_data = {
            "price": 54.99,
            "download_speed": 75,
            "upload_speed": 15
        }
        
        # Execute
        response = client.put(f"/tariff/plans/{sample_tariff_plan.id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tariff_plan.id
        mock_service.update_tariff_plan.assert_called_once_with(sample_tariff_plan.id, pytest.ANY)
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_delete_tariff_plan(self, mock_service_class, client, sample_tariff_plan):
        """Test deleting a tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.delete_tariff_plan.return_value = True
        
        # Execute
        response = client.delete(f"/tariff/plans/{sample_tariff_plan.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted successfully" in data["message"]
        mock_service.delete_tariff_plan.assert_called_once_with(sample_tariff_plan.id)


class TestUserTariffPlanEndpoints:
    """Tests for user tariff plan management endpoints."""
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_assign_plan_to_user(self, mock_service_class, client, sample_tariff_plan, sample_user_tariff_plan):
        """Test assigning a tariff plan to a user."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.assign_plan_to_user.return_value = sample_user_tariff_plan
        
        assignment_data = {
            "user_id": 1,
            "status": "active",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": None
        }
        
        # Execute
        response = client.post(f"/tariff/plans/{sample_tariff_plan.id}/assign", json=assignment_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "assigned successfully" in data["message"]
        assert data["user_plan_id"] == sample_user_tariff_plan.id
        assert data["user_id"] == sample_user_tariff_plan.user_id
        assert data["plan_id"] == sample_user_tariff_plan.tariff_plan_id
        mock_service.assign_plan_to_user.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_get_user_tariff_plan(self, mock_service_class, client, sample_user_tariff_plan, sample_tariff_plan):
        """Test getting a user's active tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.get_user_tariff_plan.return_value = sample_user_tariff_plan
        mock_service.get_tariff_plan.return_value = sample_tariff_plan
        
        # Execute
        response = client.get(f"/tariff/users/{sample_user_tariff_plan.user_id}/plan")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user_tariff_plan.user_id
        assert data["plan_id"] == sample_user_tariff_plan.tariff_plan_id
        assert data["status"] == sample_user_tariff_plan.status
        mock_service.get_user_tariff_plan.assert_called_once_with(sample_user_tariff_plan.user_id)
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_update_user_tariff_plan(self, mock_service_class, client, sample_user_tariff_plan):
        """Test updating a user's tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.update_user_tariff_plan.return_value = sample_user_tariff_plan
        
        update_data = {
            "status": "suspended",
            "end_date": (datetime.utcnow() + timedelta(days=15)).isoformat()
        }
        
        # Execute
        response = client.put(f"/tariff/users/{sample_user_tariff_plan.user_id}/plan/{sample_user_tariff_plan.tariff_plan_id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "updated successfully" in data["message"]
        assert data["user_plan_id"] == sample_user_tariff_plan.id
        assert data["user_id"] == sample_user_tariff_plan.user_id
        assert data["plan_id"] == sample_user_tariff_plan.tariff_plan_id
        assert "status" in data["updated_fields"]
        assert "end_date" in data["updated_fields"]
        mock_service.update_user_tariff_plan.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_cancel_user_tariff_plan(self, mock_service_class, client, sample_user_tariff_plan):
        """Test cancelling a user's tariff plan."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.cancel_user_tariff_plan.return_value = True
        
        # Execute
        response = client.delete(f"/tariff/users/{sample_user_tariff_plan.user_id}/plan")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cancelled successfully" in data["message"]
        assert data["user_id"] == sample_user_tariff_plan.user_id
        mock_service.cancel_user_tariff_plan.assert_called_once_with(sample_user_tariff_plan.user_id)


class TestUsageTrackingEndpoints:
    """Tests for usage tracking and policy enforcement endpoints."""
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_record_usage(self, mock_service_class, client):
        """Test recording usage data."""
        # Setup
        mock_service = mock_service_class.return_value
        usage_record = MagicMock(spec=UserUsageRecord)
        usage_record.id = 1
        usage_record.user_tariff_plan_id = 1
        usage_record.download_bytes = 1500000000  # 1.5 GB
        usage_record.upload_bytes = 500000000  # 500 MB
        usage_record.total_bytes = 2000000000  # 2 GB
        
        mock_service.record_usage.return_value = usage_record
        
        usage_data = {
            "user_tariff_plan_id": 1,
            "download_bytes": 1500000000,
            "upload_bytes": 500000000,
            "source": "radius",
            "session_id": "TEST-SESSION-123"
        }
        
        # Execute
        response = client.post("/tariff/usage/record", json=usage_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "recorded successfully" in data["message"]
        assert data["record_id"] == usage_record.id
        assert data["user_tariff_plan_id"] == usage_record.user_tariff_plan_id
        assert data["download_bytes"] == usage_record.download_bytes
        assert data["upload_bytes"] == usage_record.upload_bytes
        assert data["total_bytes"] == usage_record.total_bytes
        mock_service.record_usage.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_check_usage(self, mock_service_class, client, sample_user_tariff_plan, sample_tariff_plan):
        """Test checking a user's usage against their plan limits."""
        # Setup
        mock_service = mock_service_class.return_value
        
        # Create a mock response for check_usage
        check_result = MagicMock()
        check_result.user_id = sample_user_tariff_plan.user_id
        check_result.tariff_plan_id = sample_tariff_plan.id
        check_result.plan_name = sample_tariff_plan.name
        check_result.status = "ok"
        check_result.current_usage = sample_user_tariff_plan.data_used
        check_result.data_cap = sample_tariff_plan.data_cap
        check_result.percentage_used = (sample_user_tariff_plan.data_used / sample_tariff_plan.data_cap) * 100
        check_result.actions_triggered = []
        check_result.message = f"Using {sample_user_tariff_plan.data_used / (1024**3):.2f} GB of {sample_tariff_plan.data_cap / (1024**3):.2f} GB ({check_result.percentage_used:.1f}%)"
        
        mock_service.check_usage.return_value = check_result
        
        check_data = {
            "user_id": sample_user_tariff_plan.user_id,
            "download_bytes": 0,
            "upload_bytes": 0,
            "session_id": "TEST-SESSION-123"
        }
        
        # Execute
        response = client.post("/tariff/usage/check", json=check_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == check_result.user_id
        assert data["tariff_plan_id"] == check_result.tariff_plan_id
        assert data["plan_name"] == check_result.plan_name
        assert data["status"] == check_result.status
        assert data["current_usage"] == check_result.current_usage
        assert data["data_cap"] == check_result.data_cap
        assert data["percentage_used"] == check_result.percentage_used
        assert data["actions_triggered"] == check_result.actions_triggered
        assert data["message"] == check_result.message
        mock_service.check_usage.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_get_bandwidth_policy(self, mock_service_class, client, sample_user_tariff_plan, sample_tariff_plan):
        """Test getting the bandwidth policy for a user."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.get_user_tariff_plan.return_value = sample_user_tariff_plan
        mock_service.get_tariff_plan.return_value = sample_tariff_plan
        
        # Execute
        response = client.get(f"/tariff/users/{sample_user_tariff_plan.user_id}/bandwidth-policy")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user_tariff_plan.user_id
        assert data["download_speed"] == sample_tariff_plan.download_speed
        assert data["upload_speed"] == sample_tariff_plan.upload_speed
        assert data["is_throttled"] == sample_user_tariff_plan.is_throttled
        mock_service.get_user_tariff_plan.assert_called_once_with(sample_user_tariff_plan.user_id)
        mock_service.get_tariff_plan.assert_called_once_with(sample_user_tariff_plan.tariff_plan_id)
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_reset_usage_cycle(self, mock_service_class, client, sample_user_tariff_plan):
        """Test resetting a user's usage cycle."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.reset_usage_cycle.return_value = True
        
        # Execute
        response = client.post(f"/tariff/users/{sample_user_tariff_plan.user_id}/reset-cycle")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reset successfully" in data["message"]
        assert data["user_id"] == sample_user_tariff_plan.user_id
        mock_service.reset_usage_cycle.assert_called_once_with(sample_user_tariff_plan.user_id)
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_process_scheduled_changes(self, mock_service_class, client):
        """Test processing scheduled tariff plan changes."""
        # Setup
        mock_service = mock_service_class.return_value
        
        results = {
            "status": "success",
            "message": "Processed 3 of 5 scheduled changes",
            "total": 5,
            "processed": 3,
            "failed": 2,
            "errors": [
                "Error processing change 12: User not found",
                "Error processing change 15: Plan not found"
            ]
        }
        
        mock_service.process_scheduled_plan_changes.return_value = results
        
        # Execute
        response = client.post("/tariff/process-scheduled-changes")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == results["message"]
        assert data["results"]["total"] == results["total"]
        assert data["results"]["processed"] == results["processed"]
        assert data["results"]["failed"] == results["failed"]
        assert data["results"]["errors"] == results["errors"]
        mock_service.process_scheduled_plan_changes.assert_called_once()
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_calculate_overage(self, mock_service_class, client, sample_user_tariff_plan):
        """Test calculating overage fees."""
        # Setup
        mock_service = mock_service_class.return_value
        mock_service.calculate_overage_fee.return_value = 250.0
        
        overage_data = {
            "usage_mb": 550000  # 550 GB in MB
        }
        
        # Execute
        response = client.post(f"/tariff/users/{sample_user_tariff_plan.user_id}/calculate-overage", json=overage_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user_tariff_plan.user_id
        assert data["usage_mb"] == overage_data["usage_mb"]
        assert data["overage_fee"] == 250.0
        mock_service.calculate_overage_fee.assert_called_once_with(sample_user_tariff_plan.user_id, overage_data["usage_mb"])
    
    @patch("modules.tariff.endpoints.TariffService")
    def test_check_fup(self, mock_service_class, client, sample_user_tariff_plan, sample_tariff_plan):
        """Test checking if a user has crossed the FUP threshold."""
        # Setup
        mock_service = mock_service_class.return_value
        
        # Create a mock response for check_fup_threshold
        fup_result = MagicMock()
        fup_result.user_id = sample_user_tariff_plan.user_id
        fup_result.plan_id = sample_tariff_plan.id
        fup_result.fup_threshold = sample_tariff_plan.fup_threshold
        fup_result.current_usage = 410000000000  # 410 GB
        fup_result.threshold_exceeded = True
        fup_result.action = "throttle"
        fup_result.message = "FUP threshold exceeded. Connection will be throttled."
        
        mock_service.check_fup_threshold.return_value = fup_result
        
        check_data = {
            "user_id": sample_user_tariff_plan.user_id,
            "current_usage_bytes": 410000000000
        }
        
        # Execute
        response = client.post("/tariff/check-fup", json=check_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == fup_result.user_id
        assert data["plan_id"] == fup_result.plan_id
        assert data["fup_threshold"] == fup_result.fup_threshold
        assert data["current_usage"] == fup_result.current_usage
        assert data["threshold_exceeded"] == fup_result.threshold_exceeded
        assert data["action"] == fup_result.action
        assert data["message"] == fup_result.message
        mock_service.check_fup_threshold.assert_called_once()
