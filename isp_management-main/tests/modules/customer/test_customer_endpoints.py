"""
Tests for the Customer Management Module API endpoints.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from modules.customer.models import (
    Customer,
    CustomerType,
    CustomerStatus,
    SubscriptionState,
    CustomerAddress,
    AddressType,
    CustomerContact,
    ContactType,
    CommunicationPreference,
    CommunicationType,
    CustomerDocument,
    DocumentType,
    VerificationStatus,
    CustomerNote,
    CustomerTagDefinition,
    EmailVerification
)
from modules.customer.endpoints import router as customer_router
from backend_core.auth import get_current_user


# Test app setup
app = FastAPI()
app.include_router(customer_router)


# Mock the get_current_user dependency
async def mock_current_user():
    """Mock the current user for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["admin"]
    }


app.dependency_overrides[get_current_user] = mock_current_user


# Fixtures
@pytest.fixture
def test_client():
    """Fixture for FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_customer_service():
    """Fixture to mock the CustomerService."""
    with patch("isp_management.modules.customer.endpoints.customer_service") as mock:
        yield mock


@pytest.fixture
def mock_communication_service():
    """Fixture to mock the CommunicationService."""
    with patch("isp_management.modules.customer.communication_endpoints.communication_service") as mock:
        yield mock


@pytest.fixture
def mock_verification_service():
    """Fixture to mock the VerificationService."""
    with patch("isp_management.modules.customer.verification_endpoints.verification_service") as mock:
        yield mock


@pytest.fixture
def mock_document_service():
    """Fixture to mock the CustomerDocumentService."""
    with patch("isp_management.modules.customer.document_endpoints.document_service") as mock:
        yield mock


@pytest.fixture
def sample_customer():
    """Fixture for a sample customer."""
    return Customer(
        id=1,
        uuid=uuid.uuid4(),
        customer_number="CUST-001",
        customer_type=CustomerType.INDIVIDUAL,
        status=CustomerStatus.ACTIVE,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        username="johndoe",
        is_email_verified=True,
        email_verification_date=datetime.utcnow(),
        subscription_state=SubscriptionState.ACTIVE,
        subscription_start_date=datetime.utcnow(),
        subscription_end_date=datetime.utcnow() + timedelta(days=365),
        marketing_consent=True,
        marketing_consent_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_address():
    """Fixture for a sample address."""
    return CustomerAddress(
        id=1,
        customer_id=1,
        address_type=AddressType.BILLING,
        street_address1="123 Main St",
        city="Anytown",
        postal_code="12345",
        country="US",
        is_default=True,
        is_verified=True,
        verification_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_contact():
    """Fixture for a sample contact."""
    return CustomerContact(
        id=1,
        customer_id=1,
        contact_type=ContactType.PRIMARY,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1234567890",
        is_primary=True,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_communication_preference():
    """Fixture for a sample communication preference."""
    return CommunicationPreference(
        id=1,
        customer_id=1,
        communication_type=CommunicationType.EMAIL,
        enabled=True,
        billing_notifications=True,
        service_notifications=True,
        marketing_communications=False,
        technical_notifications=True,
        emergency_alerts=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_document():
    """Fixture for a sample document."""
    return CustomerDocument(
        id=1,
        customer_id=1,
        document_type=DocumentType.ID_CARD,
        document_name="ID Card",
        file_path="/tmp/documents/id_card.pdf",
        file_size=1024,
        mime_type="application/pdf",
        verification_status=VerificationStatus.VERIFIED,
        verified_by="Admin User",
        verification_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_note():
    """Fixture for a sample note."""
    return CustomerNote(
        id=1,
        customer_id=1,
        title="Test Note",
        content="This is a test note",
        is_important=True,
        is_private=False,
        created_by="Admin User",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_tag():
    """Fixture for a sample tag."""
    return CustomerTagDefinition(
        id=1,
        name="VIP",
        description="Very Important Customer",
        color="#FF0000",
        auto_assign=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_email_verification():
    """Fixture for a sample email verification."""
    return EmailVerification(
        id=1,
        customer_id=1,
        email="john.doe@example.com",
        token="test-token",
        status=VerificationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# Tests for customer endpoints
def test_create_customer(test_client, mock_customer_service, sample_customer):
    """Test creating a customer."""
    # Mock the create_customer method to return the sample customer
    mock_customer_service.create_customer.return_value = sample_customer
    
    # Create a customer
    response = test_client.post(
        "/customers/",
        json={
            "customer_type": "INDIVIDUAL",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "username": "johndoe",
            "password": "password123",
            "status": "ACTIVE",
            "subscription_state": "ACTIVE",
            "marketing_consent": True
        }
    )
    
    # Assert the response
    assert response.status_code == 201
    assert response.json()["first_name"] == "John"
    assert response.json()["last_name"] == "Doe"
    assert response.json()["email"] == "john.doe@example.com"
    
    # Assert the service method was called
    mock_customer_service.create_customer.assert_called_once()


def test_get_customer(test_client, mock_customer_service, sample_customer):
    """Test getting a customer by ID."""
    # Mock the get_customer method to return the sample customer
    mock_customer_service.get_customer.return_value = sample_customer
    
    # Get the customer
    response = test_client.get("/customers/1")
    
    # Assert the response
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["first_name"] == "John"
    assert response.json()["last_name"] == "Doe"
    
    # Assert the service method was called
    mock_customer_service.get_customer.assert_called_once()


def test_update_customer(test_client, mock_customer_service, sample_customer):
    """Test updating a customer."""
    # Mock the update_customer method to return the updated customer
    updated_customer = sample_customer
    updated_customer.first_name = "Jane"
    updated_customer.last_name = "Smith"
    mock_customer_service.update_customer.return_value = updated_customer
    
    # Update the customer
    response = test_client.put(
        "/customers/1",
        json={
            "first_name": "Jane",
            "last_name": "Smith"
        }
    )
    
    # Assert the response
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"
    assert response.json()["last_name"] == "Smith"
    
    # Assert the service method was called
    mock_customer_service.update_customer.assert_called_once()


def test_delete_customer(test_client, mock_customer_service):
    """Test deleting a customer."""
    # Mock the delete_customer method
    mock_customer_service.delete_customer.return_value = None
    
    # Delete the customer
    response = test_client.delete("/customers/1")
    
    # Assert the response
    assert response.status_code == 204
    
    # Assert the service method was called
    mock_customer_service.delete_customer.assert_called_once()


def test_update_subscription_state(test_client, mock_customer_service, sample_customer):
    """Test updating a customer's subscription state."""
    # Mock the update_subscription_state method to return the updated customer
    updated_customer = sample_customer
    updated_customer.subscription_state = SubscriptionState.SUSPENDED
    mock_customer_service.update_subscription_state.return_value = updated_customer
    
    # Update the subscription state
    response = test_client.put(
        "/customers/1/subscription-state",
        json={
            "subscription_state": "SUSPENDED",
            "update_dates": True
        }
    )
    
    # Assert the response
    assert response.status_code == 200
    assert response.json()["subscription_state"] == "SUSPENDED"
    
    # Assert the service method was called
    mock_customer_service.update_subscription_state.assert_called_once()


