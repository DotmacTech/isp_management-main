"""
API routes for configuration management.

This module defines the FastAPI routes for the configuration management API,
including CRUD operations for configurations and configuration groups.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user, require_permissions
from modules.config_management.schemas.configuration import (
    ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse,
    ConfigurationHistoryResponse, ConfigurationGroupCreate, ConfigurationGroupUpdate,
    ConfigurationGroupResponse, ConfigurationBulkUpdate, ConfigurationFilter,
    ConfigurationSearchResponse, ConfigurationStatisticsResponse
)
from modules.config_management.services.configuration_service import ConfigurationService
from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService
from modules.config_management.models.configuration import ConfigEnvironment, ConfigCategory


configuration_router = APIRouter(
    prefix="/api/v1/configurations",
    tags=["configurations"],
    responses={404: {"description": "Not found"}},
)


@configuration_router.get("/", response_model=List[ConfigurationResponse])
async def get_configurations(
    key: Optional[str] = Query(None, description="Filter by key (partial match)"),
    environment: Optional[ConfigEnvironment] = Query(None, description="Filter by environment"),
    category: Optional[ConfigCategory] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_encrypted: Optional[bool] = Query(None, description="Filter by encryption status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get configurations based on filters.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    filters = {
        "key": key,
        "environment": environment,
        "category": category,
        "is_active": is_active,
        "is_encrypted": is_encrypted
    }
    
    # Remove None values from filters
    filters = {k: v for k, v in filters.items() if v is not None}
    
    service = ConfigurationService(db)
    return service.get_configurations(filters, skip, limit)


@configuration_router.get("/{key}", response_model=ConfigurationResponse)
async def get_configuration(
    key: str = Path(..., description="Configuration key"),
    environment: Optional[ConfigEnvironment] = Query(None, description="Environment"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific configuration by key and environment.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    service = ConfigurationService(db)
    config = service.get_configuration(key, environment)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with key '{key}' not found for environment '{environment or ConfigEnvironment.ALL}'"
        )
    
    return config


@configuration_router.post("/", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    config: ConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new configuration.
    
    Requires authentication and 'configurations:create' permission.
    """
    require_permissions(current_user, ["configurations:create"])
    
    service = ConfigurationService(db)
    return service.create_configuration(config.model_dump(), current_user["id"])


@configuration_router.put("/{key}", response_model=ConfigurationResponse)
async def update_configuration(
    key: str = Path(..., description="Configuration key"),
    config: ConfigurationUpdate = None,
    environment: Optional[ConfigEnvironment] = Query(None, description="Environment"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an existing configuration.
    
    Requires authentication and 'configurations:update' permission.
    """
    require_permissions(current_user, ["configurations:update"])
    
    service = ConfigurationService(db)
    return service.update_configuration(key, config.model_dump(exclude_unset=True), current_user["id"], environment)


@configuration_router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    key: str = Path(..., description="Configuration key"),
    environment: Optional[ConfigEnvironment] = Query(None, description="Environment"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete (deactivate) a configuration.
    
    Requires authentication and 'configurations:delete' permission.
    """
    require_permissions(current_user, ["configurations:delete"])
    
    service = ConfigurationService(db)
    service.delete_configuration(key, current_user["id"], environment)
    return None


@configuration_router.get("/{key}/history", response_model=List[ConfigurationHistoryResponse])
async def get_configuration_history(
    key: str = Path(..., description="Configuration key"),
    environment: Optional[ConfigEnvironment] = Query(None, description="Environment"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get history of a configuration.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    service = ConfigurationService(db)
    return service.get_configuration_history(key, environment, skip, limit)


@configuration_router.post("/bulk", response_model=List[ConfigurationResponse])
async def bulk_update_configurations(
    configs: ConfigurationBulkUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update multiple configurations in a single transaction.
    
    Requires authentication and 'configurations:update' permission.
    """
    require_permissions(current_user, ["configurations:update"])
    
    service = ConfigurationService(db)
    return service.bulk_update_configurations(configs.configurations, current_user["id"])


@configuration_router.get("/groups/", response_model=List[ConfigurationGroupResponse])
async def get_configuration_groups(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all configuration groups.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    service = ConfigurationService(db)
    return service.get_configuration_groups(skip, limit)


@configuration_router.post("/groups/", response_model=ConfigurationGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration_group(
    group: ConfigurationGroupCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new configuration group.
    
    Requires authentication and 'configurations:create' permission.
    """
    require_permissions(current_user, ["configurations:create"])
    
    service = ConfigurationService(db)
    return service.create_configuration_group(group.model_dump(), current_user["id"])


@configuration_router.put("/groups/{group_id}", response_model=ConfigurationGroupResponse)
async def update_configuration_group(
    group_id: str = Path(..., description="Group ID"),
    group: ConfigurationGroupUpdate = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an existing configuration group.
    
    Requires authentication and 'configurations:update' permission.
    """
    require_permissions(current_user, ["configurations:update"])
    
    service = ConfigurationService(db)
    return service.update_configuration_group(group_id, group.model_dump(exclude_unset=True), current_user["id"])


@configuration_router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_group(
    group_id: str = Path(..., description="Group ID"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a configuration group.
    
    Requires authentication and 'configurations:delete' permission.
    """
    require_permissions(current_user, ["configurations:delete"])
    
    service = ConfigurationService(db)
    service.delete_configuration_group(group_id, current_user["id"])
    return None


# Elasticsearch integration routes

@configuration_router.get("/search", response_model=List[ConfigurationSearchResponse])
async def search_configurations(
    query: str = Query(..., description="Search query"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only include active configurations"),
    size: int = Query(100, description="Number of results to return"),
    page: int = Query(1, description="Page number"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    es_service: ConfigurationElasticsearchService = Depends(lambda: ConfigurationElasticsearchService())
):
    """
    Search configurations using Elasticsearch.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    service = ConfigurationService(db, es_service=es_service)
    from_index = (page - 1) * size
    
    filters = {}
    if environment:
        filters["environment"] = environment
    if category:
        filters["category"] = category
    if not active_only:
        filters["is_active"] = None
    
    try:
        results = service.search_configurations(
            query=query,
            filters=filters,
            size=size,
            from_=from_index
        )
        
        return {
            "total": results["total"],
            "items": results["items"],
            "page": page,
            "size": size,
            "query": query
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching configurations: {str(e)}"
        )

@configuration_router.get("/statistics", response_model=ConfigurationStatisticsResponse)
async def get_configuration_statistics(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    es_service: ConfigurationElasticsearchService = Depends(lambda: ConfigurationElasticsearchService())
):
    """
    Get configuration statistics from Elasticsearch.
    
    Requires authentication and 'configurations:read' permission.
    """
    require_permissions(current_user, ["configurations:read"])
    
    service = ConfigurationService(db, es_service=es_service)
    try:
        stats = service.get_configuration_statistics(environment=environment)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting configuration statistics: {str(e)}"
        )

@configuration_router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_configurations_to_elasticsearch(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    es_service: ConfigurationElasticsearchService = Depends(lambda: ConfigurationElasticsearchService())
):
    """
    Sync all configurations to Elasticsearch.
    
    Requires authentication and 'configurations:admin' permission.
    """
    require_permissions(current_user, ["configurations:admin"])
    
    service = ConfigurationService(db, es_service=es_service)
    try:
        result = service.sync_configurations_to_elasticsearch()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing configurations to Elasticsearch: {str(e)}"
        )
