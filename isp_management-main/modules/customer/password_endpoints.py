"""
Password management endpoints for customer portal access.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field, validator

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.utils.security import hash_password, verify_password
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import Customer
from modules.customer.auth_utils import get_current_active_customer

# Initialize router
router = APIRouter(
    prefix="/password",
    tags=["customer-password"],
)

# Role checkers
allow_admin = RoleChecker(["admin"])
allow_customer_manager = RoleChecker(["admin", "customer_manager"])


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
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return wrapper


# Password schemas
class SetPasswordRequest(BaseModel):
    """Schema for setting a customer's password."""
    password: str = Field(..., min_length=8, description="New password")
    
    @validator('password')
    def password_complexity(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain at least one uppercase letter, one lowercase letter, and one digit")
        
        return v


class ChangePasswordRequest(BaseModel):
    """Schema for changing a customer's password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def password_complexity(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain at least one uppercase letter, one lowercase letter, and one digit")
        
        return v


class PasswordResponse(BaseModel):
    """Response for password operations."""
    message: str


@router.post("/{customer_id}/set", response_model=PasswordResponse)
@handle_exceptions
async def set_customer_password(
    password_data: SetPasswordRequest,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """
    Set a customer's password (admin/manager only).
    
    This endpoint allows administrators and customer managers to set a password
    for a customer without requiring the current password.
    """
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Hash the password
    password_hash = hash_password(password_data.password)
    
    # Update the customer's password
    await session.execute(
        update(Customer)
        .where(Customer.id == customer_id)
        .values(password_hash=password_hash)
    )
    
    await session.commit()
    
    return {"message": "Password set successfully"}


@router.post("/portal/change", response_model=PasswordResponse)
@handle_exceptions
async def change_own_password(
    password_data: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """
    Change the current customer's password.
    
    This endpoint allows customers to change their own password.
    The current password is required for verification.
    """
    # Get customer from database
    customer_result = await session.execute(
        select(Customer).where(Customer.id == current_customer["id"])
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException("Customer not found")
    
    # Verify current password
    if not verify_password(password_data.current_password, customer.password_hash):
        raise ValidationException("Current password is incorrect")
    
    # Hash the new password
    password_hash = hash_password(password_data.new_password)
    
    # Update the customer's password
    await session.execute(
        update(Customer)
        .where(Customer.id == customer.id)
        .values(password_hash=password_hash)
    )
    
    await session.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/portal/reset-request", status_code=status.HTTP_202_ACCEPTED)
@handle_exceptions
async def request_password_reset(
    portal_id: str = Body(..., embed=True, description="Customer portal ID"),
    session: AsyncSession = Depends(get_session)
):
    """
    Request a password reset for a customer.
    
    This endpoint initiates the password reset process by sending
    a reset token to the customer's primary email address.
    """
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.portal_id == portal_id)
    )
    customer = customer_result.scalars().first()
    
    # Always return 202 Accepted to prevent user enumeration
    if not customer:
        return {"message": "If a matching account is found, a password reset email will be sent"}
    
    # In a real implementation, you would:
    # 1. Generate a reset token
    # 2. Store it in the database with an expiration time
    # 3. Send an email with a link containing the token
    
    # For now, we'll just return a success message
    return {"message": "If a matching account is found, a password reset email will be sent"}


@router.post("/portal/reset-confirm", response_model=PasswordResponse)
@handle_exceptions
async def confirm_password_reset(
    token: str = Body(..., description="Password reset token"),
    new_password: str = Body(..., min_length=8, description="New password"),
    session: AsyncSession = Depends(get_session)
):
    """
    Confirm a password reset for a customer.
    
    This endpoint completes the password reset process by verifying
    the reset token and setting a new password for the customer.
    """
    # In a real implementation, you would:
    # 1. Verify the reset token
    # 2. Check if it's expired
    # 3. Find the associated customer
    # 4. Set the new password
    
    # For now, we'll just return a mock response
    return {"message": "Password reset successfully"}
