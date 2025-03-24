"""
Tests for the Customer Management Module services.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

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
    EmailVerification,
    CustomerTagDefinition
)
from modules.customer.services import CustomerService
from modules.customer.communication_service import CommunicationService
from modules.customer.verification_service import VerificationService
from modules.customer.document_service import CustomerDocumentService
from backend_core.exceptions import NotFoundException, ValidationException, DuplicateException


# Fixtures
@pytest.fixture
async def customer_service():
    """Fixture for CustomerService."""
    return CustomerService()


@pytest.fixture
async def communication_service():
    """Fixture for CommunicationService."""
    return CommunicationService()


@pytest.fixture
async def verification_service():
    """Fixture for VerificationService."""
    return VerificationService()


@pytest.fixture
async def document_service():
    """Fixture for CustomerDocumentService."""
    return CustomerDocumentService(document_storage_path="/tmp/customer_documents")


@pytest.fixture
async def mock_session():
    """Fixture for mocked Session."""
    session = MagicMock(spec=Session)
    
    # Mock commit and refresh methods
    session.commit = MagicMock(return_value=None)
    session.refresh = MagicMock(return_value=None)
    
    # Mock execute method to return a result with a scalars method
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=None)
    result_mock.all = MagicMock(return_value=[])
    session.execute = MagicMock(return_value=result_mock)
    
    # Mock add method
    session.add = MagicMock(return_value=None)
    
    # Mock delete method
    session.delete = MagicMock(return_value=None)
    
    return session


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


# Tests for CustomerService
@pytest.mark.asyncio
async def test_create_customer(customer_service, mock_session, sample_customer):
    """Test creating a customer."""
    # Mock session to return no existing customer with the same email
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=None)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Mock add to set the ID
    def mock_add(customer):
        customer.id = 1
        return None
    
    mock_session.add = MagicMock(side_effect=mock_add)
    
    # Mock the generate_customer_number function
    with patch('isp_management.modules.customer.services.generate_customer_number', return_value="CUST-001"):
        customer = await customer_service.create_customer(
            session=mock_session,
            customer_type=CustomerType.INDIVIDUAL,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            username="johndoe",
            password="password123",
            status=CustomerStatus.ACTIVE,
            subscription_state=SubscriptionState.ACTIVE,
            marketing_consent=True
        )
    
    # Assert customer was created with expected values
    assert customer.customer_type == CustomerType.INDIVIDUAL
    assert customer.first_name == "John"
    assert customer.last_name == "Doe"
    assert customer.email == "john.doe@example.com"
    assert customer.phone == "+1234567890"
    assert customer.username == "johndoe"
    assert customer.status == CustomerStatus.ACTIVE
    assert customer.subscription_state == SubscriptionState.ACTIVE
    assert customer.marketing_consent == True
    
    # Assert session methods were called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_not_called()  # Commit is done by the caller


@pytest.mark.asyncio
async def test_create_customer_duplicate_email(customer_service, mock_session, sample_customer):
    """Test creating a customer with a duplicate email."""
    # Mock session to return an existing customer with the same email
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Attempt to create a customer with the same email
    with pytest.raises(DuplicateException):
        await customer_service.create_customer(
            session=mock_session,
            customer_type=CustomerType.INDIVIDUAL,
            first_name="Jane",
            last_name="Doe",
            email="john.doe@example.com",  # Same email as sample_customer
            phone="+1987654321",
            username="janedoe",
            password="password123",
            status=CustomerStatus.ACTIVE,
            subscription_state=SubscriptionState.ACTIVE,
            marketing_consent=True
        )


@pytest.mark.asyncio
async def test_get_customer(customer_service, mock_session, sample_customer):
    """Test getting a customer by ID."""
    # Mock session to return the sample customer
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Get the customer
    customer = await customer_service.get_customer(
        session=mock_session,
        customer_id=1
    )
    
    # Assert the returned customer is the sample customer
    assert customer == sample_customer
    
    # Assert execute was called with the correct query
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args[0][0]
    assert isinstance(call_args, select)
    assert call_args.whereclause is not None


@pytest.mark.asyncio
async def test_get_customer_not_found(customer_service, mock_session):
    """Test getting a non-existent customer."""
    # Mock session to return no customer
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=None)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Attempt to get a non-existent customer
    with pytest.raises(NotFoundException):
        await customer_service.get_customer(
            session=mock_session,
            customer_id=999
        )


@pytest.mark.asyncio
async def test_update_customer(customer_service, mock_session, sample_customer):
    """Test updating a customer."""
    # Mock session to return the sample customer
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Update the customer
    updated_customer = await customer_service.update_customer(
        session=mock_session,
        customer_id=1,
        first_name="Jane",
        last_name="Smith",
        phone="+1987654321"
    )
    
    # Assert the customer was updated with the new values
    assert updated_customer.first_name == "Jane"
    assert updated_customer.last_name == "Smith"
    assert updated_customer.phone == "+1987654321"
    
    # Assert the other fields remain unchanged
    assert updated_customer.email == "john.doe@example.com"
    assert updated_customer.username == "johndoe"
    assert updated_customer.status == CustomerStatus.ACTIVE
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_customer(customer_service, mock_session, sample_customer):
    """Test deleting a customer."""
    # Mock session to return the sample customer
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Delete the customer
    await customer_service.delete_customer(
        session=mock_session,
        customer_id=1
    )
    
    # Assert delete was called with the sample customer
    mock_session.delete.assert_called_once_with(sample_customer)
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_subscription_state(customer_service, mock_session, sample_customer):
    """Test updating a customer's subscription state."""
    # Mock session to return the sample customer
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=result_mock)
    result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=result_mock)
    
    # Update the subscription state
    updated_customer = await customer_service.update_subscription_state(
        session=mock_session,
        customer_id=1,
        subscription_state=SubscriptionState.SUSPENDED,
        update_dates=True
    )
    
    # Assert the subscription state was updated
    assert updated_customer.subscription_state == SubscriptionState.SUSPENDED
    
    # Assert the dates were updated
    assert updated_customer.subscription_end_date is not None
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


