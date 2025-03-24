"""
Pytest configuration for customer module tests.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add project root to Python path to enable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)
print(f"Added {project_root} to Python path")

from backend_core.database import Base
from modules.customer import models


# Create async test engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True
)

# Create async session factory
TestingSessionLocal = sessionmaker(
    bind=test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@pytest.fixture
async def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestingSessionLocal() as session:
        yield session
    
    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit tests."""
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()
    
    return session


@pytest.fixture
def sample_individual_customer_data():
    """Return sample data for an individual customer."""
    return {
        "customer_type": models.CustomerType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "username": "johndoe",
        "password": "SecurePassword123",
        "status": models.CustomerStatus.ACTIVE,
        "subscription_state": models.SubscriptionState.ACTIVE
    }


@pytest.fixture
def sample_business_customer_data():
    """Return sample data for a business customer."""
    return {
        "customer_type": models.CustomerType.BUSINESS,
        "company_name": "Acme Corporation",
        "tax_id": "123456789",
        "registration_number": "REG123456",
        "email": "info@acme.com",
        "phone": "+1987654321",
        "username": "acmecorp",
        "password": "SecurePassword123",
        "status": models.CustomerStatus.ACTIVE,
        "subscription_state": models.SubscriptionState.ACTIVE
    }


@pytest.fixture
def sample_address_data():
    """Return sample data for a customer address."""
    return {
        "address_type": models.AddressType.BILLING,
        "street_address1": "123 Main St",
        "street_address2": "Apt 4B",
        "city": "Springfield",
        "state_province": "IL",
        "postal_code": "62701",
        "country": "United States",
        "is_default": True
    }


@pytest.fixture
def sample_contact_data():
    """Return sample data for a customer contact."""
    return {
        "contact_type": models.ContactType.PRIMARY,
        "first_name": "Jane",
        "last_name": "Smith",
        "position": "CTO",
        "department": "IT",
        "email": "jane.smith@acme.com",
        "phone": "+1122334455",
        "is_primary": True
    }


@pytest.fixture
def sample_communication_preference_data():
    """Return sample data for communication preferences."""
    return {
        "communication_type": models.CommunicationType.EMAIL,
        "enabled": True,
        "billing_notifications": True,
        "service_notifications": True,
        "marketing_communications": False,
        "technical_notifications": True,
        "emergency_alerts": True
    }


@pytest.fixture
def sample_document_data():
    """Return sample data for a customer document."""
    return {
        "document_type": models.DocumentType.ID_CARD,
        "document_number": "ID123456",
        "document_name": "National ID Card",
        "file_path": "/tmp/customer_documents/1/id_card.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
        "issue_date": datetime.utcnow() - timedelta(days=365),
        "expiry_date": datetime.utcnow() + timedelta(days=365),
        "verification_status": models.VerificationStatus.PENDING
    }


@pytest.fixture
def sample_note_data():
    """Return sample data for a customer note."""
    return {
        "title": "Initial Contact",
        "content": "Customer inquired about premium services.",
        "created_by": "support_agent1",
        "is_important": False,
        "is_private": True
    }


@pytest.fixture
def sample_email_verification_data():
    """Return sample data for email verification."""
    return {
        "email": "john.doe@example.com",
        "verification_token": "abcdef123456",
        "status": models.VerificationStatus.PENDING,
        "expires_at": datetime.utcnow() + timedelta(days=1)
    }


@pytest.fixture
def sample_tag_data():
    """Return sample data for a customer tag."""
    return {
        "name": "VIP",
        "description": "Very Important Customer",
        "color": "#FFD700",
        "auto_assign": False
    }


@pytest.fixture
async def create_individual_customer(db_session):
    """Create and return a sample individual customer."""
    customer = models.Customer(
        customer_number="CUST-001",
        customer_type=models.CustomerType.INDIVIDUAL,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        username="johndoe",
        password_hash="hashed_password",
        status=models.CustomerStatus.ACTIVE,
        subscription_state=models.SubscriptionState.ACTIVE
    )
    
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    
    return customer


@pytest.fixture
async def create_business_customer(db_session):
    """Create and return a sample business customer."""
    customer = models.Customer(
        customer_number="CUST-002",
        customer_type=models.CustomerType.BUSINESS,
        company_name="Acme Corporation",
        tax_id="123456789",
        registration_number="REG123456",
        email="info@acme.com",
        phone="+1987654321",
        username="acmecorp",
        password_hash="hashed_password",
        status=models.CustomerStatus.ACTIVE,
        subscription_state=models.SubscriptionState.ACTIVE
    )
    
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    
    return customer


@pytest.fixture
async def create_customer_with_address(db_session, create_individual_customer):
    """Create a customer with an address."""
    customer = create_individual_customer
    
    address = models.CustomerAddress(
        customer_id=customer.id,
        address_type=models.AddressType.BILLING,
        street_address1="123 Main St",
        street_address2="Apt 4B",
        city="Springfield",
        state_province="IL",
        postal_code="62701",
        country="United States",
        is_default=True
    )
    
    db_session.add(address)
    await db_session.commit()
    await db_session.refresh(address)
    
    return customer, address


@pytest.fixture
async def create_customer_with_document(db_session, create_individual_customer):
    """Create a customer with a document."""
    customer = create_individual_customer
    
    document = models.CustomerDocument(
        customer_id=customer.id,
        document_type=models.DocumentType.ID_CARD,
        document_number="ID123456",
        document_name="National ID Card",
        file_path="/tmp/customer_documents/1/id_card.pdf",
        file_size=1024,
        mime_type="application/pdf",
        issue_date=datetime.utcnow() - timedelta(days=365),
        expiry_date=datetime.utcnow() + timedelta(days=365),
        verification_status=models.VerificationStatus.PENDING
    )
    
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    return customer, document


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing document uploads."""
    mock_file = MagicMock()
    mock_file.filename = "id_card.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.file.read = AsyncMock(return_value=b"test file content")
    mock_file.file.seek = AsyncMock()
    
    return mock_file
