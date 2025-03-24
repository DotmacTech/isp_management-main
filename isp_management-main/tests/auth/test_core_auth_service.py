"""
Tests for AuthService functionality.

This module contains tests for:
- Password hashing
- JWT token creation
- User authentication
- Token blacklisting
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from backend_core.auth_service import AuthService


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = AuthService.get_password_hash("password123")
    user.is_active = True
    user.role = "user"
    user.failed_login_attempts = 0
    user.account_locked_until = None
    return user


def test_password_hashing():
    """Test password hashing and verification."""
    password = "mysecretpassword"
    hashed = AuthService.get_password_hash(password)
    
    # Verify the hash is different from the original password
    assert hashed != password
    
    # Verify the password against the hash
    assert AuthService.verify_password(password, hashed)
    
    # Verify an incorrect password fails
    assert not AuthService.verify_password("wrongpassword", hashed)


def test_create_access_token():
    """Test JWT token creation."""
    # Test data
    user_id = 1
    username = "testuser"
    role = "user"
    
    # Create token with default expiry
    token = AuthService.create_access_token(
        data={"sub": username, "id": user_id, "role": role}
    )
    
    # Verify token is a string
    assert isinstance(token, str)
    
    # Create token with custom expiry
    custom_expiry = timedelta(minutes=5)
    token = AuthService.create_access_token(
        data={"sub": username, "id": user_id, "role": role},
        expires_delta=custom_expiry
    )
    
    # Verify token is a string
    assert isinstance(token, str)


@patch("backend_core.auth_service.redis_client")
def test_authenticate_user(mock_redis, mock_user):
    """Test user authentication."""
    # Mock database session
    db_session = MagicMock()
    
    # Configure mock to return our test user
    db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Test successful authentication
    authenticated_user = AuthService.authenticate_user(
        db=db_session,
        username="testuser",
        password="password123"
    )
    
    # Verify the user was authenticated
    assert authenticated_user is not None
    assert authenticated_user.id == mock_user.id
    assert authenticated_user.username == mock_user.username
    
    # Test failed authentication with wrong password
    db_session.reset_mock()
    authenticated_user = AuthService.authenticate_user(
        db=db_session,
        username="testuser",
        password="wrongpassword"
    )
    
    # Verify authentication failed
    assert authenticated_user is None
    
    # Test authentication with locked account
    db_session.reset_mock()
    mock_user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
    authenticated_user = AuthService.authenticate_user(
        db=db_session,
        username="testuser",
        password="password123"
    )
    
    # Verify authentication failed due to locked account
    assert authenticated_user is None
    
    # Reset account lock for other tests
    mock_user.account_locked_until = None


@patch("backend_core.auth_service.redis_client")
def test_blacklist_token(mock_redis):
    """Test token blacklisting."""
    # Test data
    token = "test.jwt.token"
    
    # Configure mock
    mock_redis.set.return_value = True
    
    # Ensure TOKEN_BLACKLIST is initialized
    if not hasattr(AuthService, 'TOKEN_BLACKLIST'):
        AuthService.TOKEN_BLACKLIST = set()
    
    # Blacklist token
    AuthService.blacklist_token(token)
    
    # Verify token is blacklisted
    assert token in AuthService.TOKEN_BLACKLIST


@patch("backend_core.auth_service.redis_client")
def test_is_token_blacklisted(mock_redis):
    """Test checking if a token is blacklisted."""
    # Test data
    token = "test.jwt.token"
    
    # Ensure TOKEN_BLACKLIST is initialized
    if not hasattr(AuthService, 'TOKEN_BLACKLIST'):
        AuthService.TOKEN_BLACKLIST = set()
    
    # Test when token is not blacklisted
    AuthService.TOKEN_BLACKLIST.clear()
    assert not AuthService.is_token_blacklisted(token)
    
    # Blacklist the token
    AuthService.TOKEN_BLACKLIST.add(token)
    
    # Test when token is blacklisted
    assert AuthService.is_token_blacklisted(token)
    
    # Clean up
    AuthService.TOKEN_BLACKLIST.remove(token)
