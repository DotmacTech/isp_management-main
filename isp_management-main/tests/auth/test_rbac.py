"""
Tests for Role-Based Access Control (RBAC) functionality.

This module contains tests for:
- Role-based endpoint access
- Permission checking
- Admin vs regular user access
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from typing import Optional, Dict, Any

from backend_core.auth_service import AuthService


# Create mock User class for testing
class MockUser:
    def __init__(self, id, username, email, role, is_active=True):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app for testing RBAC."""
    app = FastAPI()
    
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    
    # Define a dependency to get the current user
    def get_current_user(token: str = Depends(oauth2_scheme), db: Optional[Any] = None):
        try:
            payload = AuthService.decode_token(token)
            user_id = payload.get("sub")
            
            # For testing, we'll return a mock user based on the token payload
            if payload.get("role") == "admin":
                return MockUser(
                    id=1,
                    username="admin",
                    email="admin@example.com",
                    role="admin"
                )
            else:
                return MockUser(
                    id=2,
                    username="user",
                    email="user@example.com",
                    role="user"
                )
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Define a dependency to check if the user is an admin
    def admin_required(user: Any = Depends(get_current_user)):
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user
    
    # Define test endpoints
    @app.get("/users/me")
    def read_users_me(current_user: Any = Depends(get_current_user)):
        return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "role": current_user.role}
    
    @app.get("/users/{user_id}")
    def read_user(user_id: int, current_user: Any = Depends(get_current_user)):
        # Regular users can only access their own data
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this user's data",
            )
        
        # For testing, we'll return a mock user
        if user_id == 1:
            return {"id": 1, "username": "admin", "email": "admin@example.com", "role": "admin"}
        elif user_id == 2:
            return {"id": 2, "username": "user", "email": "user@example.com", "role": "user"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    
    @app.post("/users/")
    def create_user(username: str, email: str, role: str, current_user: Any = Depends(admin_required)):
        # Only admins can create users (enforced by admin_required dependency)
        return {"id": 3, "username": username, "email": email, "role": role}
    
    @app.get("/admin-only")
    def admin_only_endpoint(current_user: Any = Depends(admin_required)):
        # Only admins can access this endpoint (enforced by admin_required dependency)
        return {"message": "Admin access granted"}
    
    return app


@pytest.fixture
def client(mock_app):
    """Create a test client for the FastAPI app."""
    return TestClient(mock_app)


@pytest.fixture
def admin_user():
    """Create a mock admin user for testing."""
    return MockUser(
        id=1,
        username="admin",
        email="admin@example.com",
        role="admin"
    )


@pytest.fixture
def regular_user():
    """Create a mock regular user for testing."""
    return MockUser(
        id=2,
        username="user",
        email="user@example.com",
        role="user"
    )


@pytest.fixture
def admin_token(admin_user):
    """Get an authentication token for the admin user."""
    with patch("backend_core.auth_service.AuthService.create_access_token") as mock_create_token:
        mock_create_token.return_value = "admin-token"
        return "admin-token"


@pytest.fixture
def user_token(regular_user):
    """Get an authentication token for the regular user."""
    with patch("backend_core.auth_service.AuthService.create_access_token") as mock_create_token:
        mock_create_token.return_value = "user-token"
        return "user-token"


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_admin_access(mock_decode_token, mock_redis, client, admin_token, admin_user):
    """Test that admin users can access admin-only endpoints."""
    # Mock token validation to return admin payload
    mock_decode_token.return_value = {"sub": str(admin_user.id), "role": "admin"}
    
    # Test admin-only endpoint
    response = client.get("/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    
    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "Admin access granted"}


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_regular_user_restricted_access(mock_decode_token, mock_redis, client, user_token, regular_user):
    """Test that regular users cannot access admin-only endpoints."""
    # Mock token validation to return regular user payload
    mock_decode_token.return_value = {"sub": str(regular_user.id), "role": "user"}
    
    # Test admin-only endpoint
    response = client.get("/admin-only", headers={"Authorization": f"Bearer {user_token}"})
    
    # Verify response
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_user_can_access_own_data(mock_decode_token, mock_redis, client, user_token, regular_user):
    """Test that users can access their own data."""
    # Mock token validation to return regular user payload
    mock_decode_token.return_value = {"sub": str(regular_user.id), "role": "user"}
    
    # Test user endpoint with own ID
    response = client.get(f"/users/{regular_user.id}", headers={"Authorization": f"Bearer {user_token}"})
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["id"] == regular_user.id
    assert response.json()["username"] == regular_user.username
    assert response.json()["role"] == regular_user.role


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_user_cannot_access_other_user_data(mock_decode_token, mock_redis, client, user_token, regular_user):
    """Test that users cannot access other users' data."""
    # Mock token validation to return regular user payload
    mock_decode_token.return_value = {"sub": str(regular_user.id), "role": "user"}
    
    # Test user endpoint with admin ID (different from regular user)
    response = client.get("/users/1", headers={"Authorization": f"Bearer {user_token}"})
    
    # Verify response
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_admin_can_access_any_user_data(mock_decode_token, mock_redis, client, admin_token, admin_user):
    """Test that admins can access any user's data."""
    # Mock token validation to return admin payload
    mock_decode_token.return_value = {"sub": str(admin_user.id), "role": "admin"}
    
    # Test user endpoint with regular user ID (different from admin)
    response = client.get("/users/2", headers={"Authorization": f"Bearer {admin_token}"})
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["id"] == 2
    assert response.json()["username"] == "user"
    assert response.json()["role"] == "user"


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_admin_can_create_users(mock_decode_token, mock_redis, client, admin_token, admin_user):
    """Test that admins can create new users."""
    # Mock token validation to return admin payload
    mock_decode_token.return_value = {"sub": str(admin_user.id), "role": "admin"}
    
    # Test create user endpoint
    response = client.post(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "user"
        }
    )
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["id"] == 3
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["role"] == "user"


@patch("backend_core.auth_service.redis_client")
@patch("backend_core.auth_service.AuthService.decode_token")
def test_regular_user_cannot_create_users(mock_decode_token, mock_redis, client, user_token, regular_user):
    """Test that regular users cannot create new users."""
    # Mock token validation to return regular user payload
    mock_decode_token.return_value = {"sub": str(regular_user.id), "role": "user"}
    
    # Test create user endpoint
    response = client.post(
        "/users/",
        headers={"Authorization": f"Bearer {user_token}"},
        params={
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "user"
        }
    )
    
    # Verify response
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]
