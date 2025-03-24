"""
Document service for the Customer Management Module.
"""

import logging
import os
import uuid
import tempfile
from datetime import datetime
from typing import List, Optional, BinaryIO
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import (
    Customer,
    CustomerDocument,
    DocumentType,
    VerificationStatus
)

logger = logging.getLogger(__name__)


class CustomerDocumentService:
    """Service for managing customer documents."""
    
    def __init__(self, document_storage_path: str = None):
        """
        Initialize the document service.
        
        Args:
            document_storage_path: Path where documents will be stored
        """
        # Use a temporary directory for testing if no path is provided
        if document_storage_path is None:
            document_storage_path = os.environ.get(
                "CUSTOMER_DOCUMENT_PATH", 
                os.path.join(tempfile.gettempdir(), "customer_documents")
            )
            
        self.document_storage_path = document_storage_path
        
        # Ensure storage directory exists
        os.makedirs(document_storage_path, exist_ok=True)
    
    async def upload_document(
        self,
        session: AsyncSession,
        customer_id: int,
        document_type: DocumentType,
        document_name: str,
        document_file: BinaryIO,
        document_number: Optional[str] = None,
        issue_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        mime_type: Optional[str] = None
    ) -> CustomerDocument:
        """
        Upload a customer document.
        
        Args:
            session: Database session
            customer_id: Customer ID
            document_type: Type of document
            document_name: Name of document
            document_file: File object
            document_number: Document number (e.g., passport number)
            issue_date: Date document was issued
            expiry_date: Date document expires
            mime_type: MIME type of document
            
        Returns:
            Uploaded document
            
        Raises:
            NotFoundException: If customer not found
            ValidationException: If validation fails
        """
        # Check if customer exists
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        # Validate expiry date if provided
        if expiry_date and expiry_date < datetime.utcnow():
            raise ValidationException("Document is already expired")
        
        # Generate unique filename
        file_uuid = uuid.uuid4()
        file_extension = os.path.splitext(document_name)[1] if '.' in document_name else ''
        filename = f"{file_uuid}{file_extension}"
        
        # Create customer directory if it doesn't exist
        customer_dir = os.path.join(self.document_storage_path, str(customer_id))
        os.makedirs(customer_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(customer_dir, filename)
        relative_path = os.path.join(str(customer_id), filename)
        
        # Get file size
        document_file.seek(0, os.SEEK_END)
        file_size = document_file.tell()
        document_file.seek(0)
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(document_file.read())
        
        # Create document record
        document = CustomerDocument(
            customer_id=customer_id,
            document_type=document_type,
            document_number=document_number,
            document_name=document_name,
            file_path=relative_path,
            file_size=file_size,
            mime_type=mime_type,
            issue_date=issue_date,
            expiry_date=expiry_date,
            verification_status=VerificationStatus.PENDING
        )
        
        session.add(document)
        await session.flush()
        
        return document
    
    async def get_document(
        self,
        session: AsyncSession,
        document_id: int
    ) -> CustomerDocument:
        """
        Get a document by ID.
        
        Args:
            session: Database session
            document_id: Document ID
            
        Returns:
            Customer document
            
        Raises:
            NotFoundException: If document not found
        """
        result = await session.execute(
            select(CustomerDocument).where(CustomerDocument.id == document_id)
        )
        document = result.scalars().first()
        
        if not document:
            raise NotFoundException(f"Document with ID {document_id} not found")
        
        return document
    
    async def get_customer_documents(
        self,
        session: AsyncSession,
        customer_id: int,
        document_type: Optional[DocumentType] = None,
        verification_status: Optional[VerificationStatus] = None
    ) -> List[CustomerDocument]:
        """
        Get documents for a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            document_type: Filter by document type
            verification_status: Filter by verification status
            
        Returns:
            List of customer documents
            
        Raises:
            NotFoundException: If customer not found
        """
        # Check if customer exists
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        # Build query
        query = select(CustomerDocument).where(CustomerDocument.customer_id == customer_id)
        
        # Apply filters
        if document_type:
            query = query.where(CustomerDocument.document_type == document_type)
        if verification_status:
            query = query.where(CustomerDocument.verification_status == verification_status)
        
        # Execute query
        result = await session.execute(query)
        documents = result.scalars().all()
        
        return documents
    
    async def update_document(
        self,
        session: AsyncSession,
        document_id: int,
        **kwargs
    ) -> CustomerDocument:
        """
        Update a document.
        
        Args:
            session: Database session
            document_id: Document ID
            **kwargs: Fields to update
            
        Returns:
            Updated document
            
        Raises:
            NotFoundException: If document not found
            ValidationException: If validation fails
        """
        # Get document
        document = await self.get_document(session, document_id)
        
        # Validate expiry date if provided
        if 'expiry_date' in kwargs and kwargs['expiry_date'] < datetime.utcnow():
            raise ValidationException("Document is already expired")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(document, key):
                setattr(document, key, value)
        
        return document
    
    async def verify_document(
        self,
        session: AsyncSession,
        document_id: int,
        verified_by: str,
        verification_notes: Optional[str] = None
    ) -> CustomerDocument:
        """
        Mark a document as verified.
        
        Args:
            session: Database session
            document_id: Document ID
            verified_by: Name of person who verified the document
            verification_notes: Notes about verification
            
        Returns:
            Updated document
            
        Raises:
            NotFoundException: If document not found
        """
        # Get document
        document = await self.get_document(session, document_id)
        
        # Update verification status
        document.verification_status = VerificationStatus.VERIFIED
        document.verified_by = verified_by
        document.verification_date = datetime.utcnow()
        
        if verification_notes:
            document.verification_notes = verification_notes
        
        return document
    
    async def reject_document(
        self,
        session: AsyncSession,
        document_id: int,
        verified_by: str,
        verification_notes: str
    ) -> CustomerDocument:
        """
        Mark a document as failed verification.
        
        Args:
            session: Database session
            document_id: Document ID
            verified_by: Name of person who rejected the document
            verification_notes: Reason for rejection
            
        Returns:
            Updated document
            
        Raises:
            NotFoundException: If document not found
            ValidationException: If verification notes not provided
        """
        # Get document
        document = await self.get_document(session, document_id)
        
        # Require verification notes for rejection
        if not verification_notes:
            raise ValidationException("Verification notes are required for document rejection")
        
        # Update verification status
        document.verification_status = VerificationStatus.FAILED
        document.verified_by = verified_by
        document.verification_date = datetime.utcnow()
        document.verification_notes = verification_notes
        
        return document
    
    async def delete_document(
        self,
        session: AsyncSession,
        document_id: int
    ) -> None:
        """
        Delete a document.
        
        Args:
            session: Database session
            document_id: Document ID
            
        Raises:
            NotFoundException: If document not found
        """
        # Get document
        document = await self.get_document(session, document_id)
        
        # Delete file
        file_path = os.path.join(self.document_storage_path, document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete document record
        await session.delete(document)
    
    async def check_expired_documents(
        self,
        session: AsyncSession,
        customer_id: Optional[int] = None
    ) -> List[CustomerDocument]:
        """
        Check for expired documents.
        
        Args:
            session: Database session
            customer_id: Optional customer ID to check only their documents
            
        Returns:
            List of expired documents
        """
        now = datetime.utcnow()
        
        # Build query
        query = (
            select(CustomerDocument)
            .where(
                CustomerDocument.expiry_date.is_not(None),
                CustomerDocument.expiry_date < now
            )
        )
        
        # Filter by customer if specified
        if customer_id:
            query = query.where(CustomerDocument.customer_id == customer_id)
        
        # Execute query
        result = await session.execute(query)
        expired_documents = result.scalars().all()
        
        return expired_documents
