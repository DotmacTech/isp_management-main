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
    summary="Create a new network device",
    description="Create a new network device with the specified parameters."
)
async def create_device(
    device: DeviceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Create a new network device."""
    try:
        device_obj = await device_service.create_device(
            session=session,
            name=device.name,
            hostname=device.hostname,
            ip_address=device.ip_address,
            device_type=device.device_type,
            mac_address=device.mac_address,
            serial_number=device.serial_number,
            model=device.model,
            manufacturer=device.manufacturer,
            location=device.location,
            description=device.description,
            group_id=device.group_id,
            username=device.username,
            password=device.password,
            enable_password=device.enable_password,
            snmp_community=device.snmp_community,
            properties=device.properties
        )
        await session.commit()
        return DeviceResponse.from_orm(device_obj)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create device: {str(e)}"
        )


@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="Get a list of network devices",
    description="Get a list of network devices with optional filtering."
)
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_type: Optional[DeviceType] = None,
    status: Optional[DeviceStatus] = None,
    group_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get a list of network devices."""
    try:
        devices = await device_service.get_devices(
            session=session,
            skip=skip,
            limit=limit,
            device_type=device_type,
            status=status,
            group_id=group_id
        )
        return DeviceListResponse(
            items=devices,
            total=len(devices),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Failed to get devices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get devices: {str(e)}"
        )


@router.get(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    summary="Get a network device by ID",
    description="Get detailed information about a specific network device."
)
async def get_device(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get a network device by ID."""
    try:
        device = await device_service.get_device(session, device_id)
        return DeviceResponse.from_orm(device)
    except Exception as e:
        logger.error(f"Failed to get device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {str(e)}"
        )


@router.put(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    summary="Update a network device",
    description="Update an existing network device with the specified parameters."
)
async def update_device(
    device_id: int = Path(..., ge=1),
    device: DeviceUpdate = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Update a network device."""
    try:
        updated_device = await device_service.update_device(
            session=session,
            device_id=device_id,
            **device.dict(exclude_unset=True)
        )
        await session.commit()
        return DeviceResponse.from_orm(updated_device)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to update device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update device: {str(e)}"
        )


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a network device",
    description="Delete a network device by ID."
)
async def delete_device(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Delete a network device."""
    try:
        await device_service.delete_device(session, device_id)
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {str(e)}"
        )


@router.get(
    "/devices/{device_id}/status",
    response_model=Dict[str, Any],
    summary="Get device status",
    description="Get the current status of a network device including connectivity test."
)
async def get_device_status(
    device_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get the current status of a device."""
    try:
        status = await device_service.get_device_status(session, device_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get device status {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {str(e)}"
        )


# IP Pool endpoints
@router.post(
    "/ip-pools",
    response_model=IPPoolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new IP pool",
    description="Create a new IP address pool with the specified parameters."
)
async def create_ip_pool(
    pool: IPPoolCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Create a new IP address pool."""
    try:
        pool_obj = await ip_pool_service.create_pool(
            session=session,
            name=pool.name,
            network=pool.network,
            pool_type=pool.pool_type,
            gateway=pool.gateway,
            dns_servers=pool.dns_servers,
            description=pool.description
        )
        await session.commit()
        return IPPoolResponse.from_orm(pool_obj)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create IP pool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create IP pool: {str(e)}"
        )


@router.get(
    "/ip-pools",
    response_model=IPPoolListResponse,
    summary="Get a list of IP pools",
    description="Get a list of IP address pools with optional filtering."
)
async def get_ip_pools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    pool_type: Optional[IPPoolType] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get a list of IP pools."""
    try:
        pools = await ip_pool_service.get_pools(
            session=session,
            skip=skip,
            limit=limit,
            pool_type=pool_type,
            is_active=is_active
        )
        return IPPoolListResponse(
            items=pools,
            total=len(pools),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Failed to get IP pools: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get IP pools: {str(e)}"
        )


@router.get(
    "/ip-pools/{pool_id}",
    response_model=IPPoolResponse,
    summary="Get an IP pool by ID",
    description="Get detailed information about a specific IP address pool."
)
async def get_ip_pool(
    pool_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get an IP pool by ID."""
    try:
        pool = await ip_pool_service.get_pool(session, pool_id)
        return IPPoolResponse.from_orm(pool)
    except Exception as e:
        logger.error(f"Failed to get IP pool {pool_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP pool not found: {str(e)}"
        )


@router.post(
    "/ip-pools/{pool_id}/allocate",
    response_model=IPAddressResponse,
    summary="Allocate an IP address from a pool",
    description="Allocate an IP address from a pool to an entity."
)
async def allocate_ip(
    pool_id: int = Path(..., ge=1),
    assigned_to_id: int = Query(..., ge=1),
    assigned_to_type: str = Query(...),
    specific_ip: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Allocate an IP address from a pool."""
    try:
        ip_address = await ip_pool_service.allocate_ip(
            session=session,
            pool_id=pool_id,
            assigned_to_id=assigned_to_id,
            assigned_to_type=assigned_to_type,
            specific_ip=specific_ip
        )
        await session.commit()
        return IPAddressResponse.from_orm(ip_address)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to allocate IP from pool {pool_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to allocate IP: {str(e)}"
        )


@router.post(
    "/ip-pools/release/{ip_address}",
    response_model=IPAddressResponse,
    summary="Release an IP address",
    description="Release an allocated IP address back to its pool."
)
async def release_ip(
    ip_address: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Release an allocated IP address."""
    try:
        released_ip = await ip_pool_service.release_ip(
            session=session,
            ip_address=ip_address
        )
        await session.commit()
        return IPAddressResponse.from_orm(released_ip)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to release IP {ip_address}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to release IP: {str(e)}"
        )


@router.get(
    "/ip-pools/{pool_id}/usage",
    response_model=Dict[str, Any],
    summary="Get IP pool usage statistics",
    description="Get usage statistics for an IP address pool."
)
async def get_pool_usage(
    pool_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get usage statistics for an IP pool."""
    try:
        usage = await ip_pool_service.get_pool_usage(session, pool_id)
        return usage
    except Exception as e:
        logger.error(f"Failed to get IP pool usage {pool_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP pool not found: {str(e)}"
        )


# Configuration endpoints
@router.post(
    "/templates",
    response_model=ConfigTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new configuration template",
    description="Create a new configuration template for network devices."
)
async def create_template(
    template: ConfigTemplateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Create a new configuration template."""
    try:
        template_obj = await config_service.create_template(
            session=session,
            name=template.name,
            device_type=template.device_type,
            template_content=template.template_content,
            version=template.version,
            variables=template.variables,
            description=template.description
        )
        await session.commit()
        return ConfigTemplateResponse.from_orm(template_obj)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get(
    "/templates",
    response_model=List[ConfigTemplateResponse],
    summary="Get a list of configuration templates",
    description="Get a list of configuration templates with optional filtering."
)
async def get_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_type: Optional[DeviceType] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get a list of configuration templates."""
    try:
        templates = await config_service.get_templates(
            session=session,
            skip=skip,
            limit=limit,
            device_type=device_type,
            is_active=is_active
        )
        return templates
    except Exception as e:
        logger.error(f"Failed to get templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get templates: {str(e)}"
        )


@router.post(
    "/templates/{template_id}/generate",
    response_model=str,
    summary="Generate configuration from template",
    description="Generate a configuration from a template using provided variables."
)
async def generate_configuration(
    template_id: int = Path(..., ge=1),
    variables: Dict[str, Any] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Generate a configuration from a template."""
    try:
        config = await config_service.generate_configuration(
            session=session,
            template_id=template_id,
            variables=variables
        )
        return config
    except Exception as e:
        logger.error(f"Failed to generate configuration from template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate configuration: {str(e)}"
        )


@router.post(
    "/devices/{device_id}/configurations",
    response_model=DeviceConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a device configuration",
    description="Create a new configuration version for a device."
)
async def create_device_configuration(
    device_id: int = Path(..., ge=1),
    config: DeviceConfigCreate = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Create a new configuration for a device."""
    try:
        config_obj = await config_service.create_device_configuration(
            session=session,
            device_id=device_id,
            config_content=config.config_content,
            version=config.version,
            applied_by=current_user.username,
            template_id=config.template_id,
            template_variables=config.template_variables
        )
        await session.commit()
        return DeviceConfigResponse.from_orm(config_obj)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create device configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create device configuration: {str(e)}"
        )


@router.post(
    "/configurations/{config_id}/apply",
    response_model=DeviceConfigResponse,
    summary="Apply a configuration to a device",
    description="Apply a configuration to a device and mark it as active."
)
async def apply_configuration(
    config_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:write"]))
):
    """Apply a configuration to a device."""
    try:
        config_obj = await config_service.apply_configuration(
            session=session,
            config_id=config_id,
            applied_by=current_user.username
        )
        await session.commit()
        return DeviceConfigResponse.from_orm(config_obj)
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to apply configuration {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to apply configuration: {str(e)}"
        )


@router.get(
    "/devices/{device_id}/configurations",
    response_model=DeviceConfigListResponse,
    summary="Get device configurations",
    description="Get a list of configurations for a device."
)
async def get_device_configurations(
    device_id: int = Path(..., ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get a list of configurations for a device."""
    try:
        configs = await config_service.get_device_configurations(
            session=session,
            device_id=device_id,
            skip=skip,
            limit=limit
        )
        return DeviceConfigListResponse(
            items=configs,
            total=len(configs),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Failed to get device configurations {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {str(e)}"
        )


# Topology endpoints
@router.get(
    "/topology",
    response_model=TopologyResponse,
    summary="Discover network topology",
    description="Discover network topology starting from a root device."
)
async def discover_topology(
    root_device_id: Optional[int] = Query(None),
    max_depth: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Discover network topology."""
    try:
        topology = await topology_service.discover_topology(
            session=session,
            root_device_id=root_device_id,
            max_depth=max_depth
        )
        return topology
    except Exception as e:
        logger.error(f"Failed to discover topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover topology: {str(e)}"
        )


@router.get(
    "/topology/export",
    response_model=Dict[str, Any],
    summary="Export network topology",
    description="Export network topology in various formats."
)
async def export_topology(
    format: str = Query("json", regex="^(json|graphml|gexf)$"),
    root_device_id: Optional[int] = Query(None),
    max_depth: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Export network topology."""
    try:
        export_data = await topology_service.export_topology(
            session=session,
            format=format,
            root_device_id=root_device_id,
            max_depth=max_depth
        )
        return export_data
    except Exception as e:
        logger.error(f"Failed to export topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export topology: {str(e)}"
        )


@router.get(
    "/topology/analyze",
    response_model=TopologyAnalysisResponse,
    summary="Analyze network topology",
    description="Analyze network topology for insights."
)
async def analyze_topology(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Analyze network topology."""
    try:
        analysis = await topology_service.analyze_topology(session)
        return analysis
    except Exception as e:
        logger.error(f"Failed to analyze topology: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze topology: {str(e)}"
        )


@router.get(
    "/devices/{device_id}/neighbors",
    response_model=Dict[str, Any],
    summary="Get device neighbors",
    description="Get the neighbors of a device."
)
async def get_device_neighbors(
    device_id: int = Path(..., ge=1),
    max_depth: int = Query(1, ge=1, le=3),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["network:read"]))
):
    """Get the neighbors of a device."""
    try:
        neighbors = await topology_service.get_device_neighbors(
            session=session,
            device_id=device_id,
            max_depth=max_depth
        )
        return neighbors
    except Exception as e:
        logger.error(f"Failed to get device neighbors {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {str(e)}"
        )
