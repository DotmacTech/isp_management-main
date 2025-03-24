"""
Tests for the authentication service.
"""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock
import pytest
import pyotp
from fastapi import HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext

# Add the root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the correct modules for patching
import modules.auth.services

# Import the classes we want to test
from modules.auth.services import AuthService
from modules.auth.schemas import UserCreate, UserUpdate
from backend_core.audit_log import AuditLogService
from backend_core.models import User

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# We need to access the actual module that's imported in the services/__init__.py file
auth_services_real_module = modules.auth.services.auth_services

# Apply patches at the module level to ensure they're applied before any tests run
@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """Apply patches to all external dependencies."""
    # Create a mock redis client
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_redis.exists.return_value = 0
    mock_redis.setex.return_value = True
    mock_redis.expire.return_value = True
    mock_redis.get.return_value = None
    mock_redis.lpush.return_value = 1
    mock_redis.setnx.return_value = 1
    mock_redis.delete.return_value = 1
    
    # Create a mock User model
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.hashed_password = pwd_context.hash("password")
    mock_user.is_active = True
    mock_user.mfa_enabled = False
    mock_user.failed_login_attempts = 0
    
    # Create mock User class
    mock_user_class = MagicMock()
    mock_user_class.return_value = mock_user
    
    # Configure query behavior
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.first.return_value = mock_user
    mock_user_class.query = mock_query
    
    # Mock Redis.from_url globally
    monkeypatch.setattr('redis.Redis.from_url', lambda url, **kwargs: mock_redis)
    
    # Mock the redis_client in the actual services module
    monkeypatch.setattr(auth_services_real_module, 'redis_client', mock_redis)
    
    # Mock User in backend_core.models
    monkeypatch.setattr('backend_core.models.User', mock_user_class)
    
    # Mock User in the actual services module
    monkeypatch.setattr(auth_services_real_module, 'User', mock_user_class)
    
    # Mock AuditLogService.log_auth_event
    monkeypatch.setattr(AuditLogService, 'log_auth_event', MagicMock(return_value=None))
    
    return {
        'redis': mock_redis,
        'user': mock_user,
        'user_class': mock_user_class
    }

# Mock database session
@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock_db = MagicMock()
    
    # Configure common query behavior
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    
    # Configure chained methods
    mock_query.filter.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.first.return_value = None
    
    # Configure commit and refresh
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    
    return mock_db

# Test user data
@pytest.fixture
def user_data():
    """Create test user data."""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        role="customer",
        password="Password123!",
        confirm_password="Password123!"
    )

# Test password hashing
def test_password_hashing():
    """Test password hashing."""
    password = "testpassword"
    hashed = AuthService.get_password_hash(password)
    assert AuthService.verify_password(password, hashed)
    assert not AuthService.verify_password("wrongpassword", hashed)

# Test JWT token creation and decoding
def test_token_creation_and_decoding():
    """Test JWT token creation and decoding."""
    data = {"sub": "testuser"}
    token = AuthService.create_access_token(data)
    decoded = AuthService.decode_token(token)
    assert decoded["sub"] == "testuser"

# Test token expiration
def test_token_expiration():
    """Test token expiration."""
    data = {"sub": "testuser"}
    token = AuthService.create_access_token(data, expires_delta=timedelta(seconds=1))
    # Wait for token to expire
    import time
    time.sleep(2)
    with pytest.raises(HTTPException) as excinfo:
        AuthService.decode_token(token)
    assert excinfo.value.status_code == 401
    assert "Could not validate credentials" in str(excinfo.value.detail)

