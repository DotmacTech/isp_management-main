"""
Tests for Multi-Factor Authentication (MFA) functionality.

This module contains tests for:
- MFA setup
- MFA verification
- MFA login flow
- MFA device token management
- MFA disabling
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import pyotp
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from backend_core.models import User, MFADeviceToken
from backend_core.auth_service import AuthService


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user(db: Session):
    """Create a test user for MFA tests."""
    # Check if test user already exists
    existing_user = db.query(User).filter(User.username == "mfauser").first()
    if existing_user:
        # Reset MFA settings
        existing_user.mfa_enabled = False
        existing_user.mfa_secret = None
        db.commit()
        db.refresh(existing_user)
        return existing_user
    
    # Create a new test user
    hashed_password = AuthService.get_password_hash("testpassword")
    user = User(
        username="mfauser",
        email="mfa@example.com",
        hashed_password=hashed_password,
        is_active=True,
        role="user",
        mfa_enabled=False,
        mfa_secret=None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_tokens(client, test_user):
    """Get authentication tokens by logging in."""
    response = client.post(
        "/auth/login",
        json={"username": "mfauser", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()


def test_mfa_setup(client, db, auth_tokens, test_user):
    """Test setting up MFA for a user."""
    access_token = auth_tokens["access_token"]
    
    # Request MFA setup
    response = client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    setup_data = response.json()
    assert "secret" in setup_data
    assert "qr_code" in setup_data
    assert "otpauth_url" in setup_data
    
    # Store the secret for verification
    secret = setup_data["secret"]
    
    # Generate a valid TOTP code using the secret
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # Verify the MFA setup
    response = client.post(
        "/auth/mfa/verify",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Check that MFA is now enabled for the user
    db.refresh(test_user)
    assert test_user.mfa_enabled
    assert test_user.mfa_secret is not None


def test_mfa_login_flow(client, db, test_user):
    """Test the MFA login flow."""
    # Ensure MFA is enabled
    if not test_user.mfa_enabled or not test_user.mfa_secret:
        test_user.mfa_enabled = True
        test_user.mfa_secret = pyotp.random_base32()
        db.commit()
        db.refresh(test_user)
    
    # First login step - provide username and password
    response = client.post(
        "/auth/login",
        json={"username": "mfauser", "password": "testpassword"}
    )
    assert response.status_code == 200
    login_data = response.json()
    
    # Check that the response indicates MFA is required
    assert login_data["mfa_required"] is True
    assert "mfa_token" in login_data
    
    mfa_token = login_data["mfa_token"]
    
    # Generate a valid TOTP code
    totp = pyotp.TOTP(test_user.mfa_secret)
    valid_code = totp.now()
    
    # Complete MFA verification
    response = client.post(
        "/auth/mfa/login",
        json={"mfa_token": mfa_token, "code": valid_code}
    )
    assert response.status_code == 200
    
    # Check that we received full authentication tokens
    mfa_login_data = response.json()
    assert "access_token" in mfa_login_data
    assert "refresh_token" not in mfa_login_data  # Should be in cookies
    assert mfa_login_data["mfa_required"] is False


def test_mfa_device_token(client, db, test_user):
    """Test remembering a device with MFA device tokens."""
    # Ensure MFA is enabled
    if not test_user.mfa_enabled or not test_user.mfa_secret:
        test_user.mfa_enabled = True
        test_user.mfa_secret = pyotp.random_base32()
        db.commit()
        db.refresh(test_user)
    
    # First login step
    response = client.post(
        "/auth/login",
        json={"username": "mfauser", "password": "testpassword"}
    )
    assert response.status_code == 200
    login_data = response.json()
    mfa_token = login_data["mfa_token"]
    
    # Generate a valid TOTP code
    totp = pyotp.TOTP(test_user.mfa_secret)
    valid_code = totp.now()
    
    # Complete MFA verification with remember_device=True
    response = client.post(
        "/auth/mfa/login",
        json={"mfa_token": mfa_token, "code": valid_code, "remember_device": True}
    )
    assert response.status_code == 200
    
    # Check that a device token was created
    device_token = db.query(MFADeviceToken).filter(
        MFADeviceToken.user_id == test_user.id
    ).first()
    assert device_token is not None
    
    # Try logging in again - should skip MFA
    response = client.post(
        "/auth/login",
        json={"username": "mfauser", "password": "testpassword"}
    )
    assert response.status_code == 200
    login_data = response.json()
    
    # MFA should not be required due to remembered device
    assert "mfa_required" in login_data
    assert login_data.get("mfa_required") is False


def test_disable_mfa(client, db, auth_tokens, test_user):
    """Test disabling MFA for a user."""
    # Ensure MFA is enabled
    if not test_user.mfa_enabled:
        test_user.mfa_enabled = True
        test_user.mfa_secret = pyotp.random_base32()
        db.commit()
        db.refresh(test_user)
    
    access_token = auth_tokens["access_token"]
    
    # Generate a valid TOTP code
    totp = pyotp.TOTP(test_user.mfa_secret)
    valid_code = totp.now()
    
    # Disable MFA
    response = client.post(
        "/auth/mfa/disable",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Check that MFA is now disabled
    db.refresh(test_user)
    assert not test_user.mfa_enabled
    
    # Check that device tokens were deleted
    device_tokens = db.query(MFADeviceToken).filter(
        MFADeviceToken.user_id == test_user.id
    ).count()
    assert device_tokens == 0


def test_invalid_mfa_code(client, db, test_user):
    """Test that invalid MFA codes are rejected."""
    # Ensure MFA is enabled
    if not test_user.mfa_enabled or not test_user.mfa_secret:
        test_user.mfa_enabled = True
        test_user.mfa_secret = pyotp.random_base32()
        db.commit()
        db.refresh(test_user)
    
    # First login step
    response = client.post(
        "/auth/login",
        json={"username": "mfauser", "password": "testpassword"}
    )
    assert response.status_code == 200
    login_data = response.json()
    mfa_token = login_data["mfa_token"]
    
    # Try with invalid code
    response = client.post(
        "/auth/mfa/login",
        json={"mfa_token": mfa_token, "code": "000000"}  # Invalid code
    )
    assert response.status_code == 401
    assert "Invalid MFA code" in response.json()["detail"]