# Tests for address endpoints
def test_create_address(test_client, mock_customer_service, sample_address):
    """Test creating an address for a customer."""
    # Mock the execute method to return the sample customer and then None for address check
    mock_execute = MagicMock()
    mock_execute.return_value.scalars.return_value.first.side_effect = [
        sample_address.customer,  # First call: check if customer exists
        None  # Second call: check if default address exists
    ]
    
    with patch("isp_management.modules.customer.address_endpoints.session.execute", mock_execute):
        # Mock the add method
        mock_add = MagicMock()
        with patch("isp_management.modules.customer.address_endpoints.session.add", mock_add):
            # Create an address
            response = test_client.post(
                "/customers/1/addresses/",
                json={
                    "address_type": "BILLING",
                    "street_address1": "123 Main St",
                    "city": "Anytown",
                    "postal_code": "12345",
                    "country": "US",
                    "is_default": True
                }
            )
            
            # Assert the response
            assert response.status_code == 201


# Tests for contact endpoints
def test_create_contact(test_client, mock_customer_service, sample_contact):
    """Test creating a contact for a customer."""
    # Mock the execute method to return the sample customer and then None for contact check
    mock_execute = MagicMock()
    mock_execute.return_value.scalars.return_value.first.side_effect = [
        sample_contact.customer,  # First call: check if customer exists
        None  # Second call: check if primary contact exists
    ]
    
    with patch("isp_management.modules.customer.contact_endpoints.session.execute", mock_execute):
        # Mock the add method
        mock_add = MagicMock()
        with patch("isp_management.modules.customer.contact_endpoints.session.add", mock_add):
            # Create a contact
            response = test_client.post(
                "/customers/1/contacts/",
                json={
                    "contact_type": "PRIMARY",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "email": "jane.doe@example.com",
                    "phone": "+1234567890",
                    "is_primary": True,
                    "is_active": True
                }
            )
            
            # Assert the response
            assert response.status_code == 201


# Tests for communication preference endpoints
def test_create_communication_preference(test_client, mock_communication_service, sample_communication_preference):
    """Test creating a communication preference for a customer."""
    # Mock the create_preference method to return the sample preference
    mock_communication_service.create_preference.return_value = sample_communication_preference
    
    # Create a preference
    response = test_client.post(
        "/customers/1/communication-preferences/",
        json={
            "communication_type": "EMAIL",
            "enabled": True,
            "billing_notifications": True,
            "service_notifications": True,
            "marketing_communications": False,
            "technical_notifications": True,
            "emergency_alerts": True
        }
    )
    
    # Assert the response
    assert response.status_code == 201
    assert response.json()["communication_type"] == "EMAIL"
    assert response.json()["enabled"] == True
    
    # Assert the service method was called
    mock_communication_service.create_preference.assert_called_once()


# Tests for verification endpoints
def test_create_email_verification(test_client, mock_verification_service, sample_email_verification):
    """Test creating an email verification for a customer."""
    # Mock the create_email_verification method to return the sample verification
    mock_verification_service.create_email_verification.return_value = sample_email_verification
    
    # Create a verification
    response = test_client.post(
        "/customers/1/verify-email",
        json={}
    )
    
    # Assert the response
    assert response.status_code == 200
    assert response.json()["email"] == "john.doe@example.com"
    assert response.json()["status"] == "PENDING"
    
    # Assert the service method was called
    mock_verification_service.create_email_verification.assert_called_once()


def test_verify_email(test_client, mock_verification_service):
    """Test verifying an email with a token."""
    # Mock the verify_email method to return a customer ID
    mock_verification_service.verify_email.return_value = 1
    
    # Verify an email
    response = test_client.get(
        "/customers/verify-email?token=test-token"
    )
    
    # Assert the response
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert response.json()["customer_id"] == 1
    
    # Assert the service method was called
    mock_verification_service.verify_email.assert_called_once_with(
        session=mock_verification_service.verify_email.call_args[1]["session"],
        token="test-token"
    )


# Add more tests for other endpoints as needed
