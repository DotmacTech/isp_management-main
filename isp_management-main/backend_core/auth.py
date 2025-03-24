"""
Authentication and authorization utilities for the ISP Management Platform.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import ValidationError

from isp_management.backend_core.database import get_session
from isp_management.backend_core.exceptions import AuthenticationException

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "admin": "Full system access",
        "customer_manager": "Manage customers",
        "customer_agent": "View and edit customer data",
        "billing_manager": "Manage billing",
        "billing_agent": "View and process billing",
        "support_manager": "Manage support",
        "support_agent": "Handle support tickets",
        "readonly": "Read-only access"
    }
)

class RoleChecker:
    """
    Role-based access control checker.
    """
    def __init__(self, required_roles: List[str]):
        """
        Initialize with required roles.
        
        Args:
            required_roles: List of roles that are allowed to access the endpoint
        """
        self.required_roles = required_roles
    
    def __call__(self, user: Dict[str, Any] = Depends(oauth2_scheme)) -> bool:
        """
        Check if user has required role.
        
        Args:
            user: Current user
            
        Returns:
            True if user has required role
            
        Raises:
            HTTPException: If user does not have required role
        """
        if not any(role in self.required_roles for role in user.get("roles", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return True

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get the current user from a JWT token.
    
    Args:
        security_scopes: Security scopes
        token: JWT token
        session: Database session
        
    Returns:
        User data
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Check token scopes
        token_scopes = payload.get("scopes", [])
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": authenticate_value},
                )
                
        # Get user from database
        # This is a placeholder - in a real application, you would query the database
        # For testing purposes, we'll just return the payload
        return {
            "id": user_id,
            "username": payload.get("username", ""),
            "email": payload.get("email", ""),
            "roles": payload.get("roles", []),
            "scopes": token_scopes
        }
        
    except (JWTError, ValidationError):
        raise credentials_exception

# Role-based access control dependencies
allow_admin = RoleChecker(["admin"])
allow_customer_manager = RoleChecker(["admin", "customer_manager"])
allow_customer_agent = RoleChecker(["admin", "customer_manager", "customer_agent"])
allow_billing_manager = RoleChecker(["admin", "billing_manager"])
allow_billing_agent = RoleChecker(["admin", "billing_manager", "billing_agent"])
allow_support_manager = RoleChecker(["admin", "support_manager"])
allow_support_agent = RoleChecker(["admin", "support_manager", "support_agent"])

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        User data if active
        
    Raises:
        HTTPException: If user is inactive
    """
    # This would typically check a is_active field in the user record
    # For this example, we'll just return the current user
    # In a real application, you might query the database to check if the user is active
    
    # Example of checking if user is active:
    # if not current_user.get("is_active", True):
    #     raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user

async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get the current user if they have admin role.
    
    Args:
        current_user: Current active user from token
        
    Returns:
        User data if admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Check if the user has the admin role
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return current_user

def require_permissions(required_permissions: List[str]):
    """
    Dependency for requiring specific permissions to access an endpoint.
    
    Args:
        required_permissions: List of permission strings required to access the endpoint
        
    Returns:
        Dependency function that checks if the user has the required permissions
    """
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        Check if the user has the required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if they have the required permissions
            
        Raises:
            HTTPException: If the user doesn't have the required permissions
        """
        if "permissions" not in current_user or not current_user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
            
        user_permissions = current_user["permissions"]
        
        # Admin role has all permissions
        if "admin" in user_permissions:
            return current_user
            
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
                
        return current_user
        
    return permission_checker

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt
