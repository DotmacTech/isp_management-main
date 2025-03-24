"""
Verification service for the Customer Management Module.
"""

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import (
    Customer,
    EmailVerification,
    VerificationStatus
)
from modules.customer.utils import generate_verification_token, validate_email

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for managing customer verification."""
    
    def __init__(self, token_expiry_hours: int = 24):
        """
        Initialize the verification service.
        
        Args:
            token_expiry_hours: Number of hours before verification tokens expire
        """
        self.token_expiry_hours = token_expiry_hours
    
    async def create_email_verification(
        self,
        session: AsyncSession,
        customer_id: int,
        email: Optional[str] = None
    ) -> EmailVerification:
        """
        Create an email verification token.
        
        Args:
            session: Database session
            customer_id: Customer ID
            email: Email to verify (if different from customer's current email)
            
        Returns:
            Email verification object
            
        Raises:
            NotFoundException: If customer not found
            ValidationException: If email is invalid
        """
        # Get customer
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        # Use customer's email if none provided
        if not email:
            email = customer.email
        
        if not email:
            raise ValidationException("No email provided and customer has no email")
        
        # Validate email
        if not validate_email(email):
            raise ValidationException(f"Invalid email format: {email}")
        
        # Generate token
        token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
        
        # Create verification
        verification = EmailVerification(
            customer_id=customer_id,
            email=email,
            verification_token=token,
            status=VerificationStatus.PENDING,
            expires_at=expires_at
        )
        
        session.add(verification)
        await session.flush()
        
        return verification
    
    async def verify_email(
        self,
        session: AsyncSession,
        token: str
    ) -> Customer:
        """
        Verify an email using a verification token.
        
        Args:
            session: Database session
            token: Verification token
            
        Returns:
            Customer whose email was verified
            
        Raises:
            NotFoundException: If token not found
            ValidationException: If token is expired or already used
        """
        # Get verification
        verification_result = await session.execute(
            select(EmailVerification).where(EmailVerification.verification_token == token)
        )
        verification = verification_result.scalars().first()
        
        if not verification:
            raise NotFoundException(f"Verification token not found")
        
        # Check if already verified
        if verification.status == VerificationStatus.VERIFIED:
            raise ValidationException("Email already verified")
        
        # Check if expired
        if verification.status == VerificationStatus.EXPIRED or verification.expires_at < datetime.utcnow():
            verification.status = VerificationStatus.EXPIRED
            raise ValidationException("Verification token has expired")
        
        # Get customer
        customer_result = await session.execute(
            select(Customer).where(Customer.id == verification.customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {verification.customer_id} not found")
        
        # Update verification
        verification.status = VerificationStatus.VERIFIED
        verification.verified_at = datetime.utcnow()
        
        # Update customer email if different
        if verification.email != customer.email:
            customer.email = verification.email
        
        # Mark customer as email verified
        customer.is_email_verified = True
        customer.email_verification_date = datetime.utcnow()
        
        return customer
    
    async def get_verification(
        self,
        session: AsyncSession,
        verification_id: int
    ) -> EmailVerification:
        """
        Get a verification by ID.
        
        Args:
            session: Database session
            verification_id: Verification ID
            
        Returns:
            Email verification
            
        Raises:
            NotFoundException: If verification not found
        """
        result = await session.execute(
            select(EmailVerification).where(EmailVerification.id == verification_id)
        )
        verification = result.scalars().first()
        
        if not verification:
            raise NotFoundException(f"Verification with ID {verification_id} not found")
        
        return verification
    
    async def get_verification_by_token(
        self,
        session: AsyncSession,
        token: str
    ) -> EmailVerification:
        """
        Get a verification by token.
        
        Args:
            session: Database session
            token: Verification token
            
        Returns:
            Email verification
            
        Raises:
            NotFoundException: If verification not found
        """
        result = await session.execute(
            select(EmailVerification).where(EmailVerification.verification_token == token)
        )
        verification = result.scalars().first()
        
        if not verification:
            raise NotFoundException(f"Verification token not found")
        
        return verification
    
    async def cancel_verification(
        self,
        session: AsyncSession,
        verification_id: int
    ) -> EmailVerification:
        """
        Cancel a pending verification.
        
        Args:
            session: Database session
            verification_id: Verification ID
            
        Returns:
            Updated verification
            
        Raises:
            NotFoundException: If verification not found
            ValidationException: If verification is not pending
        """
        # Get verification
        verification = await self.get_verification(session, verification_id)
        
        # Check if pending
        if verification.status != VerificationStatus.PENDING:
            raise ValidationException(f"Verification is not pending, current status: {verification.status.value}")
        
        # Update status
        verification.status = VerificationStatus.FAILED
        
        return verification
    
    async def cleanup_expired_verifications(
        self,
        session: AsyncSession
    ) -> int:
        """
        Clean up expired verification tokens.
        
        Args:
            session: Database session
            
        Returns:
            Number of expired tokens updated
        """
        now = datetime.utcnow()
        
        # Update expired verifications
        result = await session.execute(
            update(EmailVerification)
            .where(
                EmailVerification.status == VerificationStatus.PENDING,
                EmailVerification.expires_at < now
            )
            .values(status=VerificationStatus.EXPIRED)
            .returning(EmailVerification.id)
        )
        
        expired_ids = result.scalars().all()
        return len(expired_ids)