# Test user creation
def test_create_user(mock_db, user_data, patch_dependencies):
    """Test user creation."""
    # Configure mock to return None for the query (user doesn't exist)
    mock_db.query.return_value.filter.return_value.first.side_effect = [None, None]
    
    # Get the mock user class
    mock_user_class = patch_dependencies['user_class']
    
    # Configure the mock user instance
    mock_user = patch_dependencies['user']
    mock_user.id = 1
    mock_user.username = user_data.username
    mock_user.email = user_data.email
    mock_user.role = user_data.role
    
    # Test creating a user
    user = AuthService.create_user(mock_db, user_data)
    
    # Verify the user was created with the correct attributes
    assert user.username == user_data.username
    assert user.email == user_data.email
    assert user.role == user_data.role
    
    # Verify that the commit and refresh methods were called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

# Test user creation with existing username
def test_create_user_existing_username(mock_db, user_data):
    """Test user creation with existing username."""
    # Configure mock to return a user for the username query
    mock_existing_user = MagicMock()
    mock_existing_user.username = user_data.username
    
    # First call returns an existing user, second call returns None
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_existing_user, None]
    
    with pytest.raises(HTTPException) as excinfo:
        AuthService.create_user(mock_db, user_data)
    
    assert excinfo.value.status_code == 400
    assert "Username already registered" in str(excinfo.value.detail)

# Test user creation with existing email
def test_create_user_existing_email(mock_db, user_data):
    """Test user creation with existing email."""
    # Configure mock to return None for the first query (username) and an existing user for the second query (email)
    mock_existing_user = MagicMock()
    mock_existing_user.username = "different_user"
    mock_existing_user.email = user_data.email
    
    # Use side_effect to handle the 'or_' condition in the query
    # This ensures the first call returns None, but the second mock has the matching email
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_existing_user]
    
    # Test the behavior
    with pytest.raises(HTTPException) as excinfo:
        AuthService.create_user(mock_db, user_data)
    
    assert excinfo.value.status_code == 400
    assert "Email already registered" in str(excinfo.value.detail)

# Test user authentication
def test_authenticate_user(mock_db):
    """Test user authentication."""
    # Create a mock user
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.mfa_enabled = False
    mock_user.failed_login_attempts = 0
    mock_user.hashed_password = pwd_context.hash("password")
    
    # Configure the mock to return the user
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock verify_password to return True
    with patch.object(AuthService, 'verify_password', return_value=True):
        # Test authenticating with correct credentials
        result_user, status = AuthService.authenticate_user(mock_db, "testuser", "password")
        
        # Verify the user was returned with success status
        assert result_user == mock_user
        assert status == "success"

# Test user authentication with incorrect password
def test_authenticate_user_incorrect_password(mock_db):
    """Test user authentication with incorrect password."""
    # Create a mock user
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.id = 1
    mock_user.is_active = True
    mock_user.failed_login_attempts = 0
    
    # Configure the mock to return the user for the initial query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock verify_password to return False and return a valid integer for increment_failed_login_attempts
    with patch.object(AuthService, 'verify_password', return_value=False), \
         patch.object(AuthService, 'increment_failed_login_attempts', return_value=1), \
         patch.object(AuditLogService, 'log_auth_event', return_value=None):
        # Test authenticating with incorrect password
        result_user, status = AuthService.authenticate_user(mock_db, "testuser", "wrongpassword")
        
        # Verify the return values indicate invalid credentials
        assert result_user == mock_user
        assert status == "invalid_credentials"

# Test user authentication for non-existent user
def test_authenticate_user_nonexistent(mock_db):
    """Test user authentication for non-existent user."""
    # Configure the mock to return None (user doesn't exist)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Test authenticating with a non-existent user
    result_user, status = AuthService.authenticate_user(mock_db, "nonexistent", "password")
    
    # Verify the return values indicate invalid credentials
    assert result_user is None
    assert status == "invalid_credentials"

