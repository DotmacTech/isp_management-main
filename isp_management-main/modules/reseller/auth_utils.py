from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import ValidationError

from backend_core.database import get_db
from backend_core.models import User, Reseller
from backend_core.config import settings

# OAuth2 scheme for reseller token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/reseller/auth/login",
    auto_error=False
)

# JWT token settings
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token for a reseller
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "token_type": "access"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT refresh token for a reseller
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "token_type": "refresh"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str) -> Dict[str, Any]:
    """
    Verify a JWT token and return the payload
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if token is of the expected type
        if payload.get("token_type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type} token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_reseller(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Reseller:
    """
    Get the current reseller from the JWT token
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Verify the token
    payload = verify_token(token, "access")
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the reseller from the database
    reseller = db.query(Reseller).join(User).filter(User.id == int(user_id)).first()
    
    if not reseller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseller not found"
        )
    
    # Check if the reseller is active
    if reseller.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reseller account is {reseller.status}"
        )
    
    return reseller

async def get_optional_reseller(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[Reseller]:
    """
    Get the current reseller from the JWT token, or None if not authenticated
    """
    if not token:
        return None
        
    try:
        # Verify the token
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        # Get the reseller from the database
        reseller = db.query(Reseller).join(User).filter(User.id == int(user_id)).first()
        
        if not reseller or reseller.status != "active":
            return None
        
        return reseller
    except HTTPException:
        return None
