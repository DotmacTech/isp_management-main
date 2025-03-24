"""
Configuration Management Service for the Network Management Module.
"""

import logging
import jinja2
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException, ValidationError, ConflictError
from core.services import BaseService
from modules.network.models import (
    Device, DeviceType, ConfigurationTemplate, DeviceConfiguration
)

logger = logging.getLogger(__name__)


class ConfigurationService(BaseService):
    """Service for managing device configurations and templates."""
    
    async def create_template(
        self,
        session: AsyncSession,
        name: str,
        device_type: DeviceType,
        template_content: str,
        version: str,
        variables: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> ConfigurationTemplate:
        """
        Create a new configuration template.
        
        Args:
            session: Database session
            name: Template name
            device_type: Type of device this template is for
            template_content: Jinja2 template content
            version: Template version
            variables: JSON schema for template variables
            description: Template description
            
        Returns:
            The created configuration template
            
        Raises:
            ValidationError: If the template data is invalid
        """
        # Validate template syntax
        try:
            jinja2.Template(template_content)
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise ValidationError(f"Invalid template syntax: {str(e)}")
        
        # Create new template
        template = ConfigurationTemplate(
            name=name,
            device_type=device_type,
            template_content=template_content,
            version=version,
            variables=variables,
            description=description,
            is_active=True
        )
        
        session.add(template)
        await session.flush()
        
        logger.info(f"Created new configuration template: {template.name} v{template.version} ({template.id})")
        return template
    
    async def get_template(self, session: AsyncSession, template_id: int) -> ConfigurationTemplate:
        """
        Get a configuration template by ID.
        
        Args:
            session: Database session
            template_id: Template ID
            
        Returns:
            The configuration template
            
        Raises:
            NotFoundException: If the template is not found
        """
        template = await session.get(ConfigurationTemplate, template_id)
        if not template:
            raise NotFoundException(f"Configuration template with ID {template_id} not found")
        return template
    
    async def get_templates(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        device_type: Optional[DeviceType] = None,
        is_active: Optional[bool] = None
    ) -> List[ConfigurationTemplate]:
        """
        Get a list of configuration templates with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            device_type: Filter by device type
            is_active: Filter by active status
            
        Returns:
            List of configuration templates
        """
        query = select(ConfigurationTemplate)
        
        # Apply filters
        if device_type:
            query = query.where(ConfigurationTemplate.device_type == device_type)
        if is_active is not None:
            query = query.where(ConfigurationTemplate.is_active == is_active)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update_template(
        self,
        session: AsyncSession,
        template_id: int,
        **kwargs
    ) -> ConfigurationTemplate:
        """
        Update a configuration template.
        
        Args:
            session: Database session
            template_id: Template ID
            **kwargs: Template properties to update
            
        Returns:
            The updated configuration template
            
        Raises:
            NotFoundException: If the template is not found
            ValidationError: If the update data is invalid
        """
        template = await self.get_template(session, template_id)
        
        # Validate template syntax if content is being updated
        if "template_content" in kwargs:
            try:
                jinja2.Template(kwargs["template_content"])
            except jinja2.exceptions.TemplateSyntaxError as e:
                raise ValidationError(f"Invalid template syntax: {str(e)}")
        
        # Update template properties
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        await session.flush()
        logger.info(f"Updated configuration template: {template.name} v{template.version} ({template.id})")
        return template
    
    async def delete_template(self, session: AsyncSession, template_id: int) -> None:
        """
        Delete a configuration template.
        
        Args:
            session: Database session
            template_id: Template ID
            
        Raises:
            NotFoundException: If the template is not found
        """
        template = await self.get_template(session, template_id)
        await session.delete(template)
        logger.info(f"Deleted configuration template: {template.name} v{template.version} ({template.id})")
    
    async def generate_configuration(
        self,
        session: AsyncSession,
        template_id: int,
        variables: Dict[str, Any]
    ) -> str:
        """
        Generate a configuration from a template.
        
        Args:
            session: Database session
            template_id: Template ID
            variables: Template variables
            
        Returns:
            The generated configuration
            
        Raises:
            NotFoundException: If the template is not found
            ValidationError: If the variables are invalid
        """
        template = await self.get_template(session, template_id)
        
        # Validate variables against schema if defined
        if template.variables:
            # This would use a JSON schema validator in a real implementation
            # For now, we'll just check that all required variables are provided
            for var_name, var_schema in template.variables.items():
                if var_schema.get("required", False) and var_name not in variables:
                    raise ValidationError(f"Missing required variable: {var_name}")
        
        # Render the template
        try:
            jinja_template = jinja2.Template(template.template_content)
            config = jinja_template.render(**variables)
            return config
        except jinja2.exceptions.UndefinedError as e:
            raise ValidationError(f"Template rendering error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Failed to generate configuration: {str(e)}")
    
    async def create_device_configuration(
        self,
        session: AsyncSession,
        device_id: int,
        config_content: str,
        version: str,
        applied_by: Optional[str] = None,
        template_id: Optional[int] = None,
        template_variables: Optional[Dict[str, Any]] = None
    ) -> DeviceConfiguration:
        """
        Create a new configuration version for a device.
        
        Args:
            session: Database session
            device_id: Device ID
            config_content: Configuration content
            version: Configuration version
            applied_by: Username who applied this configuration
            template_id: ID of the template used to generate this configuration
            template_variables: Variables used with the template
            
        Returns:
            The created device configuration
            
        Raises:
            NotFoundException: If the device is not found
        """
        # Check if device exists
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        
        # If template_id is provided, check if it exists
        if template_id:
            template = await session.get(ConfigurationTemplate, template_id)
            if not template:
                raise NotFoundException(f"Configuration template with ID {template_id} not found")
        
        # Create new configuration
        config = DeviceConfiguration(
            device_id=device_id,
            config_content=config_content,
            version=version,
            applied_by=applied_by,
            applied_at=datetime.now() if applied_by else None,
            is_active=False,
            template_id=template_id,
            template_variables=template_variables
        )
        
        session.add(config)
        await session.flush()
        
        logger.info(f"Created new configuration for device {device_id}: v{version} ({config.id})")
        return config
    
    async def apply_configuration(
        self,
        session: AsyncSession,
        config_id: int,
        applied_by: str
    ) -> DeviceConfiguration:
        """
        Apply a configuration to a device and mark it as active.
        
        Args:
            session: Database session
            config_id: Configuration ID
            applied_by: Username who is applying the configuration
            
        Returns:
            The applied configuration
            
        Raises:
            NotFoundException: If the configuration is not found
        """
        # Get the configuration
        config = await session.get(DeviceConfiguration, config_id)
        if not config:
            raise NotFoundException(f"Device configuration with ID {config_id} not found")
        
        # Get the device
        device = await session.get(Device, config.device_id)
        if not device:
            raise NotFoundException(f"Device with ID {config.device_id} not found")
        
        # Mark all other configurations as inactive
        await session.execute(
            update(DeviceConfiguration)
            .where(DeviceConfiguration.device_id == config.device_id)
            .values(is_active=False)
        )
        
        # Update the configuration
        config.is_active = True
        config.applied_by = applied_by
        config.applied_at = datetime.now()
        
        # Update the device's current configuration
        device.current_config_id = config.id
        
        await session.flush()
        logger.info(f"Applied configuration {config_id} to device {config.device_id} by {applied_by}")
        
        # In a real implementation, this would actually push the configuration to the device
        # For now, we'll just return the configuration
        return config
    
    async def get_device_configurations(
        self,
        session: AsyncSession,
        device_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[DeviceConfiguration]:
        """
        Get a list of configurations for a device.
        
        Args:
            session: Database session
            device_id: Device ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of device configurations
            
        Raises:
            NotFoundException: If the device is not found
        """
        # Check if device exists
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        
        # Get configurations
        query = select(DeviceConfiguration).where(
            DeviceConfiguration.device_id == device_id
        ).order_by(
            DeviceConfiguration.created_at.desc()
        ).offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_active_configuration(
        self,
        session: AsyncSession,
        device_id: int
    ) -> Optional[DeviceConfiguration]:
        """
        Get the active configuration for a device.
        
        Args:
            session: Database session
            device_id: Device ID
            
        Returns:
            The active configuration or None if no active configuration exists
            
        Raises:
            NotFoundException: If the device is not found
        """
        # Check if device exists
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        
        # Get active configuration
        query = select(DeviceConfiguration).where(
            and_(
                DeviceConfiguration.device_id == device_id,
                DeviceConfiguration.is_active == True
            )
        )
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
