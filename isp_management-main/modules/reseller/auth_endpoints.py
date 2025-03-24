from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.models import User, Reseller
from backend_core.auth_service import verify_password
from .auth_utils import create_access_token, create_refresh_token, verify_token
from .schemas import TokenResponse, RefreshTokenRequest

router = APIRouter(
    prefix="/auth",
    tags=["reseller_auth"]
)

@router.post("/login", response_model=TokenResponse)
async def login_reseller(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate a reseller and return JWT tokens
    """
    # Find the user
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user has a reseller profile
    reseller = db.query(Reseller).filter(Reseller.user_id == user.id).first()
    
    if not reseller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a reseller",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if reseller is active
    if reseller.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reseller account is {reseller.status}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": "reseller", "reseller_id": reseller.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": "reseller", "reseller_id": reseller.id}
    )
    
    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "reseller": {
            "id": reseller.id,
            "company_name": reseller.company_name,
            "tier": reseller.tier,
            "status": reseller.status
        }
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token
    """
    # Verify the refresh token
    payload = verify_token(refresh_request.refresh_token, "refresh")
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the user and reseller
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    reseller = db.query(Reseller).filter(Reseller.user_id == user.id).first()
    
    if not reseller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a reseller"
        )
    
    # Check if reseller is active
    if reseller.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reseller account is {reseller.status}"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": "reseller", "reseller_id": reseller.id}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": "reseller", "reseller_id": reseller.id}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "reseller": {
            "id": reseller.id,
            "company_name": reseller.company_name,
            "tier": reseller.tier,
            "status": reseller.status
        }
    }
