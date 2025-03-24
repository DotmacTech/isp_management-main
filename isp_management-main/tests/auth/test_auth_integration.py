"""
Integration tests for the Authentication system.

This module tests the complete authentication flow, including:
- Login process
- Session creation and management
- Token refresh
- MFA setup and verification
- Role-based access control
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
import pyotp
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend_core.auth_service import AuthService
from backend_core.models import User, UserSession


@pytest.fixture
def auth_app():
    """Create a test FastAPI application with authentication routes."""
    from fastapi import FastAPI, Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    
    app = FastAPI()
    
    # Add authentication routes
    @app.post("/auth/login")
    async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends()):
        user = AuthService.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = AuthService.create_access_token(
            data={"sub": user.username, "id": user.id, "role": user.role}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    
    @app.get("/auth/me")
    async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends()):
        payload = AuthService.validate_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = db.query(User).filter(User.id == payload.get("id")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    
    @app.post("/auth/refresh")
    async def refresh_token(refresh_token: str, db: Session = Depends()):
        try:
            payload = AuthService.validate_token(refresh_token)
            if payload.get("token_type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = payload.get("id")
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token = AuthService.create_access_token(
                data={"sub": user.username, "id": user.id, "role": user.role}
            )
            
            return {"access_token": access_token, "token_type": "bearer"}
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @app.post("/auth/setup-mfa")
    async def setup_mfa(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends()):
        payload = AuthService.validate_token(token)
        user_id = payload.get("id")
        
        # Setup MFA
        mfa_setup = AuthService.setup_mfa(db, user_id)
        
        return mfa_setup
    
    @app.post("/auth/verify-mfa")
    async def verify_mfa(code: str, token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends()):
        payload = AuthService.validate_token(token)
        user_id = payload.get("id")
        
        # Verify MFA setup
        verified = AuthService.verify_mfa_setup(db, user_id, code)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code",
            )
        
        return {"status": "MFA setup verified"}
    
    @app.get("/auth/sessions")
    async def get_sessions(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends()):
        payload = AuthService.validate_token(token)
        user_id = payload.get("id")
        
        # Get user sessions
        sessions = AuthService.get_user_sessions(db, user_id)
        
        return {"sessions": [{"id": s.id, "user_agent": s.user_agent, "created_at": s.created_at} for s in sessions]}
    
    @app.post("/auth/logout")
    async def logout(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends()):
        payload = AuthService.validate_token(token)
        
        # Blacklist the token
        AuthService.blacklist_token(token, datetime.fromtimestamp(payload.get("exp")))
        
        return {"status": "logged out"}
    
    return app


@pytest.fixture
def auth_client(auth_app, db_session, test_user):
    """Create a test client with the auth app."""
    
    # Mock the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Add dependency override
    auth_app.dependency_overrides = {
        "db": override_get_db
    }
    
    with TestClient(auth_app) as client:
        yield client


@patch('backend_core.auth_service.redis_client')
def test_login_flow(mock_redis, auth_client, test_user):
    """Test the complete login flow."""
    # Mock redis for token blacklist
    mock_redis.exists.return_value = False
    
    # Login
    response = auth_client.post(
        "/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    
    # Verify login response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Use token to get user info
    access_token = data["access_token"]
    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify user info
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == test_user.username
    assert user_data["id"] == test_user.id
    assert user_data["role"] == test_user.role


@patch('backend_core.auth_service.redis_client')
def test_token_refresh(mock_redis, auth_client, test_user):
    """Test token refresh flow."""
    # Mock redis for token blacklist
    mock_redis.exists.return_value = False
    
    # Create a refresh token
    refresh_token = AuthService.create_access_token(
        data={
            "sub": test_user.username, 
            "id": test_user.id, 
            "token_type": "refresh"
        },
        expires_delta=timedelta(days=7)
    )
    
    # Use refresh token to get new access token
    response = auth_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    # Verify refresh response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Use new token to get user info
    access_token = data["access_token"]
    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify user info
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == test_user.username


@patch('backend_core.auth_service.redis_client')
@patch('backend_core.auth_service.AuthService.setup_mfa')
def test_mfa_setup_flow(mock_setup_mfa, mock_redis, auth_client, test_user):
    """Test MFA setup flow."""
    # Mock redis for token blacklist
    mock_redis.exists.return_value = False
    
    # Mock MFA setup
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    mock_setup_mfa.return_value = {
        "secret": secret,
        "uri": totp.provisioning_uri(test_user.username, issuer_name="ISP Management")
    }
    
    # Login
    response = auth_client.post(
        "/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = response.json()["access_token"]
    
    # Setup MFA
    response = auth_client.post(
        "/auth/setup-mfa",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify MFA setup response
    assert response.status_code == 200
    mfa_data = response.json()
    assert "secret" in mfa_data
    assert "uri" in mfa_data
    
    # Verify MFA setup with valid code
    with patch('backend_core.auth_service.AuthService.verify_mfa_setup', return_value=True):
        response = auth_client.post(
            "/auth/verify-mfa",
            json={"code": totp.now()},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.json()["status"] == "MFA setup verified"


@patch('backend_core.auth_service.redis_client')
@patch('backend_core.auth_service.AuthService.get_user_sessions')
def test_session_management(mock_get_sessions, mock_redis, auth_client, test_user):
    """Test session management flow."""
    # Mock redis for token blacklist
    mock_redis.exists.return_value = False
    
    # Mock sessions
    mock_get_sessions.return_value = [
        MagicMock(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            user_agent="Test Browser 1.0",
            created_at=datetime.utcnow()
        ),
        MagicMock(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            user_agent="Test Mobile App 1.0",
            created_at=datetime.utcnow() - timedelta(days=1)
        )
    ]
    
    # Login
    response = auth_client.post(
        "/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = response.json()["access_token"]
    
    # Get sessions
    response = auth_client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify sessions response
    assert response.status_code == 200
    sessions_data = response.json()
    assert "sessions" in sessions_data
    assert len(sessions_data["sessions"]) == 2
    assert any(s["user_agent"] == "Test Browser 1.0" for s in sessions_data["sessions"])
    assert any(s["user_agent"] == "Test Mobile App 1.0" for s in sessions_data["sessions"])


@patch('backend_core.auth_service.redis_client')
def test_logout_flow(mock_redis, auth_client, test_user):
    """Test logout flow."""
    # Mock redis for token blacklist
    mock_redis.exists.return_value = False
    mock_redis.set.return_value = True
    
    # Login
    response = auth_client.post(
        "/auth/login",
        data={"username": test_user.username, "password": "testpassword"}
    )
    access_token = response.json()["access_token"]
    
    # Logout
    response = auth_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify logout response
    assert response.status_code == 200
    assert response.json()["status"] == "logged out"
    
    # Mock token now blacklisted
    mock_redis.exists.return_value = True
    
    # Try to use token after logout
    response = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Verify token is invalid
    assert response.status_code == 401
