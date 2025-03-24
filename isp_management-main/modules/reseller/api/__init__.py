"""
API router initialization for reseller module.

This module provides the FastAPI router for reseller endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router
from .schemas import (
    ResellerBase, ResellerCreate, ResellerResponse,
    ResellerCommissionRuleBase, ResellerCommissionRuleCreate, ResellerCommissionRuleResponse,
    ResellerSearch, CommissionType, ResellerTier
)

router = APIRouter()
router.include_router(endpoints_router)

__all__ = [
    "router",
    "ResellerBase", "ResellerCreate", "ResellerResponse",
    "ResellerCommissionRuleBase", "ResellerCommissionRuleCreate", "ResellerCommissionRuleResponse",
    "ResellerSearch", "CommissionType", "ResellerTier"
]
