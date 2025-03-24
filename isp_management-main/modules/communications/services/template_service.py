"""
Template service for the Communications module.

This module provides the TemplateService class for handling message and notification templates
in the ISP Management Platform.
"""

import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from redis import Redis

from backend_core.config import settings
from backend_core.cache import get_redis
from modules.communications import models, schemas

# Configure logging
logger = logging.getLogger(__name__)


class TemplateService:
    """Service for handling message and notification templates."""

    @staticmethod
    async def create_template(
        db: Session,
        template_data: schemas.TemplateCreate,
        user_id: int
    ) -> models.Template:
        """
        Create a new template.

        Args:
            db: Database session
            template_data: Template data
            user_id: ID of the user creating the template

        Returns:
            The created template
        """
        # Create the template
        template = models.Template(
            name=template_data.name,
            description=template_data.description,
            template_type=template_data.template_type,
            content=template_data.content,
            variables=template_data.variables,
            created_by=user_id
        )
        
        # Save to database
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # Invalidate cache
        redis = await get_redis()
        if redis:
            cache_key = f"template:{template.id}"
            await redis.delete(cache_key)
            
            # Also invalidate template list cache
            await redis.delete("templates:list")
        
        return template

    @staticmethod
    async def get_template(
        db: Session,
        template_id: int,
        use_cache: bool = True
    ) -> Optional[models.Template]:
        """
        Get a template by ID.

        Args:
            db: Database session
            template_id: ID of the template to retrieve
            use_cache: Whether to use Redis cache

        Returns:
            The template if found, None otherwise
        """
        # Try to get from cache first
        if use_cache:
            redis = await get_redis()
            if redis:
                cache_key = f"template:{template_id}"
                cached_template = await redis.get(cache_key)
                if cached_template:
                    try:
                        template_data = json.loads(cached_template)
                        return models.Template(**template_data)
                    except Exception as e:
                        logger.error(f"Error deserializing cached template: {e}")
        
        # Get from database
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        
        # Cache the result if found
        if template and use_cache:
            redis = await get_redis()
            if redis:
                cache_key = f"template:{template_id}"
                try:
                    template_dict = {
                        "id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "template_type": template.template_type,
                        "content": template.content,
                        "variables": template.variables,
                        "created_by": template.created_by,
                        "created_at": template.created_at.isoformat(),
                        "updated_at": template.updated_at.isoformat() if template.updated_at else None
                    }
                    await redis.set(cache_key, json.dumps(template_dict), ex=3600)  # Cache for 1 hour
                except Exception as e:
                    logger.error(f"Error caching template: {e}")
        
        return template

    @staticmethod
    async def update_template(
        db: Session,
        template_id: int,
        update_data: schemas.TemplateUpdate,
        user_id: int
    ) -> Optional[models.Template]:
        """
        Update a template.

        Args:
            db: Database session
            template_id: ID of the template to update
            update_data: Updated template data
            user_id: ID of the user updating the template

        Returns:
            The updated template if successful, None otherwise
        """
        template = await TemplateService.get_template(db, template_id=template_id, use_cache=False)
        
        # Check if template exists
        if not template:
            return None
        
        # Update fields
        if update_data.name is not None:
            template.name = update_data.name
        if update_data.description is not None:
            template.description = update_data.description
        if update_data.template_type is not None:
            template.template_type = update_data.template_type
        if update_data.content is not None:
            template.content = update_data.content
        if update_data.variables is not None:
            template.variables = update_data.variables
        
        # Update timestamp
        template.updated_at = datetime.utcnow()
        
        # Save changes
        db.commit()
        db.refresh(template)
        
        # Invalidate cache
        redis = await get_redis()
        if redis:
            cache_key = f"template:{template.id}"
            await redis.delete(cache_key)
            
            # Also invalidate template list cache
            await redis.delete("templates:list")
        
        return template

    @staticmethod
    async def delete_template(
        db: Session,
        template_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a template.

        Args:
            db: Database session
            template_id: ID of the template to delete
            user_id: ID of the user deleting the template

        Returns:
            True if successful, False otherwise
        """
        template = await TemplateService.get_template(db, template_id=template_id, use_cache=False)
        
        # Check if template exists
        if not template:
            return False
        
        # Delete template
        db.delete(template)
        db.commit()
        
        # Invalidate cache
        redis = await get_redis()
        if redis:
            cache_key = f"template:{template_id}"
            await redis.delete(cache_key)
            
            # Also invalidate template list cache
            await redis.delete("templates:list")
        
        return True

    @staticmethod
    async def get_templates(
        db: Session,
        template_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[models.Template]:
        """
        Get templates, optionally filtered by type.

        Args:
            db: Database session
            template_type: Filter by template type
            skip: Number of templates to skip (for pagination)
            limit: Maximum number of templates to return
            use_cache: Whether to use Redis cache

        Returns:
            List of templates
        """
        # Try to get from cache first if no filtering
        if use_cache and not template_type and skip == 0 and limit == 100:
            redis = await get_redis()
            if redis:
                cache_key = "templates:list"
                cached_templates = await redis.get(cache_key)
                if cached_templates:
                    try:
                        templates_data = json.loads(cached_templates)
                        return [models.Template(**t) for t in templates_data]
                    except Exception as e:
                        logger.error(f"Error deserializing cached templates: {e}")
        
        # Get from database
        query = db.query(models.Template)
        
        # Filter by type if provided
        if template_type:
            query = query.filter(models.Template.template_type == template_type)
        
        # Order by name
        query = query.order_by(models.Template.name)
        
        # Apply pagination
        templates = query.offset(skip).limit(limit).all()
        
        # Cache the result if no filtering
        if use_cache and not template_type and skip == 0 and limit == 100:
            redis = await get_redis()
            if redis:
                cache_key = "templates:list"
                try:
                    templates_list = []
                    for template in templates:
                        template_dict = {
                            "id": template.id,
                            "name": template.name,
                            "description": template.description,
                            "template_type": template.template_type,
                            "content": template.content,
                            "variables": template.variables,
                            "created_by": template.created_by,
                            "created_at": template.created_at.isoformat(),
                            "updated_at": template.updated_at.isoformat() if template.updated_at else None
                        }
                        templates_list.append(template_dict)
                    
                    await redis.set(cache_key, json.dumps(templates_list), ex=3600)  # Cache for 1 hour
                except Exception as e:
                    logger.error(f"Error caching templates: {e}")
        
        return templates

    @staticmethod
    async def render_template(
        template_content: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Render a template with the provided variables.

        Args:
            template_content: Template content with placeholders
            variables: Dictionary of variables to substitute

        Returns:
            Rendered template content
        """
        rendered_content = template_content
        
        # Simple placeholder substitution
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_content = rendered_content.replace(placeholder, str(value))
        
        return rendered_content
