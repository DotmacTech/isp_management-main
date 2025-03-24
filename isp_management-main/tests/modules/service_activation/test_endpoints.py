"""
Unit tests for the Service Activation Module API endpoints.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.app import app
from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from modules.service_activation.models import (
    ServiceActivation,
    ActivationStep,
    ActivationStatus,
    StepStatus
)
from modules.service_activation.schemas import (
    ServiceActivationCreate,
    ServiceActivationUpdate,
    PrerequisiteCheckResult
)
from modules.service_activation.services import ActivationService
from backend_core.exceptions import NotFoundException, ServiceException


# Mock dependencies
@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_activation_service():
    """Create a mock ActivationService."""
    return AsyncMock(spec=ActivationService)


@pytest.fixture
def mock_current_user():
    """Return a mock user with admin role."""
    return {"id": 1, "username": "admin", "email": "admin@example.com", "roles": ["admin"]}


@pytest.fixture
def client(mock_session, mock_activation_service, mock_current_user):
    """Create a test client with mocked dependencies."""
    # Override dependencies
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[RoleChecker] = lambda allowed_roles: lambda: None
    
    # Mock the ActivationService class
    with patch('isp_management.modules.service_activation.endpoints.ActivationService', 
               return_value=mock_activation_service):
        yield TestClient(app)
    
    # Clean up
    app.dependency_overrides = {}


@pytest.fixture
def sample_activation():
    """Sample ServiceActivation instance."""
    return ServiceActivation(
        id=1,
        customer_id=1,
        service_id=2,
        tariff_id=3,
        status=ActivationStatus.PENDING,
        payment_verified=False,
        prerequisites_checked=True,
        metadata={"location": "New York", "connection_type": "Fiber"},
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )


@pytest.fixture
def sample_steps():
    """Sample ActivationStep instances."""
    return [
        ActivationStep(
            id=1,
            activation_id=1,
            step_name="verify_payment",
            step_order=0,
            status=StepStatus.PENDING,
            description="Verify payment for the service",
            max_retries=3,
            retry_count=0,
            is_rollback_step=False,
            depends_on_step_id=None,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00"
        ),
        ActivationStep(
            id=2,
            activation_id=1,
            step_name="create_radius_account",
            step_order=1,
            status=StepStatus.PENDING,
            description="Create RADIUS account for the customer",
            max_retries=3,
            retry_count=0,
            is_rollback_step=False,
            depends_on_step_id=1,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00"
        )
    ]


# Tests
def test_create_service_activation(client, mock_activation_service, sample_activation):
    """Test creating a service activation."""
    # Setup
    mock_activation_service.create_activation.return_value = sample_activation
    
    # Execute
    response = client.post(
        "/service-activations/",
        json={
            "customer_id": 1,
            "service_id": 2,
            "tariff_id": 3,
            "metadata": {"location": "New York", "connection_type": "Fiber"}
        }
    )
    
    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["customer_id"] == 1
    assert response.json()["service_id"] == 2
    assert response.json()["status"] == "PENDING"
    mock_activation_service.create_activation.assert_called_once()


def test_get_service_activation(client, mock_activation_service, sample_activation):
    """Test getting a service activation by ID."""
    # Setup
    mock_activation_service.get_activation.return_value = sample_activation
    
    # Execute
    response = client.get("/service-activations/1")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 1
    assert response.json()["customer_id"] == 1
    assert response.json()["service_id"] == 2
    mock_activation_service.get_activation.assert_called_once_with(1)


def test_get_service_activation_not_found(client, mock_activation_service):
    """Test getting a non-existent service activation."""
    # Setup
    mock_activation_service.get_activation.side_effect = NotFoundException("Not found")
    
    # Execute
    response = client.get("/service-activations/999")
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Not found" in response.json()["detail"]


def test_update_service_activation(client, mock_activation_service, sample_activation):
    """Test updating a service activation."""
    # Setup
    updated_activation = sample_activation
    updated_activation.status = ActivationStatus.IN_PROGRESS
    updated_activation.payment_verified = True
    
    mock_activation_service.update_activation.return_value = updated_activation
    
    # Execute
    response = client.put(
        "/service-activations/1",
        json={
            "status": "IN_PROGRESS",
            "payment_verified": True
        }
    )
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["payment_verified"] is True
    mock_activation_service.update_activation.assert_called_once()


def test_delete_service_activation(client, mock_activation_service):
    """Test deleting a service activation."""
    # Setup
    mock_activation_service.delete_activation.return_value = None
    
    # Execute
    response = client.delete("/service-activations/1")
    
    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_activation_service.delete_activation.assert_called_once_with(1)


def test_start_service_activation(client, mock_activation_service):
    """Test starting a service activation workflow."""
    # Setup
    mock_activation_service.start_activation.return_value = True
    
    # Execute
    response = client.post("/service-activations/1/start")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    mock_activation_service.start_activation.assert_called_once_with(1)


def test_start_service_activation_error(client, mock_activation_service):
    """Test starting a service activation with error."""
    # Setup
    mock_activation_service.start_activation.side_effect = ServiceException("Invalid status")
    
    # Execute
    response = client.post("/service-activations/1/start")
    
    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid status" in response.json()["detail"]


def test_check_prerequisites(client, mock_activation_service):
    """Test checking prerequisites for a service activation."""
    # Setup
    mock_activation_service.check_prerequisites.return_value = PrerequisiteCheckResult(
        passed=True,
        message="All prerequisites checked successfully"
    )
    
    # Execute
    response = client.get("/service-activations/1/prerequisites")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["passed"] is True
    assert response.json()["message"] == "All prerequisites checked successfully"
    mock_activation_service.check_prerequisites.assert_called_once_with(1)


def test_get_activation_steps(client, mock_activation_service, sample_steps):
    """Test getting all steps for a service activation."""
    # Setup
    mock_activation_service.get_activation_steps.return_value = sample_steps
    
    # Execute
    response = client.get("/service-activations/1/steps")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    assert response.json()[0]["step_name"] == "verify_payment"
    assert response.json()[1]["step_name"] == "create_radius_account"
    mock_activation_service.get_activation_steps.assert_called_once_with(1)


def test_get_customer_activations(client, mock_activation_service, sample_activation):
    """Test getting all activations for a customer."""
    # Setup
    mock_activation_service.get_customer_activations.return_value = [sample_activation]
    
    # Execute
    response = client.get("/service-activations/customer/1")
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["customer_id"] == 1
    assert response.json()[0]["service_id"] == 2
    mock_activation_service.get_customer_activations.assert_called_once_with(1)