# Test user update
def test_update_user(mock_db):
    """Test user update."""
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    
    # Configure the mock to return the user
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Create user update data
    user_update = UserUpdate(
        username="newusername",
        email="newemail@example.com"
    )
    
    # Mock necessary methods to avoid username check
    with patch.object(AuthService, 'get_user_by_id', return_value=mock_user), \
         patch.object(AuthService, 'get_user_by_username', return_value=None), \
         patch.object(AuthService, 'get_user_by_email', return_value=None):
        # Test updating a user
        updated_user = AuthService.update_user(mock_db, 1, user_update)
        
        # Verify the user attributes were updated
        assert updated_user.username == "newusername"
        assert updated_user.email == "newemail@example.com"
        
        # Verify that the commit was called
        mock_db.commit.assert_called_once()

# Test user update for non-existent user
def test_update_user_nonexistent(mock_db):
    """Test user update for non-existent user."""
    # Configure the mock to return None (user doesn't exist)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Create user update data
    user_update = UserUpdate(
        username="newusername",
        email="newemail@example.com"
    )
    
    with pytest.raises(HTTPException) as excinfo:
        AuthService.update_user(mock_db, 999, user_update)
    
    assert excinfo.value.status_code == 404
    assert "User not found" in str(excinfo.value.detail)

# Test password reset
def test_reset_password(mock_db):
    """Test password reset."""
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    
    # Configure the mock to return the user
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Test resetting a password
    success = AuthService.reset_password(mock_db, "test@example.com", "newpassword")
    
    # Verify the password was updated and we got success
    assert success is True
    assert mock_user.hashed_password is not None
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

# Test password reset for non-existent user
def test_reset_password_nonexistent(mock_db):
    """Test password reset for non-existent user."""
    # Configure the mock to return None (user doesn't exist)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # The real implementation returns False instead of raising an exception when user doesn't exist
    # So we should check for the return value, not an exception
    result = AuthService.reset_password(mock_db, "nonexistent@example.com", "newpassword")
    
    # Assert that the function returns False for non-existent user
    assert result is False

# Test password reset token
def test_password_reset_token():
    """Test password reset token."""
    email = "test@example.com"
    token = AuthService.create_password_reset_token(email)
    assert token is not None
    
    # Verify the token
    result_email = AuthService.verify_password_reset_token(token)
    assert result_email == email

# Test TOTP setup
def test_totp_setup():
    """Test TOTP setup."""
    # Generate a TOTP secret
    secret = AuthService.generate_totp_secret()
    assert secret is not None
    
    # Generate a TOTP URI
    uri = AuthService.generate_totp_uri(secret, "testuser")
    assert "otpauth://" in uri
    assert "testuser" in uri
    
    # Generate a QR code
    qr_code = AuthService.generate_qr_code(uri)
    assert qr_code.startswith("data:image/png;base64,")

# Test TOTP verification
def test_totp_verification():
    """Test TOTP verification."""
    # Generate a TOTP secret
    secret = AuthService.generate_totp_secret()
    
    # Generate a valid code using the secret
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # Test verification with a valid code
    assert AuthService.verify_totp(secret, valid_code)
    
    # Test verification with an invalid code
    assert not AuthService.verify_totp(secret, "000000")

# Test rate limiting
def test_rate_limiting(patch_dependencies):
    """Test rate limiting."""
    mock_redis = patch_dependencies['redis']
    
    # Configure mock for this specific test
    mock_redis.incr.side_effect = [3, 6]  # First call under limit, second over
    
    # Test when under the limit
    assert not AuthService.rate_limit_login_attempts("testuser", max_attempts=5)
    
    # Test when over the limit
    assert AuthService.rate_limit_login_attempts("testuser", max_attempts=5)

# Test token blacklisting
def test_token_blacklisting(patch_dependencies):
    """Test token blacklisting."""
    mock_redis = patch_dependencies['redis']
    token = "test_token"
    
    # Initially the token should not be blacklisted
    mock_redis.exists.return_value = 0
    assert not AuthService.is_token_blacklisted(token)
    
    # Blacklist the token
    AuthService.blacklist_token(token, 3600)
    
    # Now the token should be blacklisted
    mock_redis.exists.return_value = 1
    assert AuthService.is_token_blacklisted(token)
