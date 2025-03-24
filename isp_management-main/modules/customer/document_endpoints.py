"""
API endpoints for customer documents.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import DocumentType, VerificationStatus
from modules.customer.schemas import DocumentCreate, DocumentVerificationUpdate, DocumentResponse
from modules.customer.document_service import CustomerDocumentService

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/documents",
    tags=["customer-documents"],
)

# Initialize service
document_service = CustomerDocumentService()

# Role checkers
allow_admin = RoleChecker(["admin"])
allow_customer_manager = RoleChecker(["admin", "customer_manager"])
allow_customer_agent = RoleChecker(["admin", "customer_manager", "customer_agent"])


# Exception handler
def handle_exceptions(func):
    """Decorator to handle common exceptions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return wrapper


# Document endpoints
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def upload_document(
    document_data: DocumentCreate = Depends(),
    file: UploadFile = File(...),
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Upload a new document for a customer."""
    # Get document storage path from environment variable
    document_path = os.environ.get("CUSTOMER_DOCUMENT_PATH", "./documents")
    
    # Create customer document directory if it doesn't exist
    customer_doc_dir = os.path.join(document_path, f"customer_{customer_id}")
    os.makedirs(customer_doc_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{document_data.document_type.value}_{timestamp}{file_extension}"
    file_path = os.path.join(customer_doc_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Get file size and MIME type
    file_size = os.path.getsize(file_path)
    mime_type = file.content_type
    
    # Create document record
    document = await document_service.create_document(
        session=session,
        customer_id=customer_id,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        **document_data.dict()
    )
    
    await session.commit()
    await session.refresh(document)
    
    return DocumentResponse.from_orm(document)


@router.get("/", response_model=List[DocumentResponse])
@handle_exceptions
async def get_customer_documents(
    customer_id: int = Path(..., description="Customer ID"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    verification_status: Optional[VerificationStatus] = Query(None, description="Filter by verification status"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all documents for a customer."""
    documents = await document_service.get_customer_documents(
        session=session,
        customer_id=customer_id,
        document_type=document_type,
        verification_status=verification_status
    )
    
    return [DocumentResponse.from_orm(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
@handle_exceptions
async def get_document(
    customer_id: int = Path(..., description="Customer ID"),
    document_id: int = Path(..., description="Document ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific document for a customer."""
    document = await document_service.get_document(
        session=session,
        document_id=document_id
    )
    
    # Verify that document belongs to the specified customer
    if document.customer_id != customer_id:
        raise NotFoundException(f"Document with ID {document_id} not found for customer {customer_id}")
    
    return DocumentResponse.from_orm(document)


@router.put("/{document_id}/verify", response_model=DocumentResponse)
@handle_exceptions
async def verify_document(
    verification_data: DocumentVerificationUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    document_id: int = Path(..., description="Document ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Update verification status of a document."""
    # Get document to verify it belongs to the customer
    document = await document_service.get_document(
        session=session,
        document_id=document_id
    )
    
    if document.customer_id != customer_id:
        raise NotFoundException(f"Document with ID {document_id} not found for customer {customer_id}")
    
    # Update verification status
    updated_document = await document_service.update_verification_status(
        session=session,
        document_id=document_id,
        verification_status=verification_data.verification_status,
        verified_by=verification_data.verified_by,
        verification_notes=verification_data.verification_notes
    )
    
    await session.commit()
    await session.refresh(updated_document)
    
    return DocumentResponse.from_orm(updated_document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_document(
    customer_id: int = Path(..., description="Customer ID"),
    document_id: int = Path(..., description="Document ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Delete a document for a customer."""
    # Get document to verify it belongs to the customer
    document = await document_service.get_document(
        session=session,
        document_id=document_id
    )
    
    if document.customer_id != customer_id:
        raise NotFoundException(f"Document with ID {document_id} not found for customer {customer_id}")
    
    # Delete physical file if it exists
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete document record
    await document_service.delete_document(
        session=session,
        document_id=document_id
    )
    
    await session.commit()
    
    return None
