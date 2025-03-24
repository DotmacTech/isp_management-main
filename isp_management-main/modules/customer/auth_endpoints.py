"""
Authentication endpoints for customer portal access.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
import secrets

from backend_core.database import get_session
from backend_core.exceptions import AuthenticationException, ValidationException
from backend_core.utils.security import hash_password, verify_password
from backend_core.utils.hateoas import add_resource_links
from modules.customer.models import Customer
from modules.customer.schemas import CustomerResponse

# Initialize router
router = APIRouter(
    prefix="/portal",
    tags=["customer-portal"],
)

# Environment variables
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("CUSTOMER_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("CUSTOMER_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_secret_key")
ALGORITHM = "HS256"


# Exception handler
def handle_exceptions(func):
    """Decorator to handle common exceptions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AuthenticationException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValidationException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return wrapper


class CustomerLoginResponse(dict):
    """Response model for customer login."""
    pass


@router.post("/login", response_model=CustomerLoginResponse)
@handle_exceptions
async def customer_login(
    request: Request,
    response: Response,
    portal_id: str = Form(..., description="Customer portal ID"),
    password: str = Form(..., description="Customer password"),
    session: AsyncSession = Depends(get_session)
):
    """
    Login endpoint for customer portal access.
    
    Authenticates a customer using their portal ID and password.
    Returns access and refresh tokens for authenticated customers.
    """
    # Find customer by portal ID
    customer_result = await session.execute(
        select(Customer).where(Customer.portal_id == portal_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer or not customer.password_hash:
        raise AuthenticationException("Invalid portal ID or password")
    
    # Verify password
    if not verify_password(password, customer.password_hash):
        raise AuthenticationException("Invalid portal ID or password")
    
    # Check if customer is active
    if customer.status != "active":
        raise AuthenticationException("Customer account is not active")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Generate tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    from jose import jwt
    
    # Create access token
    access_token_data = {
        "sub": str(customer.id),
        "type": "customer",
        "portal_id": customer.portal_id,
        "session_id": session_id,
        "exp": datetime.utcnow() + access_token_expires
    }
    access_token = jwt.encode(access_token_data, JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    # Create refresh token
    refresh_token = secrets.token_urlsafe(64)
    refresh_token_data = {
        "sub": str(customer.id),
        "type": "customer",
        "token": refresh_token,
        "session_id": session_id,
        "exp": datetime.utcnow() + refresh_token_expires
    }
    encoded_refresh_token = jwt.encode(refresh_token_data, JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    # Set refresh token as HTTP-only cookie
    cookie_max_age = int(refresh_token_expires.total_seconds())
    response.set_cookie(
        key="customer_refresh_token",
        value=encoded_refresh_token,
        httponly=True,
        max_age=cookie_max_age,
        expires=cookie_max_age,
        samesite="lax",
        secure=request.url.scheme == "https"
    )
    
    # Create response with customer data and tokens
    customer_data = CustomerResponse.from_orm(customer).dict()
    
    login_response = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "customer": customer_data
    }
    
    # Add HATEOAS links
    login_response = add_resource_links(
        login_response,
        resource_id=customer.id,
        resource_type="customer",
        self_route=f"/customers/{customer.id}",
        parent_route="/customers"
    )
    
    return login_response


@router.post("/refresh-token", response_model=CustomerLoginResponse)
@handle_exceptions
async def refresh_customer_token(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="customer_refresh_token"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a new access token using a refresh token.
    
    The refresh token is sent as an HTTP-only cookie.
    """
    if not refresh_token:
        raise AuthenticationException("Refresh token is missing")
    
    from jose import jwt, JWTError
    
    try:
        # Decode refresh token
        payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validate token type
        if payload.get("type") != "customer":
            raise AuthenticationException("Invalid token type")
        
        customer_id = int(payload.get("sub"))
        session_id = payload.get("session_id")
        
        # Find customer
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise AuthenticationException("Customer not found")
        
        # Check if customer is active
        if customer.status != "active":
            raise AuthenticationException("Customer account is not active")
        
        # Generate new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        access_token_data = {
            "sub": str(customer.id),
            "type": "customer",
            "portal_id": customer.portal_id,
            "session_id": session_id,
            "exp": datetime.utcnow() + access_token_expires
        }
        access_token = jwt.encode(access_token_data, JWT_SECRET_KEY, algorithm=ALGORITHM)
        
        # Create response with customer data and new access token
        customer_data = CustomerResponse.from_orm(customer).dict()
        
        login_response = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "customer": customer_data
        }
        
        # Add HATEOAS links
        login_response = add_resource_links(
            login_response,
            resource_id=customer.id,
            resource_type="customer",
            self_route=f"/customers/{customer.id}",
            parent_route="/customers"
        )
        
        return login_response
        
    except JWTError:
        raise AuthenticationException("Invalid refresh token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def customer_logout(
    response: Response
):
    """
    Logout the customer by clearing the refresh token cookie.
    """
    # Clear refresh token cookie
    response.delete_cookie(
        key="customer_refresh_token",
        httponly=True,
        samesite="lax"
    )
    
    return None
