"""
API endpoints for customer email verification.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.schemas import EmailVerificationCreate, EmailVerificationResponse, EmailVerificationResult
from modules.customer.verification_service import VerificationService

# Initialize router
router = APIRouter(
    tags=["customer-verification"],
)

# Initialize service
verification_service = VerificationService()

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


# Email verification endpoints
@router.post("/{customer_id}/verify-email", response_model=EmailVerificationResponse)
@handle_exceptions
async def create_email_verification(
    verification_data: EmailVerificationCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new email verification token for a customer."""
    verification = await verification_service.create_email_verification(
        session=session,
        customer_id=customer_id,
        email=verification_data.email
    )
    
    await session.commit()
    await session.refresh(verification)
    
    return EmailVerificationResponse.from_orm(verification)


@router.get("/verify-email", response_model=EmailVerificationResult)
@handle_exceptions
async def verify_email(
    token: str = Query(..., description="Verification token"),
    session: AsyncSession = Depends(get_session)
):
    """Verify an email using a token. This endpoint is public (no auth required)."""
    try:
        customer_id = await verification_service.verify_email(
            session=session,
            token=token
        )
        
        await session.commit()
        
        return EmailVerificationResult(
            success=True,
            message="Email verified successfully",
            customer_id=customer_id
        )
    except (NotFoundException, ValidationException) as e:
        return EmailVerificationResult(
            success=False,
            message=str(e)
        )
    except Exception as e:
        return EmailVerificationResult(
            success=False,
            message="An unexpected error occurred during verification"
        )


@router.get("/{customer_id}/email-verification-status", response_model=EmailVerificationResponse)
@handle_exceptions
async def get_email_verification_status(
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get the current email verification status for a customer."""
    verification = await verification_service.get_latest_verification(
        session=session,
        customer_id=customer_id
    )
    
    if not verification:
        raise NotFoundException(f"No email verification found for customer {customer_id}")
    
    return EmailVerificationResponse.from_orm(verification)


@router.delete("/{customer_id}/email-verification", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def cancel_email_verification(
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Cancel any pending email verification for a customer."""
    await verification_service.cancel_pending_verifications(
        session=session,
        customer_id=customer_id
    )
    
    await session.commit()
    
    return None
