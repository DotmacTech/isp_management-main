"""
Tests for Token Management functionality.

This module tests token generation, validation, refresh, and blacklisting.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend_core.auth_service import AuthService
from backend_core.config import SECRET_KEY, ALGORITHM


def test_access_token_creation():
    """Test creating an access token."""
    # Test data
    user_id = 1
    username = "testuser"
    role = "user"
    
    # Create token data
    token_data = {
        "sub": username,
        "id": user_id,
        "role": role
    }
    
    # Create token
    token = AuthService.create_access_token(token_data)
    
    # Verify token is a string
    assert isinstance(token, str)
    
    # Decode and verify token contents
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == username
    assert decoded["id"] == user_id
    assert decoded["role"] == role
    assert "exp" in decoded


def test_access_token_with_custom_expiry():
    """Test creating an access token with custom expiry."""
    # Test data
    user_id = 1
    username = "testuser"
    role = "user"
    
    # Create token data
    token_data = {
        "sub": username,
        "id": user_id,
        "role": role
    }
    
    # Create token with custom expiry
    expires_delta = timedelta(minutes=5)
    token = AuthService.create_access_token(token_data, expires_delta)
    
    # Decode and verify token expiry
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    expiry_time = datetime.fromtimestamp(decoded["exp"])
    now = datetime.utcnow()
    
    # Verify expiry is approximately 5 minutes from now (with 10 second tolerance)
    assert (expiry_time - now).total_seconds() > 290  # 5 minutes - 10 seconds
    assert (expiry_time - now).total_seconds() < 310  # 5 minutes + 10 seconds


def test_refresh_token_creation():
    """Test creating a refresh token."""
    # Test data
    user_id = 1
    username = "testuser"
    
    # Create token data
    token_data = {
        "sub": username,
        "id": user_id,
        "token_type": "refresh"
    }
    
    # Create token with longer expiry for refresh token
    expires_delta = timedelta(days=7)
    token = AuthService.create_access_token(token_data, expires_delta)
    
    # Decode and verify token contents
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == username
    assert decoded["id"] == user_id
    assert decoded["token_type"] == "refresh"
    assert "exp" in decoded
    
    # Verify expiry is approximately 7 days from now
    expiry_time = datetime.fromtimestamp(decoded["exp"])
    now = datetime.utcnow()
    assert (expiry_time - now).days >= 6  # Allow for some processing time


@patch('backend_core.auth_service.redis_client')
def test_token_blacklisting(mock_redis):
    """Test blacklisting a token."""
    # Setup
    token = "test.jwt.token"
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    # Mock redis client
    mock_redis.set.return_value = True
    
    # Blacklist token
    result = AuthService.blacklist_token(token, expires_at)
    
    # Verify result
    assert result is True
    mock_redis.set.assert_called_once()


@patch('backend_core.auth_service.redis_client')
def test_token_blacklist_checking(mock_redis):
    """Test checking if a token is blacklisted."""
    # Setup
    token = "test.jwt.token"
    
    # Test when token is not blacklisted
    mock_redis.exists.return_value = False
    assert AuthService.is_token_blacklisted(token) is False
    
    # Test when token is blacklisted
    mock_redis.exists.return_value = True
    assert AuthService.is_token_blacklisted(token) is True


@patch('backend_core.auth_service.AuthService.is_token_blacklisted')
def test_token_validation(mock_is_blacklisted):
    """Test token validation."""
    # Setup
    user_id = 1
    username = "testuser"
    role = "user"
    
    # Create token data
    token_data = {
        "sub": username,
        "id": user_id,
        "role": role
    }
    
    # Create valid token
    token = AuthService.create_access_token(token_data)
    
    # Mock token not blacklisted
    mock_is_blacklisted.return_value = False
    
    # Validate token
    payload = AuthService.validate_token(token)
    
    # Verify payload
    assert payload is not None
    assert payload["sub"] == username
    assert payload["id"] == user_id
    assert payload["role"] == role
    
    # Test with blacklisted token
    mock_is_blacklisted.return_value = True
    
    # Validate should raise exception
    with pytest.raises(HTTPException) as excinfo:
        AuthService.validate_token(token)
    
    assert excinfo.value.status_code == 401
    assert "Token has been blacklisted" in str(excinfo.value.detail)


def test_expired_token_validation():
    """Test validation of expired tokens."""
    # Setup
    user_id = 1
    username = "testuser"
    role = "user"
    
    # Create token data
    token_data = {
        "sub": username,
        "id": user_id,
        "role": role
    }
    
    # Create token that's already expired
    expires_delta = timedelta(seconds=-1)
    token = AuthService.create_access_token(token_data, expires_delta)
    
    # Validate should raise exception
    with pytest.raises(HTTPException) as excinfo:
        AuthService.validate_token(token)
    
    assert excinfo.value.status_code == 401
    assert "Token has expired" in str(excinfo.value.detail)


def test_invalid_token_validation():
    """Test validation of invalid tokens."""
    # Test with malformed token
    with pytest.raises(HTTPException) as excinfo:
        AuthService.validate_token("invalid.token.format")
    
    assert excinfo.value.status_code == 401
    assert "Could not validate credentials" in str(excinfo.value.detail)
    
    # Test with token signed with wrong key
    user_id = 1
    username = "testuser"
    role = "user"
    
    payload = {
        "sub": username,
        "id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    
    wrong_token = jwt.encode(payload, "wrong_secret_key", algorithm=ALGORITHM)
    
    with pytest.raises(HTTPException) as excinfo:
        AuthService.validate_token(wrong_token)
    
    assert excinfo.value.status_code == 401
    assert "Could not validate credentials" in str(excinfo.value.detail)
