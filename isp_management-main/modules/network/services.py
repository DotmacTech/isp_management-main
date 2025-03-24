"""
Services for the Network Management Module.
"""

import ipaddress
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException, ValidationError, ConflictError
from core.services import BaseService
from modules.network.models import (
    Device, DeviceType, DeviceStatus, DeviceGroup, 
    ConfigurationTemplate, DeviceConfiguration,
    IPPool, IPPoolType, IPAddress, IPAddressStatus,
    FirmwareVersion, FirmwareUpdateTask, FirmwareUpdateStatus
)
from modules.network.utils import (
    connect_to_device, 
    parse_configuration, 
    apply_configuration,
    validate_ip_network,
    generate_configuration_from_template
)

logger = logging.getLogger(__name__)


class DeviceService(BaseService):
    """Service for managing network devices."""
    
    async def create_device(
        self, 
        session: AsyncSession,
        name: str,
        hostname: str,
        ip_address: str,
        device_type: DeviceType,
        **kwargs
    ) -> Device:
        """
        Create a new network device.
        
        Args:
            session: Database session
            name: Device name
            hostname: Device hostname or IP for management
            ip_address: Management IP address
            device_type: Type of device
            **kwargs: Additional device properties
            
        Returns:
            The created device
            
        Raises:
            ValidationError: If the device data is invalid
            ConflictError: If a device with the same hostname already exists
        """
        # Check if device with the same hostname already exists
        existing = await session.execute(
            select(Device).where(Device.hostname == hostname)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Device with hostname {hostname} already exists")
        
        # Validate IP address
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValidationError(f"Invalid IP address: {ip_address}")
        
        # Create new device
        device = Device(
            name=name,
            hostname=hostname,
            ip_address=ip_address,
            device_type=device_type,
            status=DeviceStatus.PROVISIONING,
            **kwargs
        )
        
        session.add(device)
        await session.flush()
        
        logger.info(f"Created new device: {device.name} ({device.id})")
        return device
    
    async def get_device(self, session: AsyncSession, device_id: int) -> Device:
        """
        Get a device by ID.
        
        Args:
            session: Database session
            device_id: Device ID
            
        Returns:
            The device
            
        Raises:
            NotFoundException: If the device is not found
        """
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        return device
    
    async def get_devices(
        self, 
        session: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        device_type: Optional[DeviceType] = None,
        status: Optional[DeviceStatus] = None,
        group_id: Optional[int] = None
    ) -> List[Device]:
        """
        Get a list of devices with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            device_type: Filter by device type
            status: Filter by device status
            group_id: Filter by device group ID
            
        Returns:
            List of devices
        """
        query = select(Device)
        
        # Apply filters
        if device_type:
            query = query.where(Device.device_type == device_type)
        if status:
            query = query.where(Device.status == status)
        if group_id:
            query = query.where(Device.group_id == group_id)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update_device(
        self, 
        session: AsyncSession, 
        device_id: int, 
        **kwargs
    ) -> Device:
        """
        Update a device.
        
        Args:
            session: Database session
            device_id: Device ID
            **kwargs: Device properties to update
            
        Returns:
            The updated device
            
        Raises:
            NotFoundException: If the device is not found
            ValidationError: If the update data is invalid
        """
        device = await self.get_device(session, device_id)
        
        # Validate IP address if provided
        if "ip_address" in kwargs:
            try:
                ipaddress.ip_address(kwargs["ip_address"])
            except ValueError:
                raise ValidationError(f"Invalid IP address: {kwargs['ip_address']}")
        
        # Update device properties
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        await session.flush()
        logger.info(f"Updated device: {device.name} ({device.id})")
        return device
    
    async def delete_device(self, session: AsyncSession, device_id: int) -> None:
        """
        Delete a device.
        
        Args:
            session: Database session
            device_id: Device ID
            
        Raises:
            NotFoundException: If the device is not found
        """
        device = await self.get_device(session, device_id)
        await session.delete(device)
        logger.info(f"Deleted device: {device.name} ({device.id})")
    
    async def get_device_status(self, session: AsyncSession, device_id: int) -> Dict[str, Any]:
        """
        Get the current status of a device including connectivity test.
        
        Args:
            session: Database session
            device_id: Device ID
            
        Returns:
            Device status information
            
        Raises:
            NotFoundException: If the device is not found
        """
        device = await self.get_device(session, device_id)
        
        # Perform connectivity test
        is_reachable = await self._check_device_connectivity(device)
        
        return {
            "id": device.id,
            "name": device.name,
            "status": device.status.value,
            "is_reachable": is_reachable,
            "last_checked": datetime.now().isoformat()
        }
    
    async def _check_device_connectivity(self, device: Device) -> bool:
        """
        Check if a device is reachable.
        
        Args:
            device: The device to check
            
        Returns:
            True if the device is reachable, False otherwise
        """
        # This would be implemented with actual device connectivity check
        # For now, we'll just return a placeholder
        return True
