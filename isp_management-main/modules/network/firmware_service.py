"""
Firmware Management Service for the Network Management Module.
"""

import logging
import hashlib
import os
from typing import List, Dict, Any, Optional, Tuple, Union, BinaryIO
from datetime import datetime
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException, ValidationError, ConflictError
from core.services import BaseService
from modules.network.models import (
    Device, DeviceType, FirmwareVersion, FirmwareUpdateTask, FirmwareUpdateStatus
)

logger = logging.getLogger(__name__)


class FirmwareService(BaseService):
    """Service for managing device firmware versions and updates."""
    
    def __init__(self, firmware_storage_path: str):
        """
        Initialize the firmware service.
        
        Args:
            firmware_storage_path: Path to store firmware files
        """
        self.firmware_storage_path = firmware_storage_path
        os.makedirs(firmware_storage_path, exist_ok=True)
    
    async def upload_firmware(
        self,
        session: AsyncSession,
        version: str,
        device_type: DeviceType,
        manufacturer: str,
        model: str,
        firmware_file: BinaryIO,
        release_date: Optional[datetime] = None,
        release_notes: Optional[str] = None,
        is_recommended: bool = False
    ) -> FirmwareVersion:
        """
        Upload a new firmware version.
        
        Args:
            session: Database session
            version: Firmware version
            device_type: Type of device this firmware is for
            manufacturer: Device manufacturer
            model: Device model
            firmware_file: File-like object containing the firmware
            release_date: Release date of the firmware
            release_notes: Release notes for the firmware
            is_recommended: Whether this firmware is recommended
            
        Returns:
            The created firmware version
            
        Raises:
            ValidationError: If the firmware data is invalid
            ConflictError: If the firmware version already exists
        """
        # Check if firmware version already exists
        existing = await session.execute(
            select(FirmwareVersion).where(
                and_(
                    FirmwareVersion.version == version,
                    FirmwareVersion.device_type == device_type,
                    FirmwareVersion.manufacturer == manufacturer,
                    FirmwareVersion.model == model
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                f"Firmware version {version} for {manufacturer} {model} already exists"
            )
        
        # Read and hash the firmware file
        firmware_data = firmware_file.read()
        file_hash = hashlib.sha256(firmware_data).hexdigest()
        file_size = len(firmware_data)
        
        # Generate a unique filename
        filename = f"{manufacturer}_{model}_{version.replace('.', '_')}_{file_hash[:8]}.bin"
        file_path = os.path.join(self.firmware_storage_path, filename)
        
        # Save the firmware file
        with open(file_path, "wb") as f:
            f.write(firmware_data)
        
        # Create new firmware version
        firmware = FirmwareVersion(
            version=version,
            device_type=device_type,
            manufacturer=manufacturer,
            model=model,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            release_date=release_date or datetime.now(),
            release_notes=release_notes,
            is_recommended=is_recommended,
            is_validated=False
        )
        
        session.add(firmware)
        await session.flush()
        
        logger.info(
            f"Uploaded new firmware: {manufacturer} {model} v{version} "
            f"({firmware.id}, {file_size} bytes)"
        )
        return firmware
    
    async def get_firmware(self, session: AsyncSession, firmware_id: int) -> FirmwareVersion:
        """
        Get a firmware version by ID.
        
        Args:
            session: Database session
            firmware_id: Firmware ID
            
        Returns:
            The firmware version
            
        Raises:
            NotFoundException: If the firmware version is not found
        """
        firmware = await session.get(FirmwareVersion, firmware_id)
        if not firmware:
            raise NotFoundException(f"Firmware version with ID {firmware_id} not found")
        return firmware
    
    async def get_firmwares(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        device_type: Optional[DeviceType] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        is_recommended: Optional[bool] = None,
        is_validated: Optional[bool] = None
    ) -> List[FirmwareVersion]:
        """
        Get a list of firmware versions with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            device_type: Filter by device type
            manufacturer: Filter by manufacturer
            model: Filter by model
            is_recommended: Filter by recommended status
            is_validated: Filter by validation status
            
        Returns:
            List of firmware versions
        """
        query = select(FirmwareVersion)
        
        # Apply filters
        if device_type:
            query = query.where(FirmwareVersion.device_type == device_type)
        if manufacturer:
            query = query.where(FirmwareVersion.manufacturer == manufacturer)
        if model:
            query = query.where(FirmwareVersion.model == model)
        if is_recommended is not None:
            query = query.where(FirmwareVersion.is_recommended == is_recommended)
        if is_validated is not None:
            query = query.where(FirmwareVersion.is_validated == is_validated)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def validate_firmware(
        self,
        session: AsyncSession,
        firmware_id: int,
        is_validated: bool,
        validation_notes: Optional[str] = None
    ) -> FirmwareVersion:
        """
        Mark a firmware version as validated or not.
        
        Args:
            session: Database session
            firmware_id: Firmware ID
            is_validated: Whether the firmware is validated
            validation_notes: Notes about the validation
            
        Returns:
            The updated firmware version
            
        Raises:
            NotFoundException: If the firmware version is not found
        """
        firmware = await self.get_firmware(session, firmware_id)
        
        firmware.is_validated = is_validated
        firmware.validation_notes = validation_notes
        
        await session.flush()
        logger.info(
            f"{'Validated' if is_validated else 'Invalidated'} firmware: "
            f"{firmware.manufacturer} {firmware.model} v{firmware.version} ({firmware.id})"
        )
        return firmware
    
    async def delete_firmware(self, session: AsyncSession, firmware_id: int) -> None:
        """
        Delete a firmware version.
        
        Args:
            session: Database session
            firmware_id: Firmware ID
            
        Raises:
            NotFoundException: If the firmware version is not found
        """
        firmware = await self.get_firmware(session, firmware_id)
        
        # Delete the firmware file
        try:
            os.remove(firmware.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete firmware file {firmware.file_path}: {str(e)}")
        
        await session.delete(firmware)
        logger.info(
            f"Deleted firmware: {firmware.manufacturer} {firmware.model} "
            f"v{firmware.version} ({firmware.id})"
        )
    
    async def schedule_update(
        self,
        session: AsyncSession,
        device_id: int,
        firmware_id: int,
        scheduled_by: str,
        scheduled_for: datetime
    ) -> FirmwareUpdateTask:
        """
        Schedule a firmware update for a device.
        
        Args:
            session: Database session
            device_id: Device ID
            firmware_id: Firmware ID
            scheduled_by: Username who scheduled the update
            scheduled_for: When the update is scheduled for
            
        Returns:
            The created update task
            
        Raises:
            NotFoundException: If the device or firmware is not found
            ValidationError: If the firmware is not compatible with the device
        """
        # Check if device exists
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        
        # Check if firmware exists
        firmware = await self.get_firmware(session, firmware_id)
        
        # Check if firmware is compatible with device
        if device.device_type != firmware.device_type:
            raise ValidationError(
                f"Firmware type {firmware.device_type.value} is not compatible with "
                f"device type {device.device_type.value}"
            )
        
        if device.manufacturer and device.manufacturer != firmware.manufacturer:
            raise ValidationError(
                f"Firmware manufacturer {firmware.manufacturer} does not match "
                f"device manufacturer {device.manufacturer}"
            )
        
        if device.model and device.model != firmware.model:
            raise ValidationError(
                f"Firmware model {firmware.model} does not match device model {device.model}"
            )
        
        # Create update task
        task = FirmwareUpdateTask(
            device_id=device_id,
            firmware_version_id=firmware_id,
            scheduled_by=scheduled_by,
            scheduled_for=scheduled_for,
            status=FirmwareUpdateStatus.SCHEDULED
        )
        
        session.add(task)
        await session.flush()
        
        logger.info(
            f"Scheduled firmware update: Device {device_id} to "
            f"{firmware.manufacturer} {firmware.model} v{firmware.version} "
            f"at {scheduled_for.isoformat()} by {scheduled_by}"
        )
        return task
    
    async def get_update_task(self, session: AsyncSession, task_id: int) -> FirmwareUpdateTask:
        """
        Get a firmware update task by ID.
        
        Args:
            session: Database session
            task_id: Task ID
            
        Returns:
            The firmware update task
            
        Raises:
            NotFoundException: If the task is not found
        """
        task = await session.get(FirmwareUpdateTask, task_id)
        if not task:
            raise NotFoundException(f"Firmware update task with ID {task_id} not found")
        return task
    
    async def get_update_tasks(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        device_id: Optional[int] = None,
        status: Optional[FirmwareUpdateStatus] = None,
        scheduled_after: Optional[datetime] = None,
        scheduled_before: Optional[datetime] = None
    ) -> List[FirmwareUpdateTask]:
        """
        Get a list of firmware update tasks with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            device_id: Filter by device ID
            status: Filter by task status
            scheduled_after: Filter by scheduled time (after)
            scheduled_before: Filter by scheduled time (before)
            
        Returns:
            List of firmware update tasks
        """
        query = select(FirmwareUpdateTask)
        
        # Apply filters
        if device_id:
            query = query.where(FirmwareUpdateTask.device_id == device_id)
        if status:
            query = query.where(FirmwareUpdateTask.status == status)
        if scheduled_after:
            query = query.where(FirmwareUpdateTask.scheduled_for >= scheduled_after)
        if scheduled_before:
            query = query.where(FirmwareUpdateTask.scheduled_for <= scheduled_before)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update_task_status(
        self,
        session: AsyncSession,
        task_id: int,
        status: FirmwareUpdateStatus,
        log_output: Optional[str] = None,
        success: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> FirmwareUpdateTask:
        """
        Update the status of a firmware update task.
        
        Args:
            session: Database session
            task_id: Task ID
            status: New task status
            log_output: Log output from the update process
            success: Whether the update was successful
            notes: Additional notes
            
        Returns:
            The updated task
            
        Raises:
            NotFoundException: If the task is not found
        """
        task = await self.get_update_task(session, task_id)
        
        # Update task status
        task.status = status
        
        # Update additional fields based on status
        if status == FirmwareUpdateStatus.IN_PROGRESS:
            task.started_at = datetime.now()
        
        if status in (FirmwareUpdateStatus.COMPLETED, FirmwareUpdateStatus.FAILED):
            task.completed_at = datetime.now()
            task.success = success
        
        if log_output:
            task.log_output = log_output
        
        if notes:
            task.notes = notes
        
        await session.flush()
        logger.info(f"Updated firmware update task {task_id} status to {status.value}")
        
        # If the update was successful, update the device's firmware version
        if status == FirmwareUpdateStatus.COMPLETED and success:
            device = await session.get(Device, task.device_id)
            if device:
                device.firmware_version_id = task.firmware_version_id
                await session.flush()
                logger.info(f"Updated device {device.id} firmware version to {task.firmware_version_id}")
        
        return task
    
    async def cancel_update(
        self,
        session: AsyncSession,
        task_id: int,
        cancelled_by: str,
        reason: Optional[str] = None
    ) -> FirmwareUpdateTask:
        """
        Cancel a scheduled firmware update.
        
        Args:
            session: Database session
            task_id: Task ID
            cancelled_by: Username who cancelled the update
            reason: Reason for cancellation
            
        Returns:
            The cancelled task
            
        Raises:
            NotFoundException: If the task is not found
            ValidationError: If the task cannot be cancelled
        """
        task = await self.get_update_task(session, task_id)
        
        # Check if task can be cancelled
        if task.status != FirmwareUpdateStatus.SCHEDULED:
            raise ValidationError(
                f"Cannot cancel task with status {task.status.value}"
            )
        
        # Update task status
        task.status = FirmwareUpdateStatus.CANCELLED
        task.completed_at = datetime.now()
        task.success = False
        task.notes = f"Cancelled by {cancelled_by}: {reason}" if reason else f"Cancelled by {cancelled_by}"
        
        await session.flush()
        logger.info(f"Cancelled firmware update task {task_id} by {cancelled_by}")
        
        return task
