"""
Authentication utilities for customer portal access.
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import os

from backend_core.database import get_session
from backend_core.exceptions import AuthenticationException
from modules.customer.models import Customer

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_secret_key")
ALGORITHM = "HS256"

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="customers/portal/login",
    auto_error=False
)

async def get_current_customer(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get the current customer from a JWT token.
    
    Args:
        request: Request object
        token: JWT token
        session: Database session
        
    Returns:
        Customer data
        
    Raises:
        HTTPException: If token is invalid or customer not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is provided
    if not token:
        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
        else:
            raise credentials_exception
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validate token type
        if payload.get("type") != "customer":
            raise credentials_exception
        
        customer_id = int(payload.get("sub"))
        
        # Get customer from database
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise credentials_exception
            
        # Check if customer is active
        if customer.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer account is not active"
            )
            
        return {
            "id": customer.id,
            "uuid": str(customer.uuid),
            "customer_number": customer.customer_number,
            "portal_id": customer.portal_id,
            "customer_type": customer.customer_type.value,
            "is_authenticated": True
        }
        
    except JWTError:
        raise credentials_exception

async def get_current_active_customer(
    current_customer: Dict[str, Any] = Depends(get_current_customer)
) -> Dict[str, Any]:
    """
    Get the current active customer.
    
    Args:
        current_customer: Current customer data
        
    Returns:
        Customer data
        
    Raises:
        HTTPException: If customer is not active
    """
    if not current_customer.get("is_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return current_customer
