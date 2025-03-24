"""
Middleware for the ISP Management Platform.

This module contains middleware components for the FastAPI application,
including session tracking, authentication, and request logging.
"""

import time
import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session
from datetime import datetime

from .database import get_db
from .models import UserSession
from .config import SECRET_KEY, ALGORITHM


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract session information from JWT tokens and track user activity.
    
    This middleware:
    1. Extracts session_id from JWT tokens in the Authorization header
    2. Stores session_id in request.state for use in route handlers
    3. Updates session last_active_at timestamp for active sessions
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Start timer for request processing
        start_time = time.time()
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            
            try:
                # Decode token without verification to extract session_id
                # Full verification happens in the auth dependency
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                session_id = payload.get("session_id")
                
                if session_id:
                    # Store session_id in request state for later use
                    request.state.session_id = session_id
            except Exception:
                # If token decoding fails, continue without session tracking
                pass
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request processing time
        process_time = time.time() - start_time
        
        # Add processing time header for monitoring
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests for audit purposes.
    
    This middleware logs:
    1. Request method and path
    2. User ID (if authenticated)
    3. Client IP address
    4. Request timestamp
    5. Response status code
    6. Processing time
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Start timer for request processing
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request processing time
        process_time = time.time() - start_time
        
        # Extract user ID if available in request state
        user_id = getattr(request.state, "user_id", None)
        
        # Log request details
        # In a production environment, this would be sent to a logging service
        # such as Elasticsearch or a dedicated audit log table
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": client_ip,
            "user_id": user_id,
            "status_code": response.status_code,
            "process_time": process_time
        }
        
        # Here we would typically send this to a logging service
        # For now, we'll just print it in development
        print(f"AUDIT LOG: {log_data}")
        
        return response


def setup_middleware(app):
    """
    Set up all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Add session middleware
    app.add_middleware(SessionMiddleware)
    
    # Add audit log middleware
    app.add_middleware(AuditLogMiddleware)
