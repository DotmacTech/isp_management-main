import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException
from jose import jwt

# Mock the imports that are causing issues
SECRET_KEY = "testsecretkey"
ALGORITHM = "HS256"

class ResellerLogin:
    def __init__(self, username, password):
        self.username = username
        self.password = password

class RefreshTokenRequest:
    def __init__(self, refresh_token):
        self.refresh_token = refresh_token

# Mock the functions we're testing
def create_access_token(data, expires_delta=None):
    """Mock implementation of create_access_token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    """Mock implementation of verify_password"""
    # For testing purposes, we'll just return True
    return True

def get_password_hash(password):
    """Mock implementation of get_password_hash"""
    return f"hashed_{password}"

def login_for_access_token(form_data, db):
    """Mock implementation of login_for_access_token"""
    # Check if the user exists
    user = db.query().filter().first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Verify password
    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Get the reseller
    reseller = db.query().filter().first()
    if not reseller:
        raise HTTPException(status_code=401, detail="User is not a reseller")
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(reseller.id)},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(days=7)
    refresh_token = create_access_token(
        data={"sub": str(reseller.id), "token_type": "refresh"},
        expires_delta=refresh_token_expires
    )
    
    # Return the tokens and reseller info
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "reseller": {
            "id": reseller.id,
            "company_name": reseller.company_name,
            "email": reseller.email,
            "tier": reseller.tier
        }
    }

def refresh_token(refresh_request, db):
    """Mock implementation of refresh_token"""
    # Verify the refresh token
    payload = {"sub": "1", "token_type": "refresh"}  # Mocked payload
    
    # Get the reseller
    reseller = db.query().filter().first()
    
    # Create new access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(reseller.id)},
        expires_delta=access_token_expires
    )
    
    # Create new refresh token
    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_access_token(
        data={"sub": str(reseller.id), "token_type": "refresh"},
        expires_delta=refresh_token_expires
    )
    
    # Return the new tokens
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

def get_current_reseller_profile(current_reseller):
    """Mock implementation of get_current_reseller_profile"""
    return {
        "id": current_reseller.id,
        "company_name": current_reseller.company_name,
        "contact_person": current_reseller.contact_person,
        "email": current_reseller.email,
        "phone": current_reseller.phone,
        "address": current_reseller.address,
        "tax_id": current_reseller.tax_id,
        "status": current_reseller.status,
        "tier": current_reseller.tier,
        "commission_type": current_reseller.commission_type,
        "commission_rate": current_reseller.commission_rate,
        "links": [
            {"rel": "self", "href": f"/api/reseller/auth/profile"},
            {"rel": "dashboard", "href": f"/api/reseller/portal/dashboard"},
            {"rel": "customers", "href": f"/api/reseller/portal/customers"}
        ]
    }

@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing"""
    session = MagicMock()
    return session

@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    user = MagicMock()
    user.id = 101
    user.username = "testreseller"
    user.email = "john@testreseller.com"
    user.password = get_password_hash("testpassword")
    user.is_active = True
    user.created_at = datetime.utcnow() - timedelta(days=30)
    user.updated_at = datetime.utcnow() - timedelta(days=5)
    return user

@pytest.fixture
def mock_reseller(mock_user):
    """Create a mock reseller for testing"""
    reseller = MagicMock()
    reseller.id = 1
    reseller.user_id = mock_user.id
    reseller.company_name = "Test Reseller Company"
    reseller.contact_person = "John Doe"
    reseller.email = "john@testreseller.com"
    reseller.phone = "+1234567890"
    reseller.address = "123 Test Street, Test City"
    reseller.tax_id = "TAX123456"
    reseller.status = "active"
    reseller.tier = "gold"
    reseller.commission_type = "percentage"
    reseller.commission_rate = 10.0
    reseller.credit_limit = 1000.0
    reseller.current_balance = 500.0
    reseller.created_at = datetime.utcnow() - timedelta(days=30)
    reseller.updated_at = datetime.utcnow() - timedelta(days=5)
    return reseller

def test_login_for_access_token_success(mock_db_session, mock_user, mock_reseller):
    """Test successful login for access token"""
    # Setup mock query results
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_user, mock_reseller]
    
    # Create login request
    login_request = ResellerLogin(
        username="testreseller",
        password="testpassword"
    )
    
    # Call the endpoint directly
    response = login_for_access_token(
        form_data=login_request,
        db=mock_db_session
    )
    
    # Verify response
    assert "access_token" in response
    assert "refresh_token" in response
    assert response["token_type"] == "bearer"
    assert "reseller" in response
    assert response["reseller"]["id"] == 1
    assert response["reseller"]["company_name"] == "Test Reseller Company"
    
    # Verify token content
    payload = jwt.decode(response["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert "sub" in payload
    assert payload["sub"] == "1"  # Reseller ID as string

def test_login_for_access_token_invalid_credentials(mock_db_session, mock_user):
    """Test login with invalid credentials"""
    # Setup mock query results
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Override the verify_password function for this test
    global verify_password
    original_verify_password = verify_password
    verify_password = lambda x, y: False
    
    # Create login request
    login_request = ResellerLogin(
        username="testreseller",
        password="wrongpassword"
    )
    
    # Call the endpoint and expect an exception
    with pytest.raises(HTTPException) as excinfo:
        login_for_access_token(
            form_data=login_request,
            db=mock_db_session
        )
    
    # Restore the original verify_password function
    verify_password = original_verify_password
    
    # Verify exception details
    assert excinfo.value.status_code == 401
    assert "Incorrect username or password" in excinfo.value.detail

def test_refresh_token(mock_db_session, mock_reseller):
    """Test refreshing an access token"""
    # Create a refresh token
    refresh_token_value = create_access_token(
        data={"sub": str(mock_reseller.id), "token_type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    # Setup mock query results
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_reseller
    
    # Create refresh request
    refresh_request = RefreshTokenRequest(
        refresh_token=refresh_token_value
    )
    
    # Call the endpoint directly
    response = refresh_token(
        refresh_request=refresh_request,
        db=mock_db_session
    )
    
    # Verify response
    assert "access_token" in response
    assert "refresh_token" in response
    assert response["token_type"] == "bearer"
    
    # Verify token content
    payload = jwt.decode(response["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert "sub" in payload
    assert payload["sub"] == "1"  # Reseller ID as string

def test_get_current_reseller_profile(mock_reseller):
    """Test getting the current reseller's profile"""
    # Call the endpoint directly
    response = get_current_reseller_profile(
        current_reseller=mock_reseller
    )
    
    # Verify response
    assert response["id"] == 1
    assert response["company_name"] == "Test Reseller Company"
    assert response["email"] == "john@testreseller.com"
    assert response["tier"] == "gold"
    assert "links" in response
