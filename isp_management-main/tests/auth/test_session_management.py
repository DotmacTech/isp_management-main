"""
Tests for session management and token refresh functionality.

This module contains tests for:
- Session creation during login
- Session listing
- Session termination
- Token refresh
- Logout functionality
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt

from main import app
from backend_core.models import User, UserSession
from backend_core.auth_service import AuthService
from backend_core.config import SECRET_KEY, ALGORITHM


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user(db: Session):
    """Create a test user for authentication tests."""
    # Check if test user already exists
    existing_user = db.query(User).filter(User.username == "testuser").first()
    if existing_user:
        return existing_user
    
    # Create a new test user
    hashed_password = AuthService.get_password_hash("testpassword")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True,
        role="user"
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
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()


def test_login_creates_session(client, db, test_user):
    """Test that login creates a new session."""
    # Get initial session count
    initial_sessions = db.query(UserSession).filter(
        UserSession.user_id == test_user.id
    ).count()
    
    # Login
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    
    # Check that a new session was created
    new_sessions = db.query(UserSession).filter(
        UserSession.user_id == test_user.id
    ).count()
    assert new_sessions == initial_sessions + 1


def test_get_sessions(client, auth_tokens):
    """Test listing user sessions."""
    access_token = auth_tokens["access_token"]
    
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert data["total"] > 0
    
    # Check session structure
    session = data["sessions"][0]
    assert "session_id" in session
    assert "device_info" in session
    assert "created_at" in session
    assert "last_active_at" in session
    assert "is_current" in session


def test_terminate_session(client, db, auth_tokens, test_user):
    """Test terminating a specific session."""
    access_token = auth_tokens["access_token"]
    
    # Get sessions
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    sessions = response.json()["sessions"]
    # Find a non-current session if available
    non_current_session = next((s for s in sessions if not s["is_current"]), None)
    
    if non_current_session:
        # Terminate the non-current session
        response = client.post(
            "/auth/sessions/terminate",
            json={"session_id": non_current_session["session_id"]},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        
        # Verify session is terminated
        session = db.query(UserSession).filter(
            UserSession.session_id == non_current_session["session_id"]
        ).first()
        assert session is not None
        assert not session.is_active


def test_terminate_all_sessions(client, db, auth_tokens, test_user):
    """Test terminating all sessions except current."""
    access_token = auth_tokens["access_token"]
    
    # Create additional sessions
    for i in range(2):
        # Create session directly in the database
        session = UserSession(
            user_id=test_user.id,
            session_id=f"test_session_{i}",
            device_info=f"Test Device {i}",
            ip_address="127.0.0.1",
            is_active=True,
            created_at=datetime.utcnow(),
            last_active_at=datetime.utcnow()
        )
        db.add(session)
    db.commit()
    
    # Get initial active session count
    initial_active_sessions = db.query(UserSession).filter(
        UserSession.user_id == test_user.id,
        UserSession.is_active == True
    ).count()
    assert initial_active_sessions > 1
    
    # Terminate all sessions except current
    response = client.post(
        "/auth/sessions/terminate",
        json={"terminate_all_except_current": True},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Verify only one session remains active
    remaining_active_sessions = db.query(UserSession).filter(
        UserSession.user_id == test_user.id,
        UserSession.is_active == True
    ).count()
    assert remaining_active_sessions == 1


def test_refresh_token(client, auth_tokens):
    """Test refreshing an access token using a refresh token."""
    # Extract the refresh token from cookies
    cookies = client.cookies
    refresh_token = cookies.get("refresh_token")
    assert refresh_token is not None
    
    # Use the refresh token to get a new access token
    response = client.post("/auth/refresh")
    assert response.status_code == 200
    
    # Verify the response contains a new access token
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != auth_tokens["access_token"]
    
    # Verify the new token works
    new_token = data["access_token"]
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    assert response.status_code == 200


def test_logout(client, db, auth_tokens, test_user):
    """Test logging out and terminating the session."""
    access_token = auth_tokens["access_token"]
    
    # Get the current session ID from the token
    payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    session_id = payload.get("session_id")
    assert session_id is not None
    
    # Logout
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Verify session is terminated
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id
    ).first()
    assert session is not None
    assert not session.is_active
    
    # Verify refresh token cookie is cleared
    assert "refresh_token" not in client.cookies
    
    # Verify the access token no longer works
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


def test_blacklisted_token(client, db, auth_tokens):
    """Test that blacklisted tokens are rejected."""
    access_token = auth_tokens["access_token"]
    
    # Blacklist the token
    AuthService.blacklist_token(access_token)
    
    # Try to use the blacklisted token
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401
    assert "Token has been revoked" in response.json()["detail"]
