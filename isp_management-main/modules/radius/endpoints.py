from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_active_user, get_current_admin_user
from backend_core.models import User

from .schemas import (
    RadiusProfileCreate, RadiusProfileUpdate, RadiusProfileResponse,
    RadiusAuthRequest, RadiusAuthResponse,
    RadiusAccountingStart, RadiusAccountingUpdate, RadiusAccountingStop, RadiusAccountingResponse,
    RadiusSessionStatistics, RadiusUserSessionsResponse,
    NasDeviceCreate, NasDeviceUpdate, NasDeviceResponse, NasDeviceListResponse,
    NasVendorAttributeCreate, NasVendorAttributeUpdate, NasVendorAttributeResponse,
    RadiusBandwidthPolicyCreate, RadiusBandwidthPolicyUpdate, RadiusBandwidthPolicyResponse,
    RadiusProfileAttributeCreate, RadiusProfileAttributeUpdate, RadiusProfileAttributeResponse,
    RadiusCoARequest, RadiusCoAResponse, RadiusCoALogResponse
)
from .services import RadiusService

router = APIRouter(
    prefix="/radius",
    tags=["radius"],
    responses={404: {"description": "Not found"}},
)


# RADIUS Profile endpoints
@router.post("/profiles", response_model=RadiusProfileResponse, status_code=status.HTTP_201_CREATED)
def create_radius_profile(
    profile_data: RadiusProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new RADIUS profile for a user."""
    radius_service = RadiusService(db)
    return radius_service.create_radius_profile(profile_data)


@router.get("/profiles", response_model=List[RadiusProfileResponse])
def list_radius_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all RADIUS profiles."""
    radius_service = RadiusService(db)
    return radius_service.list_radius_profiles(skip, limit)


@router.get("/profiles/{profile_id}", response_model=RadiusProfileResponse)
def get_radius_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a RADIUS profile by ID."""
    radius_service = RadiusService(db)
    profile = radius_service.get_radius_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="RADIUS profile not found")
    return profile


@router.put("/profiles/{profile_id}", response_model=RadiusProfileResponse)
def update_radius_profile(
    profile_id: int,
    profile_data: RadiusProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a RADIUS profile."""
    radius_service = RadiusService(db)
    return radius_service.update_radius_profile(profile_id, profile_data)


@router.delete("/profiles/{profile_id}", response_model=Dict[str, bool])
def delete_radius_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a RADIUS profile."""
    radius_service = RadiusService(db)
    success = radius_service.delete_radius_profile(profile_id)
    return {"success": success}


# RADIUS Authentication endpoint
@router.post("/auth", response_model=RadiusAuthResponse)
def authenticate_radius_user(
    auth_request: RadiusAuthRequest,
    db: Session = Depends(get_db)
):
    """Authenticate a RADIUS user."""
    radius_service = RadiusService(db)
    return radius_service.authenticate_user(auth_request)


# RADIUS Accounting endpoints
@router.post("/accounting/start", response_model=RadiusAccountingResponse)
def start_accounting_session(
    accounting_data: RadiusAccountingStart,
    db: Session = Depends(get_db)
):
    """Start a RADIUS accounting session."""
    radius_service = RadiusService(db)
    return radius_service.start_accounting_session(accounting_data)


@router.post("/accounting/update", response_model=RadiusAccountingResponse)
def update_accounting_session(
    accounting_data: RadiusAccountingUpdate,
    db: Session = Depends(get_db)
):
    """Update a RADIUS accounting session."""
    radius_service = RadiusService(db)
    return radius_service.update_accounting_session(accounting_data)


@router.post("/accounting/stop", response_model=RadiusAccountingResponse)
def stop_accounting_session(
    accounting_data: RadiusAccountingStop,
    db: Session = Depends(get_db)
):
    """Stop a RADIUS accounting session."""
    radius_service = RadiusService(db)
    return radius_service.stop_accounting_session(accounting_data)


@router.get("/accounting/sessions", response_model=List[RadiusAccountingResponse])
def list_accounting_sessions(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    nas_id: Optional[int] = None,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List RADIUS accounting sessions."""
    radius_service = RadiusService(db)
    return radius_service.list_accounting_sessions(
        user_id=user_id,
        username=username,
        nas_id=nas_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )


@router.get("/accounting/sessions/{session_id}", response_model=RadiusAccountingResponse)
def get_accounting_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a RADIUS accounting session by ID."""
    radius_service = RadiusService(db)
    session = radius_service.get_accounting_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Accounting session not found")
    return session


@router.get("/accounting/statistics", response_model=RadiusSessionStatistics)
def get_session_statistics(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    nas_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get session statistics."""
    radius_service = RadiusService(db)
    return radius_service.get_session_statistics(
        user_id=user_id,
        username=username,
        nas_id=nas_id
    )


@router.get("/accounting/user/{username}/sessions", response_model=RadiusUserSessionsResponse)
def get_user_sessions(
    username: str,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get sessions for a specific user."""
    radius_service = RadiusService(db)
    return radius_service.get_user_sessions(username, active_only)


# NAS Device Management endpoints
@router.post("/nas", response_model=NasDeviceResponse, status_code=status.HTTP_201_CREATED)
def create_nas_device(
    device_data: NasDeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new NAS device."""
    radius_service = RadiusService(db)
    return radius_service.create_nas_device(device_data)


@router.get("/nas", response_model=NasDeviceListResponse)
def list_nas_devices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all NAS devices."""
    radius_service = RadiusService(db)
    devices = radius_service.list_nas_devices(skip, limit)
    return {
        "total": len(devices),
        "items": devices
    }


@router.get("/nas/{device_id}", response_model=NasDeviceResponse)
def get_nas_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a NAS device by ID."""
    radius_service = RadiusService(db)
    device = radius_service.get_nas_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="NAS device not found")
    return device


@router.put("/nas/{device_id}", response_model=NasDeviceResponse)
def update_nas_device(
    device_id: int,
    device_data: NasDeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a NAS device."""
    radius_service = RadiusService(db)
    return radius_service.update_nas_device(device_id, device_data)


@router.delete("/nas/{device_id}", response_model=Dict[str, bool])
def delete_nas_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a NAS device."""
    radius_service = RadiusService(db)
    success = radius_service.delete_nas_device(device_id)
    return {"success": success}


# NAS Vendor Attribute endpoints
@router.post("/nas/vendor-attributes", response_model=NasVendorAttributeResponse, status_code=status.HTTP_201_CREATED)
def create_nas_vendor_attribute(
    attr_data: NasVendorAttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new vendor-specific attribute for NAS devices."""
    radius_service = RadiusService(db)
    return radius_service.create_nas_vendor_attribute(attr_data)


@router.get("/nas/vendor-attributes", response_model=List[NasVendorAttributeResponse])
def list_nas_vendor_attributes(
    nas_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List vendor-specific attributes for NAS devices."""
    radius_service = RadiusService(db)
    return radius_service.list_nas_vendor_attributes(
        nas_id=nas_id,
        vendor_id=vendor_id,
        skip=skip,
        limit=limit
    )


@router.get("/nas/vendor-attributes/{attr_id}", response_model=NasVendorAttributeResponse)
def get_nas_vendor_attribute(
    attr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a vendor-specific attribute by ID."""
    radius_service = RadiusService(db)
    attr = radius_service.get_nas_vendor_attribute(attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="Vendor attribute not found")
    return attr


@router.put("/nas/vendor-attributes/{attr_id}", response_model=NasVendorAttributeResponse)
def update_nas_vendor_attribute(
    attr_id: int,
    attr_data: NasVendorAttributeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a vendor-specific attribute."""
    radius_service = RadiusService(db)
    return radius_service.update_nas_vendor_attribute(attr_id, attr_data)


@router.delete("/nas/vendor-attributes/{attr_id}", response_model=Dict[str, bool])
def delete_nas_vendor_attribute(
    attr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a vendor-specific attribute."""
    radius_service = RadiusService(db)
    success = radius_service.delete_nas_vendor_attribute(attr_id)
    return {"success": success}


# Bandwidth Policy endpoints
@router.post("/bandwidth-policies", response_model=RadiusBandwidthPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_bandwidth_policy(
    policy_data: RadiusBandwidthPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new bandwidth policy."""
    radius_service = RadiusService(db)
    return radius_service.create_bandwidth_policy(policy_data)


@router.get("/bandwidth-policies", response_model=List[RadiusBandwidthPolicyResponse])
def list_bandwidth_policies(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all bandwidth policies."""
    radius_service = RadiusService(db)
    return radius_service.list_bandwidth_policies(skip, limit, active_only)


@router.get("/bandwidth-policies/{policy_id}", response_model=RadiusBandwidthPolicyResponse)
def get_bandwidth_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a bandwidth policy by ID."""
    radius_service = RadiusService(db)
    policy = radius_service.get_bandwidth_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Bandwidth policy not found")
    return policy


@router.put("/bandwidth-policies/{policy_id}", response_model=RadiusBandwidthPolicyResponse)
def update_bandwidth_policy(
    policy_id: int,
    policy_data: RadiusBandwidthPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a bandwidth policy."""
    radius_service = RadiusService(db)
    return radius_service.update_bandwidth_policy(policy_id, policy_data)


@router.delete("/bandwidth-policies/{policy_id}", response_model=Dict[str, bool])
def delete_bandwidth_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a bandwidth policy."""
    radius_service = RadiusService(db)
    success = radius_service.delete_bandwidth_policy(policy_id)
    return {"success": success}


# Profile Attributes endpoints
@router.post("/profile-attributes", response_model=RadiusProfileAttributeResponse, status_code=status.HTTP_201_CREATED)
def create_profile_attribute(
    attr_data: RadiusProfileAttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new attribute for a RADIUS profile."""
    radius_service = RadiusService(db)
    return radius_service.create_profile_attribute(attr_data)


@router.get("/profile-attributes", response_model=List[RadiusProfileAttributeResponse])
def get_profile_attributes(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all attributes for a RADIUS profile."""
    radius_service = RadiusService(db)
    return radius_service.get_profile_attributes(profile_id)


@router.put("/profile-attributes/{attr_id}", response_model=RadiusProfileAttributeResponse)
def update_profile_attribute(
    attr_id: int,
    attr_data: RadiusProfileAttributeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a profile attribute."""
    radius_service = RadiusService(db)
    return radius_service.update_profile_attribute(attr_id, attr_data)


@router.delete("/profile-attributes/{attr_id}", response_model=Dict[str, bool])
def delete_profile_attribute(
    attr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a profile attribute."""
    radius_service = RadiusService(db)
    success = radius_service.delete_profile_attribute(attr_id)
    return {"success": success}


# CoA (Change of Authorization) endpoints
@router.post("/coa", response_model=RadiusCoAResponse)
def send_coa_request(
    coa_request: RadiusCoARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Send a CoA request to a NAS device."""
    radius_service = RadiusService(db)
    return radius_service.send_coa_request(coa_request)


@router.post("/disconnect-session/{session_id}", response_model=Dict[str, bool])
def disconnect_user_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Disconnect a specific user session."""
    radius_service = RadiusService(db)
    success = radius_service.disconnect_user_session(session_id)
    return {"success": success}


@router.post("/disconnect-user/{username}", response_model=Dict[str, Any])
def disconnect_user(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Disconnect all active sessions for a user."""
    radius_service = RadiusService(db)
    return radius_service.disconnect_user(username)


@router.get("/coa-logs", response_model=List[RadiusCoALogResponse])
def get_coa_logs(
    profile_id: Optional[int] = None,
    nas_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get CoA logs, optionally filtered by profile or NAS."""
    radius_service = RadiusService(db)
    return radius_service.get_coa_logs(
        profile_id=profile_id,
        nas_id=nas_id,
        skip=skip,
        limit=limit
    )
