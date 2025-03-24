"""
Celery tasks for the Configuration Management Module.

This module defines Celery tasks for background processing related to
configuration management, such as synchronizing configurations to Elasticsearch.
"""

import logging
from celery import shared_task
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigurationGroup
)
from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService
from modules.core.database import get_db
from modules.config_management.services.configuration_service import ConfigurationService


logger = logging.getLogger(__name__)


@shared_task(name="sync_configurations_to_elasticsearch")
def sync_configurations_to_elasticsearch() -> dict:
    """
    Sync all configurations, configuration history, and configuration groups to Elasticsearch.
    
    Returns:
        Dictionary with counts of indexed items
    """
    db = next(get_db())
    es_service = ConfigurationElasticsearchService()
    config_service = ConfigurationService(db=db, es_service=es_service)
    
    try:
        # Get all configurations that haven't been synced or have been updated
        configurations = db.query(Configuration).filter(
            or_(
                Configuration.elasticsearch_synced == False,
                and_(
                    Configuration.updated_at != None,
                    Configuration.updated_at > Configuration.created_at
                )
            )
        ).all()
        
        # Get all configuration history items that haven't been synced
        history_items = db.query(ConfigurationHistory).filter(
            ConfigurationHistory.elasticsearch_synced == False
        ).all()
        
        # Get all configuration groups that haven't been synced or have been updated
        groups = db.query(ConfigurationGroup).filter(
            or_(
                ConfigurationGroup.elasticsearch_synced == False,
                and_(
                    ConfigurationGroup.updated_at != None,
                    ConfigurationGroup.updated_at > ConfigurationGroup.created_at
                )
            )
        ).all()
        
        # Bulk index configurations
        config_count = es_service.bulk_index_configurations(configurations)
        
        # Bulk index configuration history
        history_count = es_service.bulk_index_configuration_history(history_items)
        
        # Bulk index configuration groups
        group_count = es_service.bulk_index_configuration_groups(groups)
        
        # Commit the changes to the database
        db.commit()
        
        logger.info(
            f"Successfully synchronized configurations to Elasticsearch: "
            f"{config_count} configurations, "
            f"{history_count} history items, "
            f"{group_count} groups"
        )
        
        return {
            "configurations_indexed": config_count,
            "history_items_indexed": history_count,
            "groups_indexed": group_count
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error synchronizing configurations to Elasticsearch: {str(e)}")
        raise e
    finally:
        db.close()


@shared_task(name="cleanup_configuration_history")
def cleanup_configuration_history(days: int = 90) -> int:
    """
    Clean up old configuration history entries.
    
    Args:
        days: Number of days to keep history for
        
    Returns:
        Number of history entries deleted
    """
    db = next(get_db())
    es_service = ConfigurationElasticsearchService()
    config_service = ConfigurationService(db=db, es_service=es_service)
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get IDs of history entries to delete
        history_ids = [
            row[0] for row in db.query(ConfigurationHistory.id).filter(
                ConfigurationHistory.created_at < cutoff_date
            ).all()
        ]
        
        # Delete from Elasticsearch
        for history_id in history_ids:
            es_service.delete_configuration_history(history_id)
        
        # Delete from database
        deleted_count = db.query(ConfigurationHistory).filter(
            ConfigurationHistory.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Successfully cleaned up {deleted_count} configuration history entries")
        
        return deleted_count
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up configuration history: {str(e)}")
        raise e
    finally:
        db.close()
