"""
API endpoints for the Network Management Module.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.auth.dependencies import get_current_user, require_permissions
from core.models import User
from modules.network.models import (
    Device, DeviceType, DeviceStatus, DeviceGroup,
    ConfigurationTemplate, DeviceConfiguration,
    IPPool, IPPoolType, IPAddress, IPAddressStatus,
    FirmwareVersion, FirmwareUpdateTask, FirmwareUpdateStatus
)
from modules.network.services import DeviceService
from modules.network.ip_pool_service import IPPoolService
from modules.network.configuration_service import ConfigurationService
from modules.network.firmware_service import FirmwareService
from modules.network.topology_service import TopologyService
from modules.network.schemas import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse,
    DeviceGroupCreate, DeviceGroupUpdate, DeviceGroupResponse,
    IPPoolCreate, IPPoolUpdate, IPPoolResponse, IPPoolListResponse, IPAddressResponse,
    ConfigTemplateCreate, ConfigTemplateUpdate, ConfigTemplateResponse,
    DeviceConfigCreate, DeviceConfigResponse, DeviceConfigListResponse,
    FirmwareVersionResponse, FirmwareUpdateTaskCreate, FirmwareUpdateTaskResponse,
    TopologyResponse, TopologyAnalysisResponse
)
from backend_core.utils.hateoas import add_resource_links, generate_collection_links, add_link
from backend_core.schemas import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["Network Management"])

# Initialize services
device_service = DeviceService()
ip_pool_service = IPPoolService()
config_service = ConfigurationService()
firmware_service = FirmwareService(firmware_storage_path="/data/firmware")
topology_service = TopologyService()


# Device endpoints
@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def create_device(
    device: DeviceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new network device."""
    try:
        new_device = await device_service.create_device(session, device)
        
        # Convert to response model
        response = DeviceResponse.from_orm(new_device)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/devices",
            resource_id=new_device.id,
            related_resources=["configurations", "status"]
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="ping",
            href=f"/api/v1/network/devices/{new_device.id}/ping",
            method="POST",
            title="Ping device"
        )
        
        add_link(
            response=response,
            rel="reboot",
            href=f"/api/v1/network/devices/{new_device.id}/reboot",
            method="POST",
            title="Reboot device"
        )
        
        if new_device.group_id:
            add_link(
                response=response,
                rel="group",
                href=f"/api/v1/network/device-groups/{new_device.group_id}",
                method="GET",
                title="View device group"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error creating device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create device: {str(e)}"
        )

@router.get(
    "/devices",
    response_model=DeviceListResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_type: Optional[DeviceType] = None,
    status: Optional[DeviceStatus] = None,
    group_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a list of network devices."""
    try:
        devices, total = await device_service.get_devices(
            session, skip, limit, device_type, status, group_id
        )
        
        # Convert to response models
        device_responses = [DeviceResponse.from_orm(device) for device in devices]
        
        # Create paginated response
        response = PaginatedResponse(
            items=device_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination
        page = skip // limit + 1 if limit > 0 else 1
        
        # Add collection links
        collection_links = generate_collection_links(
            resource_path="/api/v1/network/devices",
            page=page,
            limit=limit,
            total=total
        )
        
        for rel, link in collection_links.items():
            response.links[rel] = link
        
        # Add links to each device
        for device_response in device_responses:
            add_resource_links(
                response=device_response,
                resource_path="/api/v1/network/devices",
                resource_id=device_response.id,
                related_resources=["configurations", "status"]
            )
            
            # Add specific action links
            add_link(
                response=device_response,
                rel="ping",
                href=f"/api/v1/network/devices/{device_response.id}/ping",
                method="POST",
                title="Ping device"
            )
            
            add_link(
                response=device_response,
                rel="reboot",
                href=f"/api/v1/network/devices/{device_response.id}/reboot",
                method="POST",
                title="Reboot device"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error retrieving devices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve devices: {str(e)}"
        )

@router.get(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_device(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a network device by ID."""
    try:
        device = await device_service.get_device(session, device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
        
        # Convert to response model
        response = DeviceResponse.from_orm(device)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/devices",
            resource_id=device.id,
            related_resources=["configurations", "status"]
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="ping",
            href=f"/api/v1/network/devices/{device.id}/ping",
            method="POST",
            title="Ping device"
        )
        
        add_link(
            response=response,
            rel="reboot",
            href=f"/api/v1/network/devices/{device.id}/reboot",
            method="POST",
            title="Reboot device"
        )
        
        add_link(
            response=response,
            rel="backup_config",
            href=f"/api/v1/network/devices/{device.id}/backup-config",
            method="POST",
            title="Backup device configuration"
        )
        
        add_link(
            response=response,
            rel="neighbors",
            href=f"/api/v1/network/devices/{device.id}/neighbors",
            method="GET",
            title="Get device neighbors"
        )
        
        if device.group_id:
            add_link(
                response=response,
                rel="group",
                href=f"/api/v1/network/device-groups/{device.group_id}",
                method="GET",
                title="View device group"
            )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve device: {str(e)}"
        )

