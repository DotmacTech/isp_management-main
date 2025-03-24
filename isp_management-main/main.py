"""
ISP Management Platform - Main Application

This is the main entry point for the ISP Management Platform API.
It configures the FastAPI application, sets up middleware, and includes all API routes.
"""

import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend_core.database import engine, Base, get_db
from backend_core.middleware import setup_middleware
from backend_core.utils.exception_handlers import register_exception_handlers
from backend_core.config import (
    API_VERSION, 
    API_TITLE, 
    API_DESCRIPTION,
    ALLOWED_ORIGINS,
    SUPPORTED_API_VERSIONS
)

# Import all API routers
from modules.auth.endpoints import router as auth_router
from modules.billing.api.endpoints import router as billing_router
from modules.monitoring import router as monitoring_router
# Import other routers as needed

# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom middleware
setup_middleware(app)

# Register exception handlers
register_exception_handlers(app)

# Include API routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(monitoring_router, prefix="/api/v1/monitoring", tags=["Monitoring"])
# Include other routers as needed

# Create separate routers for each API version
v1_router = FastAPI(
    title=f"{API_TITLE} v1",
    description=f"{API_DESCRIPTION} - Version 1.0",
    version="1.0"
)

v2_router = FastAPI(
    title=f"{API_TITLE} v2",
    description=f"{API_DESCRIPTION} - Version 2.0",
    version="2.0"
)

# Include routers in the version-specific applications
# V1 API routes
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
# Include other v1 routers here

# V2 API routes (can be the same as v1 initially)
v2_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v2_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
# Include other v2 routers here

# Mount versioned APIs
app.mount("/api/v1", v1_router)
app.mount("/api/v2", v2_router)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Custom Swagger UI documentation endpoint.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{API_TITLE} - Swagger UI",
        oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """
    Get OpenAPI schema for the API.
    """
    return get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
    )

@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify API is running and database connection is working.
    
    Returns:
        dict: Status of the API and database connection
    """
    try:
        # Verify database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "database": db_status
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    """
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

@app.on_event("startup")
async def startup_event():
    """
    Execute tasks on application startup.
    """
    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute tasks on application shutdown.
    """
    # Add cleanup tasks here
    pass

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