# Tests for CommunicationService
@pytest.mark.asyncio
async def test_create_preference(communication_service, mock_session, sample_customer):
    """Test creating a communication preference."""
    # Mock session to return the sample customer
    customer_result_mock = MagicMock()
    customer_result_mock.scalars = MagicMock(return_value=customer_result_mock)
    customer_result_mock.first = MagicMock(return_value=sample_customer)
    
    # Mock session to return no existing preference
    pref_result_mock = MagicMock()
    pref_result_mock.scalars = MagicMock(return_value=pref_result_mock)
    pref_result_mock.first = MagicMock(return_value=None)
    
    # Set up the execute mock to return different results based on the query
    def mock_execute(query):
        if "customers" in str(query):
            return customer_result_mock
        else:
            return pref_result_mock
    
    mock_session.execute = MagicMock(side_effect=mock_execute)
    
    # Create a preference
    preference = await communication_service.create_preference(
        session=mock_session,
        customer_id=1,
        communication_type=CommunicationType.EMAIL,
        enabled=True,
        billing_notifications=True,
        service_notifications=True,
        marketing_communications=False,
        technical_notifications=True,
        emergency_alerts=True
    )
    
    # Assert the preference was created with the expected values
    assert preference.customer_id == 1
    assert preference.communication_type == CommunicationType.EMAIL
    assert preference.enabled == True
    assert preference.billing_notifications == True
    assert preference.service_notifications == True
    assert preference.marketing_communications == False
    assert preference.technical_notifications == True
    assert preference.emergency_alerts == True
    
    # Assert add was called
    mock_session.add.assert_called_once()
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


# Tests for VerificationService
@pytest.mark.asyncio
async def test_create_email_verification(verification_service, mock_session, sample_customer):
    """Test creating an email verification."""
    # Mock session to return the sample customer
    customer_result_mock = MagicMock()
    customer_result_mock.scalars = MagicMock(return_value=customer_result_mock)
    customer_result_mock.first = MagicMock(return_value=sample_customer)
    
    # Mock session to return no existing verification
    verification_result_mock = MagicMock()
    verification_result_mock.scalars = MagicMock(return_value=verification_result_mock)
    verification_result_mock.first = MagicMock(return_value=None)
    verification_result_mock.all = MagicMock(return_value=[])
    
    # Set up the execute mock to return different results based on the query
    def mock_execute(query):
        if "customers" in str(query):
            return customer_result_mock
        else:
            return verification_result_mock
    
    mock_session.execute = MagicMock(side_effect=mock_execute)
    
    # Mock the generate_verification_token function
    with patch('isp_management.modules.customer.verification_service.generate_verification_token', return_value="test-token"):
        # Create a verification
        verification = await verification_service.create_email_verification(
            session=mock_session,
            customer_id=1
        )
    
    # Assert the verification was created with the expected values
    assert verification.customer_id == 1
    assert verification.email == "john.doe@example.com"
    assert verification.token == "test-token"
    assert verification.status == VerificationStatus.PENDING
    assert verification.expires_at > datetime.utcnow()
    
    # Assert add was called
    mock_session.add.assert_called_once()
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


# Add more tests for other services and edge cases as needed
