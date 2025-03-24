"""
Core authentication utilities for the ISP Management Platform.

This module provides authentication utilities that are used across
different modules of the ISP Management Platform.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend_core.auth import get_current_user as backend_get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current user from the JWT token.
    
    This is a wrapper around the backend_core.auth.get_current_user function
    to maintain compatibility with the modules.core.auth import path.
    
    Args:
        token: JWT token.
    
    Returns:
        Dictionary containing user information.
    
    Raises:
        HTTPException: If the token is invalid or expired.
    """
    return backend_get_current_user(token)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password.
    
    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Get a password hash.
    
    Args:
        password: Plain text password.
    
    Returns:
        Hashed password.
    """
    return pwd_context.hash(password)


def check_permissions(user: Dict[str, Any], required_permissions: list) -> bool:
    """
    Check if a user has the required permissions.
    
    Args:
        user: Dictionary containing user information.
        required_permissions: List of required permissions.
    
    Returns:
        True if the user has all required permissions, False otherwise.
    """
    # Admin users have all permissions
    if user.get("is_admin", False):
        return True
    
    # Get user permissions
    user_permissions = user.get("permissions", [])
    
    # Check if the user has all required permissions
    return all(perm in user_permissions for perm in required_permissions)
