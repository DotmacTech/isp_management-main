# Authentication Testing Guide

This guide provides comprehensive information on testing the authentication system in the ISP Management Platform.

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Security Testing](#security-testing)
7. [Performance Testing](#performance-testing)
8. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Overview

The authentication system is a critical component of the ISP Management Platform, handling user authentication, authorization, session management, and security features. Thorough testing is essential to ensure its reliability and security.

## Test Environment Setup

### Prerequisites

- Python 3.9+
- pytest 7.0+
- pytest-mock
- pytest-cov
- pytest-asyncio (for async tests)
- Redis (for token blacklisting and rate limiting tests)

### Environment Configuration

Create a `.env.test` file in the project root with the following configuration:

```
# Database
DATABASE_URL=sqlite:///./test.db

# JWT Configuration
JWT_SECRET_KEY=test_jwt_secret_key
JWT_REFRESH_SECRET_KEY=test_jwt_refresh_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis Configuration
REDIS_URL=redis://localhost:6379/1

# Email Configuration
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=test
SMTP_PASSWORD=test
FROM_EMAIL=test@example.com
EMAIL_TESTING=true

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### Test Database Setup

For testing, we use SQLite in-memory databases to ensure tests are isolated and can run in parallel:

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend_core.database import Base

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

### Mock Redis Setup

For Redis-dependent tests, we use a mock Redis client:

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_redis():
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.exists.return_value = 0
    return redis_mock
```

## Unit Testing

Unit tests focus on testing individual components in isolation, using mocks for dependencies.

### Running Unit Tests

```bash
# Run all authentication unit tests
python -m pytest tests/auth/ -v

# Run specific test file
python -m pytest tests/auth/test_auth_service.py -v

# Run with coverage report
python -m pytest tests/auth/ --cov=backend_core.auth_service --cov-report=term-missing
```

### Key Test Files

- **test_auth_service.py**: Tests for the AuthService class
- **test_rbac.py**: Tests for role-based access control
- **test_mfa.py**: Tests for multi-factor authentication
- **test_session_management.py**: Tests for session management

### Test Examples

#### Testing Password Hashing

```python
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
```

#### Testing JWT Token Creation

```python
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
```

#### Testing User Authentication

```python
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
```

#### Testing Token Blacklisting

```python
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
```

#### Testing Role-Based Access Control

```python
def test_admin_access(client, admin_token):
    """Test that admin users can access admin-only endpoints."""
    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
def test_regular_user_restricted_access(client, user_token):
    """Test that regular users cannot access admin-only endpoints."""
    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
```

## Integration Testing

Integration tests verify that different components work together correctly.

### Running Integration Tests

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run specific integration test file
python -m pytest tests/integration/test_auth_endpoints.py -v
```

### Test Examples

#### Testing Login Endpoint

```python
def test_login_endpoint(client, test_user):
    """Test the login endpoint."""
    response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["id"] == test_user.id
```

#### Testing Protected Endpoints

```python
def test_protected_endpoint(client, user_token):
    """Test accessing a protected endpoint with a valid token."""
    response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    
def test_protected_endpoint_without_token(client):
    """Test accessing a protected endpoint without a token."""
    response = client.get("/auth/users/me")
    assert response.status_code == 401
```

## End-to-End Testing

End-to-end tests verify the entire authentication flow from the user's perspective.

### Test Examples

#### Testing Complete Login Flow

```python
def test_complete_login_flow(client, test_user):
    """Test the complete login flow including token refresh."""
    # Login
    login_response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "password123"
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    # Access protected endpoint
    me_response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_response.status_code == 200
    
    # Refresh token
    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    
    # Access protected endpoint with new token
    new_me_response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert new_me_response.status_code == 200
    
    # Logout
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 200
    
    # Try to access protected endpoint after logout
    final_response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert final_response.status_code == 401
```

## Security Testing

Security testing focuses on identifying vulnerabilities in the authentication system.

### Key Security Tests

#### Testing Password Policies

```python
def test_password_policy(client):
    """Test password policy enforcement."""
    # Test weak password
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak",
            "confirm_password": "weak"
        }
    )
    assert response.status_code == 400
    assert "password" in response.json()["detail"].lower()
    
    # Test strong password
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongP@ssw0rd123",
            "confirm_password": "StrongP@ssw0rd123"
        }
    )
    assert response.status_code == 201
```

#### Testing Account Lockout

```python
def test_account_lockout(client, test_user):
    """Test account lockout after multiple failed login attempts."""
    # Attempt login with incorrect password multiple times
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={
                "username": test_user.username,
                "password": "wrongpassword"
            }
        )
        assert response.status_code in [400, 401]
    
    # Attempt login with correct password after lockout
    response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "password123"
        }
    )
    assert response.status_code == 401
    assert "locked" in response.json()["detail"].lower()
```

#### Testing Token Expiry

```python
def test_token_expiry(client, test_user):
    """Test token expiry."""
    # Login
    login_response = client.post(
        "/auth/login",
        json={
            "username": test_user.username,
            "password": "password123"
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    # Modify token to make it expired
    with patch("backend_core.auth_service.jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.ExpiredSignatureError()
        
        # Access protected endpoint with expired token
        response = client.get(
            "/auth/users/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
```

## Performance Testing

Performance testing ensures the authentication system can handle the expected load.

### Key Performance Tests

#### Testing Login Performance

```python
def test_login_performance(client, test_user, benchmark):
    """Test login performance."""
    def login():
        return client.post(
            "/auth/login",
            json={
                "username": test_user.username,
                "password": "password123"
            }
        )
    
    result = benchmark(login)
    assert result.status_code == 200
```

#### Testing Token Validation Performance

```python
def test_token_validation_performance(client, user_token, benchmark):
    """Test token validation performance."""
    def validate_token():
        return client.get(
            "/auth/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
    
    result = benchmark(validate_token)
    assert result.status_code == 200
```

## Troubleshooting Common Issues

### Token Blacklisting Issues

If token blacklisting tests are failing, check:

1. The `TOKEN_BLACKLIST` set is properly initialized
2. The `blacklist_token` method is correctly adding tokens to the set
3. The `is_token_blacklisted` method is correctly checking for tokens in the set

Example fix:

```python
# Ensure TOKEN_BLACKLIST is initialized
if not hasattr(AuthService, 'TOKEN_BLACKLIST'):
    AuthService.TOKEN_BLACKLIST = set()

# Blacklist token
AuthService.blacklist_token(token)

# Verify token is blacklisted
assert token in AuthService.TOKEN_BLACKLIST
```

### Method Name Mismatches

If tests are failing due to method name mismatches, check:

1. The method names in the tests match the actual implementation
2. The method signatures match (parameters and return types)

Example fix:

```python
# Change from non-existent method
# AuthService.validate_token(token)

# To correct method
AuthService.decode_token(token)
```

### Database Session Issues

If tests are failing due to database session issues, check:

1. The session is properly closed after each test
2. The database is properly reset between tests
3. The correct session is being passed to methods

Example fix:

```python
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

### Mock User Issues

If tests are failing due to mock user issues, check:

1. The mock user has all required attributes
2. The mock user's password is properly hashed
3. The mock user's role is correctly set

Example fix:

```python
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
```
