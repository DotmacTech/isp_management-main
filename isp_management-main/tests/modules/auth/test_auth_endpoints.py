"""
Tests for the authentication endpoints.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend_core.main import app
from modules.auth.services import AuthService
from backend_core.models import User

# Test client
client = TestClient(app)

# Mock user
@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = AuthService.get_password_hash("Password123!")
    user.role = "customer"
    user.is_active = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user

# Test registration endpoint
@patch("isp_management.modules.auth.endpoints.AuthService.create_user")
@patch("isp_management.modules.auth.endpoints.EmailService.send_email")
def test_register(mock_send_email, mock_create_user, mock_user):
    # Configure mock to return a user
    mock_create_user.return_value = mock_user
    
    # Test registration
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "customer"
        }
    )
    
    # Verify the response
    assert response.status_code == 201
    assert response.json()["username"] == mock_user.username
    assert response.json()["email"] == mock_user.email
    assert response.json()["role"] == mock_user.role
    
    # Verify the user was created
    mock_create_user.assert_called_once()
    
    # Verify an email was sent
    mock_send_email.assert_called_once()

# Test login endpoint
@patch("isp_management.modules.auth.endpoints.AuthService.authenticate_user")
@patch("isp_management.modules.auth.endpoints.AuthService.rate_limit_login_attempts")
@patch("isp_management.modules.auth.endpoints.AuthService.clear_login_attempts")
def test_login(mock_clear_attempts, mock_rate_limit, mock_authenticate, mock_user):
    # Configure mocks
    mock_rate_limit.return_value = False  # No rate limiting
    mock_authenticate.return_value = mock_user
    
    # Test login
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "Password123!",
            "remember_me": False
        }
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()
    assert response.json()["user_id"] == mock_user.id
    assert response.json()["username"] == mock_user.username
    assert response.json()["role"] == mock_user.role
    
    # Verify the user was authenticated
    mock_authenticate.assert_called_once()
    
    # Verify login attempts were cleared
    mock_clear_attempts.assert_called_once()

# Test login with rate limiting
@patch("isp_management.modules.auth.endpoints.AuthService.rate_limit_login_attempts")
def test_login_rate_limited(mock_rate_limit):
    # Configure mock to return True (rate limited)
    mock_rate_limit.return_value = True
    
    # Test login
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "Password123!",
            "remember_me": False
        }
    )
    
    # Verify the response
    assert response.status_code == 429
    assert "Too many login attempts" in response.json()["detail"]

# Test login with invalid credentials
@patch("isp_management.modules.auth.endpoints.AuthService.authenticate_user")
@patch("isp_management.modules.auth.endpoints.AuthService.rate_limit_login_attempts")
def test_login_invalid_credentials(mock_rate_limit, mock_authenticate):
    # Configure mocks
    mock_rate_limit.return_value = False  # No rate limiting
    mock_authenticate.return_value = None  # Authentication fails
    
    # Test login
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword",
            "remember_me": False
        }
    )
    
    # Verify the response
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

# Test login with inactive user
@patch("isp_management.modules.auth.endpoints.AuthService.authenticate_user")
@patch("isp_management.modules.auth.endpoints.AuthService.rate_limit_login_attempts")
def test_login_inactive_user(mock_rate_limit, mock_authenticate, mock_user):
    # Configure mocks
    mock_rate_limit.return_value = False  # No rate limiting
    mock_user.is_active = False
    mock_authenticate.return_value = mock_user
    
    # Test login
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "Password123!",
            "remember_me": False
        }
    )
    
    # Verify the response
    assert response.status_code == 401
    assert "User account is disabled" in response.json()["detail"]

# Test password reset request
@patch("isp_management.modules.auth.endpoints.AuthService.create_password_reset_token")
@patch("isp_management.modules.auth.endpoints.EmailService.send_email")
def test_request_password_reset(mock_send_email, mock_create_token):
    # Configure mock to return a token
    mock_create_token.return_value = "reset_token"
    
    # Test password reset request
    response = client.post(
        "/auth/password-reset",
        json={
            "email": "test@example.com"
        }
    )
    
    # Verify the response
    assert response.status_code == 202
    assert "If your email is registered" in response.json()["message"]
    
    # Verify a token was created
    mock_create_token.assert_called_once_with("test@example.com")
    
    # Verify an email was sent
    mock_send_email.assert_called_once()

# Test password reset confirmation
@patch("isp_management.modules.auth.endpoints.AuthService.verify_password_reset_token")
@patch("isp_management.modules.auth.endpoints.AuthService.reset_password")
def test_confirm_password_reset(mock_reset_password, mock_verify_token):
    # Configure mocks
    mock_verify_token.return_value = "test@example.com"
    mock_reset_password.return_value = True
    
    # Test password reset confirmation
    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": "reset_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
    )
    
    # Verify the response
    assert response.status_code == 200
    assert "Password has been reset successfully" in response.json()["message"]
    
    # Verify the token was verified
    mock_verify_token.assert_called_once_with("reset_token")
    
    # Verify the password was reset
    mock_reset_password.assert_called_once_with(
        pytest.ANY,  # db session
        "test@example.com",
        "NewPassword123!"
    )

# Test password reset confirmation with invalid token
@patch("isp_management.modules.auth.endpoints.AuthService.verify_password_reset_token")
def test_confirm_password_reset_invalid_token(mock_verify_token):
    # Configure mock to raise an exception
    mock_verify_token.side_effect = HTTPException(status_code=400, detail="Invalid token")
    
    # Test password reset confirmation
    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": "invalid_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
    )
    
    # Verify the response
    assert response.status_code == 400
    assert "Invalid token" in response.json()["detail"]

# Test password reset confirmation with failed reset
@patch("isp_management.modules.auth.endpoints.AuthService.verify_password_reset_token")
@patch("isp_management.modules.auth.endpoints.AuthService.reset_password")
def test_confirm_password_reset_failed(mock_reset_password, mock_verify_token):
    # Configure mocks
    mock_verify_token.return_value = "test@example.com"
    mock_reset_password.return_value = False
    
    # Test password reset confirmation
    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": "reset_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
    )
    
    # Verify the response
    assert response.status_code == 400
    assert "Password reset failed" in response.json()["detail"]

# Test logout
@patch("isp_management.modules.auth.endpoints.AuthService.decode_token")
@patch("isp_management.modules.auth.endpoints.AuthService.blacklist_token")
def test_logout(mock_blacklist, mock_decode, mock_user):
    # Configure mocks
    mock_decode.return_value = {
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": mock_user.role,
        "exp": int((datetime.utcnow() + timedelta(minutes=30)).timestamp())
    }
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": mock_user.role
    })
    
    # Test logout
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]
    
    # Verify the token was blacklisted
    mock_blacklist.assert_called_once()

# Test get current user
@patch("isp_management.modules.auth.dependencies.get_current_user")
def test_read_users_me(mock_get_user, mock_user):
    # Configure mock to return a user
    mock_get_user.return_value = mock_user
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": mock_user.role
    })
    
    # Test get current user
    response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    assert response.json()["email"] == mock_user.email
    assert response.json()["role"] == mock_user.role

# Test get user list (admin only)
@patch("isp_management.modules.auth.dependencies.get_admin_user")
@patch("isp_management.modules.auth.endpoints.AuthService.get_users")
@patch("isp_management.modules.auth.endpoints.AuthService.count_users")
def test_read_users(mock_count, mock_get_users, mock_get_admin, mock_user):
    # Configure mocks
    mock_get_admin.return_value = mock_user
    mock_get_users.return_value = [mock_user]
    mock_count.return_value = 1
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": "admin"
    })
    
    # Test get user list
    response = client.get(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["users"]) == 1
    assert response.json()["users"][0]["username"] == mock_user.username

# Test get user by ID (staff or admin only)
@patch("isp_management.modules.auth.dependencies.get_staff_user")
@patch("isp_management.modules.auth.endpoints.AuthService.get_user_by_id")
def test_read_user(mock_get_user, mock_get_staff, mock_user):
    # Configure mocks
    mock_get_staff.return_value = mock_user
    mock_get_user.return_value = mock_user
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": "staff"
    })
    
    # Test get user by ID
    response = client.get(
        f"/auth/users/{mock_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    assert response.json()["email"] == mock_user.email
    assert response.json()["role"] == mock_user.role

# Test update user (staff or admin only)
@patch("isp_management.modules.auth.dependencies.get_staff_user")
@patch("isp_management.modules.auth.endpoints.AuthService.update_user")
def test_update_user(mock_update_user, mock_get_staff, mock_user):
    # Configure mocks
    mock_get_staff.return_value = mock_user
    mock_update_user.return_value = mock_user
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": "staff"
    })
    
    # Test update user
    response = client.put(
        f"/auth/users/{mock_user.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "updateduser",
            "email": "updated@example.com"
        }
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    assert response.json()["email"] == mock_user.email
    
    # Verify the user was updated
    mock_update_user.assert_called_once()

# Test deactivate user (admin only)
@patch("isp_management.modules.auth.dependencies.get_admin_user")
@patch("isp_management.modules.auth.endpoints.AuthService.deactivate_user")
def test_deactivate_user(mock_deactivate, mock_get_admin, mock_user):
    # Configure mocks
    mock_get_admin.return_value = mock_user
    mock_user.id = 2  # Different ID to avoid self-deactivation check
    mock_deactivate.return_value = mock_user
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": "admin"
    })
    
    # Test deactivate user
    response = client.post(
        "/auth/users/2/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    
    # Verify the user was deactivated
    mock_deactivate.assert_called_once_with(pytest.ANY, 2)

# Test activate user (admin only)
@patch("isp_management.modules.auth.dependencies.get_admin_user")
@patch("isp_management.modules.auth.endpoints.AuthService.activate_user")
def test_activate_user(mock_activate, mock_get_admin, mock_user):
    # Configure mocks
    mock_get_admin.return_value = mock_user
    mock_activate.return_value = mock_user
    
    # Create a valid token
    token = AuthService.create_access_token({
        "sub": mock_user.username,
        "id": mock_user.id,
        "role": "admin"
    })
    
    # Test activate user
    response = client.post(
        f"/auth/users/{mock_user.id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["username"] == mock_user.username
    
    # Verify the user was activated
    mock_activate.assert_called_once_with(pytest.ANY, mock_user.id)
