"""
Schemas for the radius module.

This package contains schemas for the radius module.
"""

# Re-export all schemas from the api.schemas module for compatibility
from ..api.schemas import (
    # RADIUS session schemas
    RadiusSessionStatistics,
    RadiusUserSessionsResponse,
    RadiusAccountingResponse,
    
    # RADIUS authentication schemas
    RadiusAuthRequest,
    RadiusAuthResponse,
    
    # RADIUS accounting schemas
    RadiusAccountingStart,
    RadiusAccountingUpdate,
    RadiusAccountingStop,
    
    # RADIUS profile schemas
    RadiusProfileCreate, 
    RadiusProfileUpdate, 
    RadiusProfileResponse,
    
    # RADIUS CoA schemas
    RadiusCoARequest,
    RadiusCoAResponse,
    RadiusCoALogResponse,
    
    # NAS device schemas
    NasDeviceBase,
    NasDeviceCreate,
    NasDeviceUpdate,
    NasDeviceResponse,
    NasDeviceListResponse,
    
    # NAS vendor attribute schemas
    NasVendorAttributeCreate,
    NasVendorAttributeUpdate,
    NasVendorAttributeResponse,
    
    # RADIUS profile attribute schemas
    RadiusProfileAttributeBase,
    RadiusProfileAttributeCreate,
    RadiusProfileAttributeUpdate,
    RadiusProfileAttributeResponse,
    
    # RADIUS bandwidth policy schemas
    RadiusBandwidthPolicyCreate,
    RadiusBandwidthPolicyUpdate,
    RadiusBandwidthPolicyResponse
)