@router.put(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def update_device(
    device_id: int = Path(..., ge=1),
    device: DeviceUpdate = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a network device."""
    try:
        updated_device = await device_service.update_device(
            session, device_id, **device.dict(exclude_unset=True)
        )
        
        # Convert to response model
        response = DeviceResponse.from_orm(updated_device)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/devices",
            resource_id=updated_device.id,
            related_resources=["configurations", "status"]
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="ping",
            href=f"/api/v1/network/devices/{updated_device.id}/ping",
            method="POST",
            title="Ping device"
        )
        
        add_link(
            response=response,
            rel="reboot",
            href=f"/api/v1/network/devices/{updated_device.id}/reboot",
            method="POST",
            title="Reboot device"
        )
        
        if updated_device.group_id:
            add_link(
                response=response,
                rel="group",
                href=f"/api/v1/network/device-groups/{updated_device.group_id}",
                method="GET",
                title="View device group"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error updating device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update device: {str(e)}"
        )

@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def delete_device(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a network device."""
    try:
        await device_service.delete_device(session, device_id)
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete device: {str(e)}"
        )

@router.get(
    "/devices/{device_id}/status",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_device_status(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get the current status of a network device including connectivity test."""
    try:
        status = await device_service.get_device_status(session, device_id)
        return status
    except Exception as e:
        logger.error(f"Error retrieving device status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve device status: {str(e)}"
        )

# IP Pool endpoints
@router.post(
    "/ip-pools",
    response_model=IPPoolResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def create_ip_pool(
    pool: IPPoolCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new IP address pool."""
    try:
        new_pool = await ip_pool_service.create_pool(session, pool)
        
        # Convert to response model
        response = IPPoolResponse.from_orm(new_pool)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/ip-pools",
            resource_id=new_pool.id,
            related_resources=["addresses", "usage"]
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="allocate",
            href=f"/api/v1/network/ip-pools/{new_pool.id}/allocate",
            method="POST",
            title="Allocate IP address from pool"
        )
        
        add_link(
            response=response,
            rel="scan",
            href=f"/api/v1/network/ip-pools/{new_pool.id}/scan",
            method="POST",
            title="Scan IP pool for active devices"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error creating IP pool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create IP pool: {str(e)}"
        )

@router.get(
    "/ip-pools",
    response_model=IPPoolListResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_ip_pools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    pool_type: Optional[IPPoolType] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a list of IP pools."""
    try:
        pools, total = await ip_pool_service.get_pools(
            session, skip, limit, pool_type, is_active
        )
        
        # Convert to response models
        pool_responses = [IPPoolResponse.from_orm(pool) for pool in pools]
        
        # Create paginated response
        response = PaginatedResponse(
            items=pool_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination
        page = skip // limit + 1 if limit > 0 else 1
        
        # Add collection links
        collection_links = generate_collection_links(
            resource_path="/api/v1/network/ip-pools",
            page=page,
            limit=limit,
            total=total
        )
        
        for rel, link in collection_links.items():
            response.links[rel] = link
        
        # Add links to each pool
        for pool_response in pool_responses:
            add_resource_links(
                response=pool_response,
                resource_path="/api/v1/network/ip-pools",
                resource_id=pool_response.id,
                related_resources=["addresses", "usage"]
            )
            
            # Add specific action links
            add_link(
                response=pool_response,
                rel="allocate",
                href=f"/api/v1/network/ip-pools/{pool_response.id}/allocate",
                method="POST",
                title="Allocate IP address from pool"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error retrieving IP pools: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve IP pools: {str(e)}"
        )

@router.get(
    "/ip-pools/{pool_id}",
    response_model=IPPoolResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_ip_pool(
    pool_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get an IP pool by ID."""
    try:
        pool = await ip_pool_service.get_pool(session, pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"IP pool with ID {pool_id} not found"
            )
        
        # Convert to response model
        response = IPPoolResponse.from_orm(pool)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/ip-pools",
            resource_id=pool.id,
            related_resources=["addresses", "usage"]
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="allocate",
            href=f"/api/v1/network/ip-pools/{pool.id}/allocate",
            method="POST",
            title="Allocate IP address from pool"
        )
        
        add_link(
            response=response,
            rel="scan",
            href=f"/api/v1/network/ip-pools/{pool.id}/scan",
            method="POST",
            title="Scan IP pool for active devices"
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving IP pool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve IP pool: {str(e)}"
        )

@router.post(
    "/ip-pools/{pool_id}/allocate",
    response_model=IPAddressResponse,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def allocate_ip(
    pool_id: int = Path(..., ge=1),
    assigned_to_id: int = Query(..., ge=1),
    assigned_to_type: str = Query(...),
    specific_ip: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Allocate an IP address from a pool."""
    try:
        ip_address = await ip_pool_service.allocate_ip(
            session, pool_id, assigned_to_id, assigned_to_type, specific_ip
        )
        
        # Convert to response model
        response = IPAddressResponse.from_orm(ip_address)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/ip-addresses",
            resource_id=ip_address.id
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="release",
            href=f"/api/v1/network/ip-addresses/{ip_address.id}/release",
            method="POST",
            title="Release IP address"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error allocating IP address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to allocate IP address: {str(e)}"
        )

@router.post(
    "/ip-addresses/{ip_address}/release",
    response_model=IPAddressResponse,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def release_ip(
    ip_address: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Release an allocated IP address."""
    try:
        released_ip = await ip_pool_service.release_ip(session, ip_address)
        
        # Convert to response model
        response = IPAddressResponse.from_orm(released_ip)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/ip-addresses",
            resource_id=released_ip.id
        )
        
        return response
    except Exception as e:
        logger.error(f"Error releasing IP address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release IP address: {str(e)}"
        )

@router.get(
    "/ip-pools/{pool_id}/usage",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_pool_usage(
    pool_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get usage statistics for an IP address pool."""
    try:
        usage = await ip_pool_service.get_pool_usage(session, pool_id)
        return usage
    except Exception as e:
        logger.error(f"Error retrieving IP pool usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve IP pool usage: {str(e)}"
        )

# Configuration endpoints
@router.post(
    "/templates",
    response_model=ConfigTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def create_template(
    template: ConfigTemplateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new configuration template."""
    try:
        new_template = await config_service.create_template(session, template)
        
        # Convert to response model
        response = ConfigTemplateResponse.from_orm(new_template)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/templates",
            resource_id=new_template.id
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="generate",
            href=f"/api/v1/network/templates/{new_template.id}/generate",
            method="POST",
            title="Generate configuration from template"
        )
        
        add_link(
            response=response,
            rel="apply",
            href=f"/api/v1/network/templates/{new_template.id}/apply",
            method="POST",
            title="Apply template to device"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error creating configuration template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration template: {str(e)}"
        )

@router.get(
    "/templates",
    response_model=List[ConfigTemplateResponse],
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_type: Optional[DeviceType] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a list of configuration templates."""
    try:
        templates, total = await config_service.get_templates(
            session, skip, limit, device_type, is_active
        )
        
        # Convert to response models
        template_responses = [ConfigTemplateResponse.from_orm(template) for template in templates]
        
        # Create paginated response
        response = PaginatedResponse(
            items=template_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination
        page = skip // limit + 1 if limit > 0 else 1
        
        # Add collection links
        collection_links = generate_collection_links(
            resource_path="/api/v1/network/templates",
            page=page,
            limit=limit,
            total=total
        )
        
        for rel, link in collection_links.items():
            response.links[rel] = link
        
        # Add links to each template
        for template_response in template_responses:
            add_resource_links(
                response=template_response,
                resource_path="/api/v1/network/templates",
                resource_id=template_response.id
            )
            
            # Add specific action links
            add_link(
                response=template_response,
                rel="generate",
                href=f"/api/v1/network/templates/{template_response.id}/generate",
                method="POST",
                title="Generate configuration from template"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error retrieving configuration templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration templates: {str(e)}"
        )

@router.post(
    "/templates/{template_id}/generate",
    response_model=str,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def generate_configuration(
    template_id: int = Path(..., ge=1),
    variables: Dict[str, Any] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate a configuration from a template."""
    try:
        config = await config_service.generate_configuration(session, template_id, variables)
        return config
    except Exception as e:
        logger.error(f"Error generating configuration from template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate configuration: {str(e)}"
        )

@router.post(
    "/devices/{device_id}/configurations",
    response_model=DeviceConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def create_device_configuration(
    device_id: int = Path(..., ge=1),
    config: DeviceConfigCreate = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new configuration for a device."""
    try:
        config_obj = await config_service.create_device_configuration(
            session, device_id, config
        )
        
        # Convert to response model
        response = DeviceConfigResponse.from_orm(config_obj)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/device-configurations",
            resource_id=config_obj.id
        )
        
        # Add specific action links
        add_link(
            response=response,
            rel="apply",
            href=f"/api/v1/network/device-configurations/{config_obj.id}/apply",
            method="POST",
            title="Apply configuration to device"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error creating device configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create device configuration: {str(e)}"
        )

@router.post(
    "/device-configurations/{config_id}/apply",
    response_model=DeviceConfigResponse,
    dependencies=[Depends(require_permissions(["network:write"]))]
)
async def apply_configuration(
    config_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Apply a configuration to a device."""
    try:
        config_obj = await config_service.apply_configuration(session, config_id)
        
        # Convert to response model
        response = DeviceConfigResponse.from_orm(config_obj)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/network/device-configurations",
            resource_id=config_obj.id
        )
        
        return response
    except Exception as e:
        logger.error(f"Error applying configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply configuration: {str(e)}"
        )

@router.get(
    "/devices/{device_id}/configurations",
    response_model=DeviceConfigListResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_device_configurations(
    device_id: int = Path(..., ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a list of configurations for a device."""
    try:
        configs, total = await config_service.get_device_configurations(
            session, device_id, skip, limit
        )
        
        # Convert to response models
        config_responses = [DeviceConfigResponse.from_orm(config) for config in configs]
        
        # Create paginated response
        response = PaginatedResponse(
            items=config_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination
        page = skip // limit + 1 if limit > 0 else 1
        
        # Add collection links
        collection_links = generate_collection_links(
            resource_path="/api/v1/network/device-configurations",
            page=page,
            limit=limit,
            total=total
        )
        
        for rel, link in collection_links.items():
            response.links[rel] = link
        
        # Add links to each configuration
        for config_response in config_responses:
            add_resource_links(
                response=config_response,
                resource_path="/api/v1/network/device-configurations",
                resource_id=config_response.id
            )
            
            # Add specific action links
            add_link(
                response=config_response,
                rel="apply",
                href=f"/api/v1/network/device-configurations/{config_response.id}/apply",
                method="POST",
                title="Apply configuration to device"
            )
        
        return response
    except Exception as e:
        logger.error(f"Error retrieving device configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve device configurations: {str(e)}"
        )

# Topology endpoints
@router.post(
    "/topology/discover",
    response_model=TopologyResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def discover_topology(
    root_device_id: Optional[int] = Query(None),
    max_depth: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Discover network topology."""
    try:
        topology = await topology_service.discover_topology(session, root_device_id, max_depth)
        
        # Convert to response model
        response = TopologyResponse.from_orm(topology)
        
        # Add HATEOAS links
        add_link(
            response=response,
            rel="self",
            href=f"/api/v1/network/topology/discover?root_device_id={root_device_id or ''}&max_depth={max_depth}",
            method="POST",
            title="Rediscover topology"
        )
        
        add_link(
            response=response,
            rel="export",
            href=f"/api/v1/network/topology/export?format=json&root_device_id={root_device_id or ''}&max_depth={max_depth}",
            method="GET",
            title="Export topology as JSON"
        )
        
        add_link(
            response=response,
            rel="analyze",
            href="/api/v1/network/topology/analyze",
            method="POST",
            title="Analyze topology"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error discovering topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover topology: {str(e)}"
        )

@router.get(
    "/topology/export",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def export_topology(
    format: str = Query("json", regex="^(json|graphml|gexf)$"),
    root_device_id: Optional[int] = Query(None),
    max_depth: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Export network topology."""
    try:
        export_data = await topology_service.export_topology(session, format, root_device_id, max_depth)
        return export_data
    except Exception as e:
        logger.error(f"Error exporting topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export topology: {str(e)}"
        )

@router.get(
    "/topology/analyze",
    response_model=TopologyAnalysisResponse,
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def analyze_topology(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Analyze network topology."""
    try:
        analysis = await topology_service.analyze_topology(session)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze topology: {str(e)}"
        )

@router.get(
    "/devices/{device_id}/neighbors",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permissions(["network:read"]))]
)
async def get_device_neighbors(
    device_id: int = Path(..., ge=1),
    max_depth: int = Query(1, ge=1, le=3),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get the neighbors of a device."""
    try:
        neighbors = await topology_service.get_device_neighbors(session, device_id, max_depth)
        return neighbors
    except Exception as e:
        logger.error(f"Error retrieving device neighbors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve device neighbors: {str(e)}"
        )
