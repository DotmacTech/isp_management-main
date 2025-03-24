"""
Tests for Multi-Factor Authentication core functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pyotp

# Import the MFA manager and shared models
from backend_core.mfa import MFAManager
from backend_core.auth_models import MFADeviceToken, User

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    
    # Mock user query
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.mfa_secret = None
    user.mfa_enabled = False
    
    # Setup query mocking for string-based queries
    db.query.return_value.filter_by.return_value.first.return_value = user
    
    return db

def test_setup_mfa(mock_db):
    """Test setting up MFA for a user."""
    # Call the setup_mfa method
    result = MFAManager.setup_mfa(mock_db, 1)
    
    # Check that the result contains the expected keys
    assert "secret" in result
    assert "qr_code" in result
    
    # Check that the secret was saved to the user
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    assert user.mfa_secret == result["secret"]
    
    # Check that the QR code contains the user's email - URL encoded format
    assert "test%40example.com" in result["qr_code"]
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_verify_mfa_setup_success(mock_db):
    """Test verifying MFA setup with a valid code."""
    # Setup
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    user.mfa_secret = pyotp.random_base32()
    
    # Generate a valid code
    totp = pyotp.TOTP(user.mfa_secret)
    code = totp.now()
    
    # Call the verify_mfa_setup method
    with patch('pyotp.TOTP.verify', return_value=True):
        result = MFAManager.verify_mfa_setup(mock_db, 1, code)
    
    # Check that the result is True
    assert result is True
    
    # Check that MFA was enabled for the user
    assert user.mfa_enabled is True
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_verify_mfa_setup_failure(mock_db):
    """Test verifying MFA setup with an invalid code."""
    # Setup
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    user.mfa_secret = pyotp.random_base32()
    
    # Call the verify_mfa_setup method with an invalid code
    with patch('pyotp.TOTP.verify', return_value=False):
        result = MFAManager.verify_mfa_setup(mock_db, 1, "000000")
    
    # Check that the result is False
    assert result is False
    
    # Check that MFA was not enabled for the user
    assert user.mfa_enabled is False
    
    # Verify that the commit was not called
    mock_db.commit.assert_not_called()

def test_verify_mfa_code_success(mock_db):
    """Test verifying MFA code during login with a valid code."""
    # Setup
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    user.mfa_secret = pyotp.random_base32()
    user.mfa_enabled = True
    
    # Generate a valid code
    totp = pyotp.TOTP(user.mfa_secret)
    code = totp.now()
    
    # Call the verify_mfa_code method
    with patch('pyotp.TOTP.verify', return_value=True):
        result = MFAManager.verify_mfa_code(mock_db, 1, code)
    
    # Check that the result is True
    assert result is True

def test_verify_mfa_code_failure(mock_db):
    """Test verifying MFA code during login with an invalid code."""
    # Setup
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    user.mfa_secret = pyotp.random_base32()
    user.mfa_enabled = True
    
    # Call the verify_mfa_code method with an invalid code
    with patch('pyotp.TOTP.verify', return_value=False):
        result = MFAManager.verify_mfa_code(mock_db, 1, "000000")
    
    # Check that the result is False
    assert result is False

def test_verify_mfa_code_not_enabled(mock_db):
    """Test verifying MFA code when MFA is not enabled."""
    # Setup
    user = mock_db.query.return_value.filter_by.return_value.first.return_value
    user.mfa_secret = pyotp.random_base32()
    user.mfa_enabled = False
    
    # Call the verify_mfa_code method
    result = MFAManager.verify_mfa_code(mock_db, 1, "000000")
    
    # Check that the result is False
    assert result is False

def test_create_mfa_device_token(mock_db):
    """Test creating an MFA device token."""
    # Call the create_mfa_device_token method
    token = MFAManager.create_mfa_device_token(mock_db, 1)
    
    # Check that a token was returned
    assert token is not None
    assert isinstance(token, str)
    
    # Check that a device token was added to the database
    mock_db.add.assert_called_once()
    args, _ = mock_db.add.call_args
    device_token = args[0]
    
    assert isinstance(device_token, MFADeviceToken)
    assert device_token.user_id == 1
    assert device_token.token == token
    assert device_token.expires_at > datetime.utcnow()
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_verify_mfa_device_token_success(mock_db):
    """Test verifying an MFA device token with a valid token."""
    # Setup - mock the query and filter methods
    mock_db.query.return_value.filter_by.return_value.first.return_value = MagicMock()
    
    # Call the verify_mfa_device_token method
    result = MFAManager.verify_mfa_device_token(mock_db, 1, "valid-token")
    
    # Check that the result is True
    assert result is True

def test_verify_mfa_device_token_failure(mock_db):
    """Test verifying an MFA device token with an invalid token."""
    # Setup
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    
    # Call the verify_mfa_device_token method
    result = MFAManager.verify_mfa_device_token(mock_db, 1, "invalid-token")
    
    # Check that the result is False
    assert result is False
