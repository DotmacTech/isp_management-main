"""
Unit tests for the Service Activation Module services.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from modules.service_activation.models import (
    ServiceActivation,
    ActivationStep,
    ActivationLog,
    ActivationStatus,
    StepStatus
)
from modules.service_activation.schemas import (
    ServiceActivationCreate,
    ServiceActivationUpdate,
    WorkflowDefinition
)
from modules.service_activation.services import ActivationService
from backend_core.exceptions import NotFoundException, ServiceException


# Fixtures
@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_workflow_engine():
    """Create a mock workflow engine."""
    engine = AsyncMock()
    engine.execute_workflow = AsyncMock(return_value=True)
    engine.register_step_handler = MagicMock()
    engine.register_rollback_handler = MagicMock()
    return engine


@pytest.fixture
def activation_service(mock_session, mock_workflow_engine):
    """Create an ActivationService instance with mock dependencies."""
    with patch('isp_management.modules.service_activation.services.WorkflowEngine', 
               return_value=mock_workflow_engine):
        service = ActivationService(mock_session)
        return service


@pytest.fixture
def sample_activation_data():
    """Sample data for creating a service activation."""
    return ServiceActivationCreate(
        customer_id=1,
        service_id=2,
        tariff_id=3,
        metadata={"location": "New York", "connection_type": "Fiber"}
    )


@pytest.fixture
def sample_activation():
    """Sample ServiceActivation instance."""
    return ServiceActivation(
        id=1,
        customer_id=1,
        service_id=2,
        tariff_id=3,
        status=ActivationStatus.PENDING,
        metadata={"location": "New York", "connection_type": "Fiber"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
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
            max_retries=3
        ),
        ActivationStep(
            id=2,
            activation_id=1,
            step_name="create_radius_account",
            step_order=1,
            status=StepStatus.PENDING,
            description="Create RADIUS account for the customer",
            max_retries=3,
            depends_on_step_id=1
        )
    ]


# Tests
@pytest.mark.asyncio
async def test_create_activation(activation_service, mock_session, sample_activation_data, sample_activation):
    """Test creating a service activation."""
    # Setup
    mock_session.add = MagicMock()
    mock_session.refresh.return_value = None
    
    # Mock the execute response to return the sample activation
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = sample_activation
    mock_session.execute.return_value = mock_result
    
    # Mock the _get_workflow_for_service method
    activation_service._get_workflow_for_service = AsyncMock(return_value=WorkflowDefinition(
        name="Test Workflow",
        description="Test workflow for unit tests",
        steps=[
            {
                "name": "verify_payment",
                "description": "Verify payment for the service",
                "max_retries": 3
            },
            {
                "name": "create_radius_account",
                "description": "Create RADIUS account for the customer",
                "max_retries": 3,
                "depends_on": None
            }
        ],
        rollback_steps=[]
    ))
    
    # Execute
    result = await activation_service.create_activation(sample_activation_data)
    
    # Assert
    assert mock_session.add.call_count >= 1  # At least one add call for the activation
    assert mock_session.commit.call_count >= 1
    assert mock_session.refresh.call_count >= 1
    assert result.customer_id == sample_activation_data.customer_id
    assert result.service_id == sample_activation_data.service_id
    assert result.tariff_id == sample_activation_data.tariff_id
    assert result.status == ActivationStatus.PENDING


@pytest.mark.asyncio
async def test_get_activation(activation_service, mock_session, sample_activation):
    """Test getting a service activation by ID."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = sample_activation
    mock_session.execute.return_value = mock_result
    
    # Execute
    result = await activation_service.get_activation(1)
    
    # Assert
    mock_session.execute.assert_called_once()
    assert result.id == sample_activation.id
    assert result.customer_id == sample_activation.customer_id
    assert result.service_id == sample_activation.service_id


@pytest.mark.asyncio
async def test_get_activation_not_found(activation_service, mock_session):
    """Test getting a non-existent service activation."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Execute and Assert
    with pytest.raises(NotFoundException):
        await activation_service.get_activation(999)


@pytest.mark.asyncio
async def test_update_activation(activation_service, mock_session, sample_activation):
    """Test updating a service activation."""
    # Setup
    activation_service.get_activation = AsyncMock(return_value=sample_activation)
    
    update_data = ServiceActivationUpdate(
        status=ActivationStatus.IN_PROGRESS,
        payment_verified=True,
        prerequisites_checked=True,
        metadata={"updated": True}
    )
    
    # Execute
    result = await activation_service.update_activation(1, update_data)
    
    # Assert
    assert mock_session.commit.called
    assert result.status == ActivationStatus.IN_PROGRESS
    assert result.payment_verified is True
    assert result.prerequisites_checked is True
    assert result.metadata == {"updated": True}


@pytest.mark.asyncio
async def test_delete_activation(activation_service, mock_session, sample_activation):
    """Test deleting a service activation."""
    # Setup
    activation_service.get_activation = AsyncMock(return_value=sample_activation)
    
    # Execute
    await activation_service.delete_activation(1)
    
    # Assert
    mock_session.delete.assert_called_once_with(sample_activation)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_start_activation(activation_service, mock_session, mock_workflow_engine, sample_activation):
    """Test starting a service activation workflow."""
    # Setup
    activation_service.get_activation = AsyncMock(return_value=sample_activation)
    
    # Execute
    result = await activation_service.start_activation(1)
    
    # Assert
    mock_workflow_engine.execute_workflow.assert_called_once_with(1)
    assert result is True


@pytest.mark.asyncio
async def test_start_activation_invalid_status(activation_service, mock_session, sample_activation):
    """Test starting a service activation with invalid status."""
    # Setup
    sample_activation.status = ActivationStatus.COMPLETED
    activation_service.get_activation = AsyncMock(return_value=sample_activation)
    
    # Execute and Assert
    with pytest.raises(ServiceException):
        await activation_service.start_activation(1)


@pytest.mark.asyncio
async def test_get_activation_steps(activation_service, mock_session, sample_steps):
    """Test getting all steps for a service activation."""
    # Setup
    activation_service.get_activation = AsyncMock()  # Just to verify activation exists
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = sample_steps
    mock_session.execute.return_value = mock_result
    
    # Execute
    result = await activation_service.get_activation_steps(1)
    
    # Assert
    activation_service.get_activation.assert_called_once_with(1)
    mock_session.execute.assert_called_once()
    assert len(result) == 2
    assert result[0].step_name == "verify_payment"
    assert result[1].step_name == "create_radius_account"


@pytest.mark.asyncio
async def test_get_customer_activations(activation_service, mock_session, sample_activation):
    """Test getting all activations for a customer."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [sample_activation]
    mock_session.execute.return_value = mock_result
    
    # Execute
    result = await activation_service.get_customer_activations(1)
    
    # Assert
    mock_session.execute.assert_called_once()
    assert len(result) == 1
    assert result[0].customer_id == 1
    assert result[0].service_id == 2
