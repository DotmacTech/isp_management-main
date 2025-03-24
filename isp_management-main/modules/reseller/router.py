from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.utils.hateoas import generate_links, generate_collection_links
from . import endpoints, auth_endpoints, portal_endpoints

# Create main router for reseller module
router = APIRouter(
    prefix="/api/v1/reseller",
    tags=["reseller"]
)

# Include all sub-routers
router.include_router(endpoints.router)
router.include_router(auth_endpoints.router)
router.include_router(portal_endpoints.router)

# Add root endpoint with HATEOAS links
@router.get("/", response_model=dict)
async def reseller_root(db: Session = Depends(get_db)):
    """
    Root endpoint for reseller module that provides HATEOAS links to available resources
    """
    return {
        "module": "reseller",
        "description": "Reseller management module with self-service portal and commission tracking",
        "version": "1.0.0",
        "_links": {
            "self": {"href": "/api/v1/reseller"},
            "resellers": {"href": "/api/v1/reseller/resellers"},
            "customers": {"href": "/api/v1/reseller/customers"},
            "transactions": {"href": "/api/v1/reseller/transactions"},
            "commission_rules": {"href": "/api/v1/reseller/commission/rules"},
            "auth": {"href": "/api/v1/reseller/auth"},
            "portal": {"href": "/api/v1/reseller/portal"}
        }
    }
