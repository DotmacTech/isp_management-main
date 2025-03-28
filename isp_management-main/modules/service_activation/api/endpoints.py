"""
API endpoints for the Service Activation Module.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ServiceException
from modules.service_activation.models import ActivationStatus
from modules.service_activation.schemas import (
    ServiceActivationCreate,
    ServiceActivationUpdate,
    ServiceActivationResponse,
    ActivationStepResponse,
    ActivationLogResponse,
    PrerequisiteCheckResult
)
from modules.service_activation.services import ActivationService

# Initialize router
router = APIRouter(
    prefix="/service-activations",
    tags=["service-activations"],
    responses={404: {"description": "Not found"}}
)

# Role-based access control
allow_admin = RoleChecker(["admin"])
allow_service_manager = RoleChecker(["admin", "service_manager"])
allow_customer_service = RoleChecker(["admin", "service_manager", "customer_service"])


# Exception handling decorator
def handle_exceptions(func):
    """Decorator to handle common exceptions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ServiceException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            # Log the exception
            import logging
            logging.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again later."
            )
    return wrapper


# Service Activation endpoints
@router.post("/", response_model=ServiceActivationResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_service_activation(
    activation_data: ServiceActivationCreate,
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_service_manager)
):
    """
    Create a new service activation.
    
    This endpoint initiates the process of activating a service for a customer.
    It creates the activation record and sets up the workflow steps.
    """
    service = ActivationService(session)
    activation = await service.create_activation(activation_data)
    return activation


@router.get("/{activation_id}", response_model=ServiceActivationResponse)
@handle_exceptions
async def get_service_activation(
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_customer_service)
):
    """
    Get a service activation by ID.
    
    This endpoint retrieves details about a specific service activation,
    including its status, steps, and logs.
    """
    service = ActivationService(session)
    activation = await service.get_activation(activation_id)
    return activation


@router.put("/{activation_id}", response_model=ServiceActivationResponse)
@handle_exceptions
async def update_service_activation(
    update_data: ServiceActivationUpdate,
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_service_manager)
):
    """
    Update a service activation.
    
    This endpoint allows updating certain properties of a service activation,
    such as its status, payment verification, or metadata.
    """
    service = ActivationService(session)
    activation = await service.update_activation(activation_id, update_data)
    return activation


@router.delete("/{activation_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_service_activation(
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_admin)
):
    """
    Delete a service activation.
    
    This endpoint permanently deletes a service activation record.
    This should only be used for cleanup of failed or test activations.
    """
    service = ActivationService(session)
    await service.delete_activation(activation_id)
    return None


@router.post("/{activation_id}/start", response_model=Dict[str, Any])
@handle_exceptions
async def start_service_activation(
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_service_manager)
):
    """
    Start the service activation workflow.
    
    This endpoint begins the execution of the service activation workflow,
    which will process all the steps required to activate the service.
    """
    service = ActivationService(session)
    success = await service.start_activation(activation_id)
    
    return {
        "success": success,
        "message": "Service activation workflow started successfully" if success else "Failed to start service activation workflow"
    }


@router.get("/{activation_id}/prerequisites", response_model=PrerequisiteCheckResult)
@handle_exceptions
async def check_prerequisites(
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_customer_service)
):
    """
    Check prerequisites for a service activation.
    
    This endpoint checks if all prerequisites are met for activating the service,
    such as customer eligibility, location serviceability, etc.
    """
    service = ActivationService(session)
    result = await service.check_prerequisites(activation_id)
    return result


@router.get("/{activation_id}/steps", response_model=List[ActivationStepResponse])
@handle_exceptions
async def get_activation_steps(
    activation_id: int = Path(..., description="The ID of the service activation"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_customer_service)
):
    """
    Get all steps for a service activation.
    
    This endpoint retrieves all the steps in the workflow for a specific service activation,
    including their status, order, and dependencies.
    """
    service = ActivationService(session)
    steps = await service.get_activation_steps(activation_id)
    return steps


@router.get("/customer/{customer_id}", response_model=List[ServiceActivationResponse])
@handle_exceptions
async def get_customer_activations(
    customer_id: int = Path(..., description="The ID of the customer"),
    session: AsyncSession = Depends(get_session),
    _: Dict = Depends(allow_customer_service)
):
    """
    Get all activations for a customer.
    
    This endpoint retrieves all service activations for a specific customer,
    ordered by creation date (newest first).
    """
    service = ActivationService(session)
    activations = await service.get_customer_activations(customer_id)
    return activations
