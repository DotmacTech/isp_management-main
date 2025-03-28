"""
API endpoints for the Customer Management Module.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import (
    NotFoundException, 
    ValidationException, 
    DuplicateException, 
    AuthenticationException
)
from modules.customer.models import (
    CustomerType,
    CustomerStatus,
    SubscriptionState,
    DocumentType,
    VerificationStatus,
    AddressType,
    ContactType,
    CommunicationType
)
from modules.customer.services import CustomerService
from modules.customer.communication_service import CommunicationService
from modules.customer.verification_service import VerificationService
from modules.customer.document_service import CustomerDocumentService
from modules.customer.schemas import (
    # Customer schemas
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerDetailResponse,
    
    # Address schemas
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    
    # Contact schemas
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    
    # Communication preference schemas
    CommunicationPreferenceCreate,
    CommunicationPreferenceUpdate,
    CommunicationPreferenceResponse,
    
    # Document schemas
    DocumentCreate,
    DocumentResponse,
    DocumentVerificationUpdate,
    
    # Note schemas
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    
    # Tag schemas
    TagCreate,
    TagUpdate,
    TagResponse,
    
    # Verification schemas
    EmailVerificationCreate,
    EmailVerificationResponse,
    EmailVerificationResult,
    
    # Subscription schemas
    SubscriptionStateUpdate
)

# Initialize router
router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        401: {"description": "Unauthorized"},
    },
)

# Initialize services
customer_service = CustomerService()
communication_service = CommunicationService()
verification_service = VerificationService()
document_service = CustomerDocumentService()  # Use default temp directory

# Role checkers
allow_admin = RoleChecker(["admin"])
allow_customer_manager = RoleChecker(["admin", "customer_manager"])
allow_customer_agent = RoleChecker(["admin", "customer_manager", "customer_agent"])
allow_billing = RoleChecker(["admin", "customer_manager", "billing"])


# Exception handler
def handle_exceptions(func):
    """Decorator to handle common exceptions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except DuplicateException as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except AuthenticationException as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return wrapper


# Customer endpoints
@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_customer(
    customer_data: CustomerCreate,
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new customer."""
    customer = await customer_service.create_customer(
        session=session,
        **customer_data.dict()
    )
    await session.commit()
    return CustomerResponse.from_orm(customer)


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
@handle_exceptions
async def get_customer(
    customer_id: int = Path(..., description="Customer ID"),
    include_addresses: bool = Query(False, description="Include customer addresses"),
    include_contacts: bool = Query(False, description="Include customer contacts"),
    include_preferences: bool = Query(False, description="Include communication preferences"),
    include_documents: bool = Query(False, description="Include customer documents"),
    include_notes: bool = Query(False, description="Include customer notes"),
    include_tags: bool = Query(False, description="Include customer tags"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a customer by ID."""
    customer = await customer_service.get_customer(
        session=session,
        customer_id=customer_id,
        include_addresses=include_addresses,
        include_contacts=include_contacts,
        include_preferences=include_preferences,
        include_documents=include_documents,
        include_notes=include_notes,
        include_tags=include_tags
    )
    return CustomerDetailResponse.from_orm(customer)


@router.get("/", response_model=CustomerListResponse)
@handle_exceptions
async def get_customers(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    customer_type: Optional[CustomerType] = Query(None, description="Filter by customer type"),
    status: Optional[CustomerStatus] = Query(None, description="Filter by customer status"),
    subscription_state: Optional[SubscriptionState] = Query(None, description="Filter by subscription state"),
    search: Optional[str] = Query(None, description="Search term for name, email, phone, or customer number"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    include_addresses: bool = Query(False, description="Include customer addresses"),
    include_contacts: bool = Query(False, description="Include customer contacts"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a list of customers with optional filtering."""
    customers, total_count = await customer_service.get_customers(
        session=session,
        skip=skip,
        limit=limit,
        customer_type=customer_type,
        status=status,
        subscription_state=subscription_state,
        search=search,
        tag_ids=tag_ids,
        include_addresses=include_addresses,
        include_contacts=include_contacts
    )
    return CustomerListResponse(
        items=[CustomerResponse.from_orm(customer) for customer in customers],
        total=total_count,
        skip=skip,
        limit=limit
    )


@router.put("/{customer_id}", response_model=CustomerResponse)
@handle_exceptions
async def update_customer(
    customer_data: CustomerUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a customer."""
    customer = await customer_service.update_customer(
        session=session,
        customer_id=customer_id,
        **customer_data.dict(exclude_unset=True)
    )
    await session.commit()
    return CustomerResponse.from_orm(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_customer(
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Delete a customer."""
    await customer_service.delete_customer(
        session=session,
        customer_id=customer_id
    )
    await session.commit()
    return None


@router.put("/{customer_id}/subscription-state", response_model=CustomerResponse)
@handle_exceptions
async def update_subscription_state(
    state_data: SubscriptionStateUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Update a customer's subscription state."""
    customer = await customer_service.change_subscription_state(
        session=session,
        customer_id=customer_id,
        new_state=state_data.subscription_state,
        update_dates=state_data.update_dates
    )
    await session.commit()
    return CustomerResponse.from_orm(customer)


@router.post("/{customer_id}/tags/{tag_id}", response_model=CustomerResponse)
@handle_exceptions
async def add_tag_to_customer(
    customer_id: int = Path(..., description="Customer ID"),
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Add a tag to a customer."""
    customer = await customer_service.add_tag_to_customer(
        session=session,
        customer_id=customer_id,
        tag_id=tag_id
    )
    await session.commit()
    return CustomerResponse.from_orm(customer)


@router.delete("/{customer_id}/tags/{tag_id}", response_model=CustomerResponse)
@handle_exceptions
async def remove_tag_from_customer(
    customer_id: int = Path(..., description="Customer ID"),
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Remove a tag from a customer."""
    customer = await customer_service.remove_tag_from_customer(
        session=session,
        customer_id=customer_id,
        tag_id=tag_id
    )
    await session.commit()
    return CustomerResponse.from_orm(customer)


# Import additional endpoint modules
from modules.customer.address_endpoints import router as address_router
from modules.customer.contact_endpoints import router as contact_router
from modules.customer.communication_preference_endpoints import router as communication_preference_router
from modules.customer.document_endpoints import router as document_router
from modules.customer.note_endpoints import router as note_router
from modules.customer.tag_endpoints import router as tag_router
from modules.customer.custom_field_endpoints import router as custom_field_router
from modules.customer.contact_method_endpoints import router as contact_method_router
from modules.customer.auth_endpoints import router as auth_router
from modules.customer.portal_endpoints import router as portal_router
from modules.customer.password_endpoints import router as password_router

# Include routers
router.include_router(address_router)
router.include_router(contact_router)
router.include_router(communication_preference_router)
router.include_router(document_router)
router.include_router(note_router)
router.include_router(tag_router)
router.include_router(custom_field_router)
router.include_router(contact_method_router)
router.include_router(portal_router)
router.include_router(password_router)

# Include auth router at the module level
from fastapi import APIRouter
customer_module_router = APIRouter(prefix="/customers")
customer_module_router.include_router(router)
customer_module_router.include_router(auth_router)
customer_module_router.include_router(portal_router)
customer_module_router.include_router(password_router)

# Update the customer_router in the __init__ module to avoid circular imports
import modules.customer
isp_management.modules.customer.customer_router = customer_module_router
