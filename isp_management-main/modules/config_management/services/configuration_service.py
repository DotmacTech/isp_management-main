"""
Configuration service for the Configuration Management Module.

This service provides methods for managing system configurations, including
CRUD operations, validation, and version control.
"""

from datetime import datetime
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status
import jsonschema

from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigurationGroup, ConfigurationGroupItem,
    ConfigEnvironment, ConfigCategory
)
from modules.config_management.services.encryption_service import EncryptionService
from modules.config_management.services.cache_service import CacheService
from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService
from sqlalchemy import func
from sqlalchemy import exists
from datetime import timedelta

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service for managing system configurations."""
    
    def __init__(self, db: Session, encryption_service: Optional[EncryptionService] = None, 
                 cache_service: Optional[CacheService] = None,
                 es_service: Optional[ConfigurationElasticsearchService] = None):
        """
        Initialize the configuration service.
        
        Args:
            db: Database session
            encryption_service: Service for encrypting/decrypting sensitive configurations
            cache_service: Service for caching frequently accessed configurations
            es_service: Service for Elasticsearch integration
        """
        self.db = db
        self.encryption_service = encryption_service or EncryptionService()
        self.cache_service = cache_service or CacheService()
        self.es_service = es_service
        self.elasticsearch_enabled = es_service is not None
    
    def get_configuration(self, key: str, environment: Optional[str] = None, include_inactive: bool = False) -> Optional[Configuration]:
        """
        Get a configuration by key and environment.
        
        Args:
            key: Configuration key
            environment: Environment to get configuration for (defaults to current environment)
            include_inactive: Whether to include inactive configurations
            
        Returns:
            Configuration if found, None otherwise
        """
        try:
            if not environment:
                environment = ConfigEnvironment.ALL
                
            # First try to get from cache
            cached_config = self.cache_service.get_configuration(key, environment)
            if cached_config:
                # If encrypted, decrypt the value
                if cached_config.is_encrypted and self.encryption_service:
                    cached_config.value = self.encryption_service.decrypt(cached_config.value)
                return cached_config
            
            # If not in cache, query database
            query = self.db.query(Configuration)
            query = query.filter(Configuration.key == key)
            
            # Filter by environment (ALL or specific environment)
            query = query.filter(
                or_(
                    Configuration.environment == environment,
                    Configuration.environment == ConfigEnvironment.ALL
                )
            )
            
            # Filter active configurations by default
            if not include_inactive:
                query = query.filter(Configuration.is_active == True)
                
            config = query.first()
            
            # Add to cache if found
            if config:
                self.cache_service.set_configuration(config)
                
                # If encrypted, decrypt the value
                if config.is_encrypted and self.encryption_service:
                    config.value = self.encryption_service.decrypt(config.value)
                
            return config
        except Exception as e:
            logger.error(f"Error getting configuration: {str(e)}")
            return None
    
    def get_configuration_value(self, key: str, environment: Optional[str] = None, 
                               default: Any = None) -> Any:
        """
        Get a configuration value by key and environment.
        
        Args:
            key: Configuration key
            environment: Environment to get configuration for (defaults to current environment)
            default: Default value to return if configuration not found
            
        Returns:
            Configuration value if found, default otherwise
        """
        config = self.get_configuration(key, environment)
        return config.value if config else default
    
    def get_configurations(self, filters: Dict[str, Any] = None, 
                          skip: int = 0, limit: int = 100) -> List[Configuration]:
        """
        Get configurations based on filters.
        
        Args:
            filters: Dictionary of filter conditions
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of configurations matching the filters
        """
        query = self.db.query(Configuration)
        
        # Filter out inactive configurations by default, unless explicitly requested
        filters = filters or {}
        if 'is_active' not in filters:
            query = query.filter(Configuration.is_active == True)
        
        if filters:
            if 'key' in filters and filters['key']:
                query = query.filter(Configuration.key.ilike(f"%{filters['key']}%"))
            
            if 'environment' in filters and filters['environment']:
                query = query.filter(Configuration.environment == filters['environment'])
            
            if 'category' in filters and filters['category']:
                query = query.filter(Configuration.category == filters['category'])
            
            if 'is_active' in filters and filters['is_active'] is not None:
                query = query.filter(Configuration.is_active == filters['is_active'])
            
            if 'is_encrypted' in filters and filters['is_encrypted'] is not None:
                query = query.filter(Configuration.is_encrypted == filters['is_encrypted'])
            
            if 'created_by' in filters and filters['created_by']:
                query = query.filter(Configuration.created_by == filters['created_by'])
            
            if 'created_after' in filters and filters['created_after']:
                query = query.filter(Configuration.created_at >= filters['created_after'])
            
            if 'created_before' in filters and filters['created_before']:
                query = query.filter(Configuration.created_at <= filters['created_before'])
            
            if 'updated_after' in filters and filters['updated_after']:
                query = query.filter(Configuration.updated_at >= filters['updated_after'])
            
            if 'updated_before' in filters and filters['updated_before']:
                query = query.filter(Configuration.updated_at <= filters['updated_before'])
        
        return query.order_by(Configuration.key).offset(skip).limit(limit).all()
    
    def create_configuration(self, config_data: Dict[str, Any], created_by: str) -> Configuration:
        """
        Create a new configuration.
        
        Args:
            config_data: Configuration data
            created_by: User who created the configuration
            
        Returns:
            Created configuration
            
        Raises:
            HTTPException: If a configuration with the same key already exists
        """
        # Check if a configuration with the same key already exists
        existing_config = self.get_configuration(config_data["key"], config_data.get("environment", ConfigEnvironment.ALL))
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Configuration with key '{config_data['key']}' already exists in environment '{config_data.get('environment', ConfigEnvironment.ALL)}'"
            )
        
        # Validate schema if provided
        if "validation_schema" in config_data and config_data["validation_schema"]:
            try:
                self._validate_schema(config_data["validation_schema"])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid validation schema: {str(e)}"
                )
                
            # Validate value against schema
            try:
                self._validate_value(config_data["value"], config_data["validation_schema"])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # Encrypt value if needed
        if config_data.get("is_encrypted", False):
            config_data["value"] = self.encryption_service.encrypt(config_data["value"])
        
        # Create configuration
        config = Configuration(
            key=config_data["key"],
            value=config_data["value"],
            description=config_data.get("description"),
            environment=config_data.get("environment", ConfigEnvironment.ALL),
            category=config_data.get("category", ConfigCategory.SYSTEM),
            is_encrypted=config_data.get("is_encrypted", False),
            validation_schema=config_data.get("validation_schema"),
            version=1,
            is_active=config_data.get("is_active", True),
            created_by=created_by,
            elasticsearch_synced=False
        )
        
        try:
            # Add to database
            self.db.add(config)
            self.db.flush()
            
            # Create history entry
            history = ConfigurationHistory(
                configuration_id=config.id,
                key=config.key,
                value=config.value,
                environment=config.environment,
                category=config.category,
                is_encrypted=config.is_encrypted,
                version=config.version,
                action="create",
                created_by=created_by,
                elasticsearch_synced=False
            )
            self.db.add(history)
            self.db.commit()
            
            # Add to cache
            self.cache_service.set_configuration(config)
            
            # Index in Elasticsearch if enabled
            if self.elasticsearch_enabled:
                self.es_service.index_configuration(config)
                self.es_service.index_configuration_history(history)
                
                # Update elasticsearch_synced flag
                config.elasticsearch_synced = True
                history.elasticsearch_synced = True
                self.db.commit()
            
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating configuration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating configuration: {str(e)}"
            )
    
    def update_configuration(self, key: str, config_data: Dict[str, Any], updated_by: str, environment: str = ConfigEnvironment.ALL) -> Configuration:
        """
        Update an existing configuration.
        
        Args:
            key: Configuration key
            config_data: Updated configuration data
            updated_by: User who updated the configuration
            environment: Configuration environment
            
        Returns:
            Updated configuration
            
        Raises:
            HTTPException: If the configuration does not exist
        """
        # Get existing configuration
        config = self.get_configuration(key, environment)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration with key '{key}' not found in environment '{environment}'"
            )
        
        # Validate schema if provided
        if "validation_schema" in config_data and config_data["validation_schema"]:
            try:
                self._validate_schema(config_data["validation_schema"])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid validation schema: {str(e)}"
                )
                
            # Validate value against schema
            try:
                if "value" in config_data:
                    self._validate_value(config_data["value"], config_data["validation_schema"])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # Update version
        new_version = config.version + 1
        
        # First update the configuration object with new values
        for field, value in config_data.items():
            if hasattr(config, field):
                # Encrypt value if needed
                if field == "value" and config_data.get("is_encrypted", config.is_encrypted):
                    value = self.encryption_service.encrypt(value)
                setattr(config, field, value)
        
        # Create history entry with the new values
        history = ConfigurationHistory(
            configuration_id=config.id,
            key=config.key,
            value=config.value,  # This will now be the new value
            environment=config.environment,
            category=config.category,
            is_encrypted=config.is_encrypted,
            version=new_version,
            action="update",
            created_by=updated_by,
            elasticsearch_synced=False
        )
        
        try:
            # Update version and metadata
            config.version = new_version
            config.updated_by = updated_by
            config.updated_at = datetime.utcnow()
            config.elasticsearch_synced = False
            
            # Add history entry
            self.db.add(history)
            self.db.commit()
            
            # Update cache
            self.cache_service.set_configuration(config)
            
            # Index in Elasticsearch if enabled
            if self.elasticsearch_enabled:
                self.es_service.index_configuration(config)
                self.es_service.index_configuration_history(history)
                
                # Update elasticsearch_synced flag
                config.elasticsearch_synced = True
                history.elasticsearch_synced = True
                self.db.commit()
            
            # If the value is encrypted, decrypt it for the return
            if config.is_encrypted and self.encryption_service:
                config.value = self.encryption_service.decrypt(config.value)
                
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating configuration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating configuration: {str(e)}"
            )
    
    def delete_configuration(self, key: str, deleted_by: str, environment: str = ConfigEnvironment.ALL) -> bool:
        """
        Delete a configuration.
        
        Args:
            key: Configuration key
            deleted_by: User who deleted the configuration
            environment: Configuration environment
            
        Returns:
            True if the configuration was deleted
            
        Raises:
            HTTPException: If the configuration does not exist
        """
        # Get existing configuration
        config = self.get_configuration(key, environment)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration with key '{key}' not found in environment '{environment}'"
            )
        
        try:
            # Create history entry before deactivating
            history = ConfigurationHistory(
                configuration_id=config.id,
                key=config.key,
                value=config.value,
                environment=config.environment,
                category=config.category,
                is_encrypted=config.is_encrypted,
                version=config.version,
                action="delete",
                created_by=deleted_by,
                elasticsearch_synced=False
            )
            self.db.add(history)
            
            # Mark as inactive instead of deleting
            config.is_active = False
            config.updated_by = deleted_by
            config.updated_at = datetime.utcnow()
            config.elasticsearch_synced = False
            self.db.commit()
            
            # Remove from cache
            self.cache_service.delete_configuration(key, environment)
            
            # Update in Elasticsearch if enabled
            if self.elasticsearch_enabled:
                self.es_service.index_configuration(config)
                self.es_service.index_configuration_history(history)
                
                # Update elasticsearch_synced flag
                config.elasticsearch_synced = True
                history.elasticsearch_synced = True
                self.db.commit()
            
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting configuration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting configuration: {str(e)}"
            )
    
    def get_configuration_history(self, key: str, environment: Optional[str] = None,
                                 skip: int = 0, limit: int = 100) -> List[ConfigurationHistory]:
        """
        Get history of a configuration.
        
        Args:
            key: Configuration key
            environment: Environment of the configuration
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of configuration history entries
            
        Raises:
            HTTPException: If configuration not found
        """
        # Get the configuration - including inactive ones
        config = self.get_configuration(key, environment, include_inactive=True)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration with key '{key}' not found in environment '{environment}'"
            )
        
        # Query history
        query = self.db.query(ConfigurationHistory).filter(
            ConfigurationHistory.configuration_id == config.id
        )
        
        return query.order_by(ConfigurationHistory.created_at.desc()).offset(skip).limit(limit).all()
    
    def _validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate a JSON schema.
        
        Args:
            schema: JSON schema to validate
            
        Returns:
            True if schema is valid
            
        Raises:
            Exception: If schema is invalid
        """
        try:
            # Basic validation of schema structure
            required_keys = ["type"]
            for key in required_keys:
                if key not in schema:
                    raise ValueError(f"Schema is missing required key: {key}")
                    
            # Validate type
            valid_types = ["string", "number", "integer", "boolean", "array", "object", "null"]
            if schema["type"] not in valid_types:
                raise ValueError(f"Invalid schema type: {schema['type']}")
                
            # Check for min/max constraints
            if schema["type"] in ["number", "integer"]:
                if "minimum" in schema and not isinstance(schema["minimum"], (int, float)):
                    raise ValueError("'minimum' must be a number")
                if "maximum" in schema and not isinstance(schema["maximum"], (int, float)):
                    raise ValueError("'maximum' must be a number")
                if "minimum" in schema and "maximum" in schema and schema["minimum"] > schema["maximum"]:
                    raise ValueError("'minimum' cannot be greater than 'maximum'")
                    
            # Check for string constraints
            if schema["type"] == "string":
                if "minLength" in schema and not isinstance(schema["minLength"], int):
                    raise ValueError("'minLength' must be an integer")
                if "maxLength" in schema and not isinstance(schema["maxLength"], int):
                    raise ValueError("'maxLength' must be an integer")
                if "minLength" in schema and "maxLength" in schema and schema["minLength"] > schema["maxLength"]:
                    raise ValueError("'minLength' cannot be greater than 'maxLength'")
                    
            # Check for array constraints
            if schema["type"] == "array":
                if "items" not in schema:
                    raise ValueError("Array schema must include 'items' property")
                    
            return True
        except Exception as e:
            raise ValueError(f"Invalid schema: {str(e)}")
            
    def _validate_value(self, value: Any, schema: Dict[str, Any]) -> bool:
        """
        Validate a value against a JSON schema.
        
        Args:
            value: Value to validate
            schema: JSON schema to validate against
            
        Returns:
            True if value is valid
            
        Raises:
            Exception: If value is invalid
        """
        try:
            # Basic type validation
            if schema["type"] == "string":
                if not isinstance(value, str):
                    raise ValueError(f"Value must be a string, got {type(value).__name__}")
                    
                # String length validation
                if "minLength" in schema and len(value) < schema["minLength"]:
                    raise ValueError(f"String length must be at least {schema['minLength']}")
                if "maxLength" in schema and len(value) > schema["maxLength"]:
                    raise ValueError(f"String length must be at most {schema['maxLength']}")
                    
            elif schema["type"] == "number":
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Value must be a number, got {type(value).__name__}")
                    
                # Number range validation
                if "minimum" in schema and value < schema["minimum"]:
                    raise ValueError(f"Value must be at least {schema['minimum']}")
                if "maximum" in schema and value > schema["maximum"]:
                    raise ValueError(f"Value must be at most {schema['maximum']}")
                    
            elif schema["type"] == "integer":
                if not isinstance(value, int) or isinstance(value, bool):
                    raise ValueError(f"Value must be an integer, got {type(value).__name__}")
                    
                # Integer range validation
                if "minimum" in schema and value < schema["minimum"]:
                    raise ValueError(f"Value must be at least {schema['minimum']}")
                if "maximum" in schema and value > schema["maximum"]:
                    raise ValueError(f"Value must be at most {schema['maximum']}")
                    
            elif schema["type"] == "boolean":
                if not isinstance(value, bool):
                    raise ValueError(f"Value must be a boolean, got {type(value).__name__}")
                    
            elif schema["type"] == "array":
                if not isinstance(value, list):
                    raise ValueError(f"Value must be an array, got {type(value).__name__}")
                    
                # Array length validation
                if "minItems" in schema and len(value) < schema["minItems"]:
                    raise ValueError(f"Array must have at least {schema['minItems']} items")
                if "maxItems" in schema and len(value) > schema["maxItems"]:
                    raise ValueError(f"Array must have at most {schema['maxItems']} items")
                    
                # Array item validation
                if "items" in schema:
                    for item in value:
                        self._validate_value(item, schema["items"])
                        
            elif schema["type"] == "object":
                if not isinstance(value, dict):
                    raise ValueError(f"Value must be an object, got {type(value).__name__}")
                    
                # Required properties validation
                if "required" in schema:
                    for prop in schema["required"]:
                        if prop not in value:
                            raise ValueError(f"Required property '{prop}' is missing")
                            
                # Property validation
                if "properties" in schema:
                    for prop, prop_schema in schema["properties"].items():
                        if prop in value:
                            self._validate_value(value[prop], prop_schema)
                            
            return True
        except Exception as e:
            raise ValueError(f"Value does not match validation schema: {str(e)}")
    
    def bulk_update_configurations(self, configurations: List[Dict[str, Any]], 
                                  user_id: str) -> List[Configuration]:
        """
        Update multiple configurations in a single transaction.
        
        Args:
            configurations: List of configuration data to update
            user_id: ID of the user updating the configurations
            
        Returns:
            List of updated configurations
            
        Raises:
            HTTPException: If any validation fails
        """
        updated_configs = []
        
        try:
            for config_data in configurations:
                key = config_data.pop('key')
                environment = config_data.pop('environment', None)
                
                # Get existing configuration
                query = self.db.query(Configuration).filter(
                    Configuration.key == key,
                    Configuration.is_active == True
                )
                
                if environment:
                    query = query.filter(Configuration.environment == environment)
                else:
                    query = query.filter(Configuration.environment == ConfigEnvironment.ALL)
                
                config = query.first()
                
                if not config:
                    # Create new configuration if not exists
                    config_data['key'] = key
                    if environment:
                        config_data['environment'] = environment
                    
                    config = self.create_configuration(config_data, user_id)
                else:
                    # Update existing configuration
                    config = self.update_configuration(key, config_data, user_id, environment)
                
                updated_configs.append(config)
            
            self.db.commit()
            
            # Invalidate cache for all updated configurations
            for config in updated_configs:
                self.cache_service.delete(f"config:{config.key}:{config.environment}")
            
            return updated_configs
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in bulk update: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error in bulk update: {str(e)}"
            )
    
    def create_configuration_group(self, group_data: Dict[str, Any], created_by: str) -> ConfigurationGroup:
        """
        Create a new configuration group.
        
        Args:
            group_data: Group data
            created_by: User who created the group
            
        Returns:
            Created configuration group
            
        Raises:
            HTTPException: If a group with the same name already exists
        """
        # Check if a group with the same name already exists
        existing_group = self.db.query(ConfigurationGroup).filter(
            ConfigurationGroup.name == group_data["name"]
        ).first()
        
        if existing_group:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Configuration group with name '{group_data['name']}' already exists"
            )
        
        # Create group
        group = ConfigurationGroup(
            name=group_data["name"],
            description=group_data.get("description"),
            environment=group_data.get("environment", ConfigEnvironment.ALL),
            is_active=group_data.get("is_active", True),
            created_by=created_by,
            elasticsearch_synced=False
        )
        
        try:
            # Add to database
            self.db.add(group)
            self.db.commit()
            
            # Index in Elasticsearch if enabled
            if self.elasticsearch_enabled:
                self.es_service.index_configuration_group(group)
                
                # Update elasticsearch_synced flag
                group.elasticsearch_synced = True
                self.db.commit()
            
            return group
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating configuration group: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating configuration group: {str(e)}"
            )
    
    def get_configuration_group(self, group_id: str, with_configurations: bool = False) -> Optional[ConfigurationGroup]:
        """
        Get a configuration group by ID.
        
        Args:
            group_id: Group ID
            with_configurations: Whether to include configurations in the group
            
        Returns:
            Configuration group if found, None otherwise
        """
        group = self.db.query(ConfigurationGroup).filter(
            ConfigurationGroup.id == group_id
        ).first()
        
        if group and with_configurations:
            # Get configurations in the group
            config_ids = self.db.query(ConfigurationGroupItem.configuration_id).filter(
                ConfigurationGroupItem.group_id == group_id
            ).all()
            
            config_ids = [item[0] for item in config_ids]
            
            configurations = self.db.query(Configuration).filter(
                Configuration.id.in_(config_ids),
                Configuration.is_active == True
            ).all()
            
            # Attach configurations to group (not persisted, just for return value)
            setattr(group, 'configurations', configurations)
        
        return group
    
    def get_configuration_groups(self, skip: int = 0, limit: int = 100) -> List[ConfigurationGroup]:
        """
        Get all configuration groups.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of configuration groups
        """
        return self.db.query(ConfigurationGroup).order_by(
            ConfigurationGroup.name
        ).offset(skip).limit(limit).all()
    
    def update_configuration_group(self, group_id: int, group_data: Dict[str, Any], updated_by: str) -> ConfigurationGroup:
        """
        Update an existing configuration group.
        
        Args:
            group_id: Group ID
            group_data: Updated group data
            updated_by: User updating the group
            
        Returns:
            Updated configuration group
            
        Raises:
            HTTPException: If group not found
        """
        # Get existing group
        group = self.db.query(ConfigurationGroup).filter(
            ConfigurationGroup.id == group_id,
            ConfigurationGroup.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration group with ID {group_id} not found"
            )
        
        # Update group fields
        if "name" in group_data:
            # Check if another group with the same name exists
            existing_group = self.db.query(ConfigurationGroup).filter(
                ConfigurationGroup.name == group_data["name"],
                ConfigurationGroup.id != group_id,
                ConfigurationGroup.is_active == True
            ).first()
            
            if existing_group:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Configuration group with name '{group_data['name']}' already exists"
                )
            
            group.name = group_data["name"]
        
        if "description" in group_data:
            group.description = group_data["description"]
        
        if "environment" in group_data:
            group.environment = group_data["environment"]
        
        group.updated_by = updated_by
        group.updated_at = datetime.utcnow()
        
        # Update configurations if provided
        if "configurations" in group_data:
            # Remove existing items
            self.db.query(ConfigurationGroupItem).filter(
                ConfigurationGroupItem.group_id == group.id
            ).delete()
            
            # Add new items
            for config_key in group_data["configurations"]:
                config = self.get_configuration(config_key, group.environment)
                if config and config.is_active:
                    group_item = ConfigurationGroupItem(
                        group_id=group.id,
                        configuration_id=config.id,
                        created_by=updated_by,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(group_item)
        
        self.db.commit()
        
        # Index in Elasticsearch if enabled
        if self.elasticsearch_enabled:
            try:
                self.es_service.index_configuration_group(group)
            except Exception as e:
                logger.error(f"Error indexing configuration group in Elasticsearch: {str(e)}")
        
        return group
    
    def delete_configuration_group(self, group_id: int, deleted_by: str) -> bool:
        """
        Delete (deactivate) a configuration group.
        
        Args:
            group_id: Group ID
            deleted_by: User deleting the group
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            HTTPException: If group not found
        """
        # Get existing group
        group = self.db.query(ConfigurationGroup).filter(
            ConfigurationGroup.id == group_id,
            ConfigurationGroup.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration group with ID {group_id} not found"
            )
        
        # Deactivate group
        group.is_active = False
        group.updated_by = deleted_by
        group.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Index in Elasticsearch if enabled
        if self.elasticsearch_enabled:
            try:
                self.es_service.index_configuration_group(group)
            except Exception as e:
                logger.error(f"Error updating configuration group in Elasticsearch: {str(e)}")
        
        return True
    
    def search_configurations(self, query: str, environment: Optional[str] = None, 
                             category: Optional[str] = None, active_only: bool = True,
                             skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search configurations using Elasticsearch.
        
        Args:
            query: Search query string
            environment: Filter by environment
            category: Filter by category
            active_only: Only include active configurations
            skip: Number of results to skip
            limit: Maximum number of results to return
            
        Returns:
            List of matching configurations
            
        Raises:
            HTTPException: If Elasticsearch is not enabled or search fails
        """
        if not self.elasticsearch_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Elasticsearch is not enabled for this service"
            )
        
        try:
            search_results = self.es_service.search_configurations(
                query=query,
                environment=environment,
                category=category,
                active_only=active_only,
                from_=skip,
                size=limit
            )
            
            return search_results
        except Exception as e:
            logger.error(f"Error searching configurations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching configurations: {str(e)}"
            )
    
    def get_configuration_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configurations using Elasticsearch.
        
        Returns:
            Dictionary containing configuration statistics
            
        Raises:
            HTTPException: If Elasticsearch is not enabled or statistics retrieval fails
        """
        if not self.elasticsearch_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Elasticsearch is not enabled for this service"
            )
        
        try:
            statistics = self.es_service.get_configuration_statistics()
            return statistics
        except Exception as e:
            logger.error(f"Error getting configuration statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting configuration statistics: {str(e)}"
            )
    
    def sync_configurations_to_elasticsearch(self) -> Dict[str, int]:
        """
        Sync all configurations, configuration history, and configuration groups to Elasticsearch.
        
        Returns:
            Dictionary with counts of indexed items
            
        Raises:
            HTTPException: If Elasticsearch is not enabled or sync fails
        """
        if not self.elasticsearch_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Elasticsearch is not enabled for this service"
            )
        
        try:
            # Get all configurations that haven't been synced or have been updated
            configurations = self.db.query(Configuration).filter(
                or_(
                    Configuration.elasticsearch_synced == False,
                    and_(
                        Configuration.updated_at != None,
                        Configuration.updated_at > Configuration.created_at
                    )
                )
            ).all()
            
            # Get all configuration history items that haven't been synced
            history_items = self.db.query(ConfigurationHistory).filter(
                ConfigurationHistory.elasticsearch_synced == False
            ).all()
            
            # Get all configuration groups that haven't been synced or have been updated
            groups = self.db.query(ConfigurationGroup).filter(
                or_(
                    ConfigurationGroup.elasticsearch_synced == False,
                    and_(
                        ConfigurationGroup.updated_at != None,
                        ConfigurationGroup.updated_at > ConfigurationGroup.created_at
                    )
                )
            ).all()
            
            # Bulk index configurations
            config_count = self.es_service.bulk_index_configurations(configurations)
            
            # Bulk index configuration history
            history_count = self.es_service.bulk_index_configuration_history(history_items)
            
            # Bulk index configuration groups
            group_count = self.es_service.bulk_index_configuration_groups(groups)
            
            # Commit the changes to the database
            self.db.commit()
            
            return {
                "configurations_indexed": config_count,
                "history_items_indexed": history_count,
                "groups_indexed": group_count
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing configurations to Elasticsearch: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error syncing configurations to Elasticsearch: {str(e)}"
            )
    
    def cleanup_old_history(self, days_to_keep: int = 90) -> int:
        """
        Clean up old configuration history entries.
        
        Args:
            days_to_keep: Number of days of history to keep
            
        Returns:
            Number of history entries deleted
        """
        if days_to_keep < 1:
            raise ValueError("days_to_keep must be at least 1")
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Find history entries older than cutoff date
            # But keep at least one history entry per configuration
            subquery = self.db.query(
                ConfigurationHistory.configuration_id,
                func.max(ConfigurationHistory.created_at).label('max_date')
            ).group_by(ConfigurationHistory.configuration_id).subquery()
            
            # Get IDs of history entries to delete
            to_delete = self.db.query(ConfigurationHistory).filter(
                ConfigurationHistory.created_at < cutoff_date,
                ~exists().where(
                    and_(
                        subquery.c.configuration_id == ConfigurationHistory.configuration_id,
                        subquery.c.max_date == ConfigurationHistory.created_at
                    )
                )
            )
            
            # Count how many will be deleted
            count = to_delete.count()
            
            # Delete the entries
            to_delete.delete(synchronize_session=False)
            
            self.db.commit()
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up configuration history: {str(e)}")
            raise
