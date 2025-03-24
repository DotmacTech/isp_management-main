"""
Tests for the Customer Document Service.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

from sqlalchemy.orm import Session
from fastapi import UploadFile

from modules.customer.models import (
    Customer,
    CustomerType,
    CustomerStatus,
    CustomerDocument,
    DocumentType,
    VerificationStatus
)
from modules.customer.document_service import CustomerDocumentService
from backend_core.exceptions import NotFoundException, ValidationException


# Fixtures
@pytest.fixture
def document_service():
    """Fixture for CustomerDocumentService."""
    return CustomerDocumentService(document_storage_path="/tmp/customer_documents")


@pytest.fixture
async def mock_session():
    """Fixture for mocked AsyncSession."""
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
        file_path="/tmp/customer_documents/1/id_card.pdf",
        file_size=1024,
        mime_type="application/pdf",
        verification_status=VerificationStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_upload_file():
    """Fixture for a mock UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = "id_card.pdf"
    file.content_type = "application/pdf"
    file.file = MagicMock()
    file.file.read = MagicMock(return_value=b"test file content")
    return file


# Tests
@pytest.mark.asyncio
async def test_upload_document(document_service, mock_session, sample_customer, mock_upload_file):
    """Test uploading a document."""
    # Mock session to return the sample customer
    customer_result_mock = MagicMock()
    customer_result_mock.scalars = MagicMock(return_value=customer_result_mock)
    customer_result_mock.first = MagicMock(return_value=sample_customer)
    mock_session.execute = MagicMock(return_value=customer_result_mock)
    
    # Mock os.makedirs to avoid creating directories
    with patch("os.makedirs") as mock_makedirs:
        # Mock open to avoid writing to disk
        with patch("builtins.open", mock_open()) as mock_file:
            # Mock os.path.getsize to return a file size
            with patch("os.path.getsize", return_value=1024):
                # Mock get_mime_type to return a MIME type
                with patch("isp_management.modules.customer.document_service.get_mime_type", return_value="application/pdf"):
                    # Upload a document
                    document = await document_service.upload_document(
                        session=mock_session,
                        customer_id=1,
                        document_type=DocumentType.ID_CARD,
                        file=mock_upload_file,
                        description="Customer ID Card"
                    )
    
    # Assert the document was created with the expected values
    assert document.customer_id == 1
    assert document.document_type == DocumentType.ID_CARD
    assert document.document_name == "id_card.pdf"
    assert document.file_size == 1024
    assert document.mime_type == "application/pdf"
    assert document.verification_status == VerificationStatus.PENDING
    assert document.description == "Customer ID Card"
    
    # Assert the directory was created
    mock_makedirs.assert_called_once()
    
    # Assert the file was written
    mock_file.assert_called_once()
    
    # Assert add was called
    mock_session.add.assert_called_once()
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_document(document_service, mock_session, sample_document):
    """Test getting a document by ID."""
    # Mock session to return the sample document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=sample_document)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Get the document
    document = await document_service.get_document(
        session=mock_session,
        document_id=1
    )
    
    # Assert the returned document is the sample document
    assert document == sample_document
    
    # Assert execute was called
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_document_not_found(document_service, mock_session):
    """Test getting a non-existent document."""
    # Mock session to return no document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=None)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Attempt to get a non-existent document
    with pytest.raises(NotFoundException):
        await document_service.get_document(
            session=mock_session,
            document_id=999
        )


@pytest.mark.asyncio
async def test_get_customer_documents(document_service, mock_session, sample_document):
    """Test getting all documents for a customer."""
    # Mock session to return a list with the sample document
    documents_result_mock = MagicMock()
    documents_result_mock.scalars = MagicMock(return_value=documents_result_mock)
    documents_result_mock.all = MagicMock(return_value=[sample_document])
    mock_session.execute = MagicMock(return_value=documents_result_mock)
    
    # Get the customer's documents
    documents = await document_service.get_customer_documents(
        session=mock_session,
        customer_id=1
    )
    
    # Assert the returned list contains the sample document
    assert len(documents) == 1
    assert documents[0] == sample_document
    
    # Assert execute was called
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_document_verification(document_service, mock_session, sample_document):
    """Test updating a document's verification status."""
    # Mock session to return the sample document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=sample_document)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Update the document's verification status
    updated_document = await document_service.update_document_verification(
        session=mock_session,
        document_id=1,
        verification_status=VerificationStatus.VERIFIED,
        verified_by="Admin User",
        verification_notes="Verified ID card"
    )
    
    # Assert the document was updated with the new values
    assert updated_document.verification_status == VerificationStatus.VERIFIED
    assert updated_document.verified_by == "Admin User"
    assert updated_document.verification_notes == "Verified ID card"
    assert updated_document.verification_date is not None
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_document(document_service, mock_session, sample_document):
    """Test deleting a document."""
    # Mock session to return the sample document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=sample_document)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Mock os.path.exists to return True
    with patch("os.path.exists", return_value=True):
        # Mock os.remove to avoid actually deleting files
        with patch("os.remove") as mock_remove:
            # Delete the document
            await document_service.delete_document(
                session=mock_session,
                document_id=1
            )
    
    # Assert delete was called with the sample document
    mock_session.delete.assert_called_once_with(sample_document)
    
    # Assert os.remove was called to delete the file
    mock_remove.assert_called_once_with(sample_document.file_path)
    
    # Assert commit was not called (it's done by the caller)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_document_file_path(document_service, mock_session, sample_document):
    """Test getting a document's file path."""
    # Mock session to return the sample document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=sample_document)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Mock os.path.exists to return True
    with patch("os.path.exists", return_value=True):
        # Get the document's file path
        file_path = await document_service.get_document_file_path(
            session=mock_session,
            document_id=1
        )
    
    # Assert the returned file path is the sample document's file path
    assert file_path == sample_document.file_path


@pytest.mark.asyncio
async def test_get_document_file_path_not_found(document_service, mock_session, sample_document):
    """Test getting a file path for a document whose file doesn't exist."""
    # Mock session to return the sample document
    document_result_mock = MagicMock()
    document_result_mock.scalars = MagicMock(return_value=document_result_mock)
    document_result_mock.first = MagicMock(return_value=sample_document)
    mock_session.execute = MagicMock(return_value=document_result_mock)
    
    # Mock os.path.exists to return False
    with patch("os.path.exists", return_value=False):
        # Attempt to get the document's file path
        with pytest.raises(NotFoundException):
            await document_service.get_document_file_path(
                session=mock_session,
                document_id=1
            )


# Add more tests for edge cases and other methods as needed
