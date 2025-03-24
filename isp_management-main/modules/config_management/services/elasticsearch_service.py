"""
Elasticsearch service for the Configuration Management Module.

This module provides functionality for indexing and searching configurations in Elasticsearch.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from elasticsearch import Elasticsearch, helpers
from fastapi import HTTPException, status

from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigurationGroup
)

logger = logging.getLogger(__name__)


class ConfigurationElasticsearchService:
    """Service for managing configurations in Elasticsearch."""

    def __init__(self, es_client: Optional[Elasticsearch] = None, index_prefix: str = "isp"):
        """
        Initialize the Elasticsearch service.

        Args:
            es_client: Elasticsearch client
            index_prefix: Prefix for Elasticsearch indices
        """
        self.es_client = es_client
        self.index_prefix = index_prefix
        self.config_index = f"{index_prefix}-configurations"
        self.config_history_index = f"{index_prefix}-configuration-history"
        self.config_group_index = f"{index_prefix}-configuration-groups"
        
        if self.es_client:
            self.create_indices_if_not_exist()

    def create_indices_if_not_exist(self) -> None:
        """Create indices if they don't exist."""
        # Configuration index
        if not self.es_client.indices.exists(index=self.config_index):
            self.es_client.indices.create(
                index=self.config_index,
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "key": {"type": "keyword"},
                            "value": {"type": "object"},
                            "description": {"type": "text"},
                            "environment": {"type": "keyword"},
                            "category": {"type": "keyword"},
                            "is_encrypted": {"type": "boolean"},
                            "version": {"type": "integer"},
                            "is_active": {"type": "boolean"},
                            "created_by": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "updated_by": {"type": "keyword"},
                            "updated_at": {"type": "date"},
                            "elasticsearch_synced": {"type": "boolean"}
                        }
                    }
                }
            )
            logger.info(f"Created index: {self.config_index}")

        # Configuration history index
        if not self.es_client.indices.exists(index=self.config_history_index):
            self.es_client.indices.create(
                index=self.config_history_index,
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "configuration_id": {"type": "keyword"},
                            "key": {"type": "keyword"},
                            "value": {"type": "object"},
                            "environment": {"type": "keyword"},
                            "category": {"type": "keyword"},
                            "is_encrypted": {"type": "boolean"},
                            "version": {"type": "integer"},
                            "action": {"type": "keyword"},
                            "created_by": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "elasticsearch_synced": {"type": "boolean"}
                        }
                    }
                }
            )
            logger.info(f"Created index: {self.config_history_index}")

        # Configuration group index
        if not self.es_client.indices.exists(index=self.config_group_index):
            self.es_client.indices.create(
                index=self.config_group_index,
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "keyword"},
                            "description": {"type": "text"},
                            "created_by": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "updated_by": {"type": "keyword"},
                            "updated_at": {"type": "date"},
                            "elasticsearch_synced": {"type": "boolean"}
                        }
                    }
                }
            )
            logger.info(f"Created index: {self.config_group_index}")

    def index_configuration(self, configuration: Configuration) -> Dict[str, Any]:
        """
        Index a configuration in Elasticsearch.

        Args:
            configuration: Configuration to index

        Returns:
            Elasticsearch response
        """
        try:
            # Convert value to string for indexing if it's not already a string
            value = configuration.value
            if not isinstance(value, str):
                value = json.dumps(value)

            doc = {
                "id": configuration.id,
                "key": configuration.key,
                "value": value,
                "description": configuration.description,
                "environment": configuration.environment.value,
                "category": configuration.category.value,
                "is_encrypted": configuration.is_encrypted,
                "version": configuration.version,
                "is_active": configuration.is_active,
                "created_by": configuration.created_by,
                "created_at": configuration.created_at.isoformat() if configuration.created_at else None,
                "updated_by": configuration.updated_by,
                "updated_at": configuration.updated_at.isoformat() if configuration.updated_at else None,
                "elasticsearch_synced": True
            }

            response = self.es_client.index(
                index=self.config_index,
                id=configuration.id,
                document=doc
            )
            return response
        except Exception as e:
            logger.error(f"Error indexing configuration {configuration.id}: {str(e)}")
            raise

    def index_configuration_history(self, history: ConfigurationHistory) -> Dict[str, Any]:
        """
        Index a configuration history entry in Elasticsearch.

        Args:
            history: Configuration history entry to index

        Returns:
            Elasticsearch response
        """
        try:
            # Convert value to string for indexing if it's not already a string
            value = history.value
            if not isinstance(value, str):
                value = json.dumps(value)

            doc = {
                "id": history.id,
                "configuration_id": history.configuration_id,
                "key": history.key,
                "value": value,
                "environment": history.environment.value,
                "category": history.category.value,
                "is_encrypted": history.is_encrypted,
                "version": history.version,
                "action": history.action,
                "created_by": history.created_by,
                "created_at": history.created_at.isoformat() if history.created_at else None,
                "elasticsearch_synced": True
            }

            response = self.es_client.index(
                index=self.config_history_index,
                id=history.id,
                document=doc
            )
            return response
        except Exception as e:
            logger.error(f"Error indexing configuration history {history.id}: {str(e)}")
            raise

    def index_configuration_group(self, group: ConfigurationGroup, configurations: List[Configuration] = None) -> Dict[str, Any]:
        """
        Index a configuration group in Elasticsearch.

        Args:
            group: Configuration group to index
            configurations: List of configurations in the group

        Returns:
            Elasticsearch response
        """
        try:
            doc = {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "created_by": group.created_by,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_by": group.updated_by,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
                "elasticsearch_synced": True
            }

            if configurations:
                doc["configurations"] = [
                    {"id": config.id, "key": config.key}
                    for config in configurations
                ]

            response = self.es_client.index(
                index=self.config_group_index,
                id=group.id,
                document=doc
            )
            return response
        except Exception as e:
            logger.error(f"Error indexing configuration group {group.id}: {str(e)}")
            raise

    def bulk_index_configurations(self, configurations: List[Configuration]) -> int:
        """
        Bulk index configurations.

        Args:
            configurations: List of configurations to index

        Returns:
            Number of configurations indexed

        Raises:
            Exception: If indexing fails
        """
        try:
            actions = []
            
            for config in configurations:
                action = {
                    "index": {"_id": config.id}
                }
                actions.append(action)
                
                doc = {
                    "id": config.id,
                    "key": config.key,
                    "value": config.value,
                    "description": config.description,
                    "environment": config.environment.value,
                    "category": config.category.value,
                    "is_encrypted": config.is_encrypted,
                    "version": config.version,
                    "is_active": config.is_active,
                    "created_by": config.created_by,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_by": config.updated_by,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                    "elasticsearch_synced": True
                }
                actions.append(doc)
            
            if not actions:
                return 0
            
            # Execute bulk operation
            response = self.es_client.bulk(operations=actions, index=self.config_index)
            
            # Update elasticsearch_synced flag in database
            for config in configurations:
                config.elasticsearch_synced = True
            
            # Count successful operations
            success_count = 0
            for item in response.get("items", []):
                if item.get("index", {}).get("status") in (200, 201):
                    success_count += 1
            
            return success_count
        except Exception as e:
            logger.error(f"Error bulk indexing configurations: {str(e)}")
            raise

    def bulk_index_configuration_history(self, history_items: List[ConfigurationHistory]) -> int:
        """
        Bulk index configuration history.

        Args:
            history_items: List of configuration history items to index

        Returns:
            Number of history items indexed

        Raises:
            Exception: If indexing fails
        """
        try:
            actions = []
            
            for history in history_items:
                action = {
                    "index": {"_id": history.id}
                }
                actions.append(action)
                
                doc = {
                    "id": history.id,
                    "configuration_id": history.configuration_id,
                    "key": history.key,
                    "value": history.value,
                    "environment": history.environment.value,
                    "category": history.category.value,
                    "is_encrypted": history.is_encrypted,
                    "version": history.version,
                    "action": history.action,
                    "created_by": history.created_by,
                    "created_at": history.created_at.isoformat() if history.created_at else None,
                    "elasticsearch_synced": True
                }
                actions.append(doc)
            
            if not actions:
                return 0
            
            # Execute bulk operation
            response = self.es_client.bulk(operations=actions, index=self.config_history_index)
            
            # Update elasticsearch_synced flag in database
            for history in history_items:
                history.elasticsearch_synced = True
            
            # Count successful operations
            success_count = 0
            for item in response.get("items", []):
                if item.get("index", {}).get("status") in (200, 201):
                    success_count += 1
            
            return success_count
        except Exception as e:
            logger.error(f"Error bulk indexing configuration history: {str(e)}")
            raise

    def bulk_index_configuration_groups(self, groups: List[ConfigurationGroup]) -> int:
        """
        Bulk index configuration groups.

        Args:
            groups: List of configuration groups to index

        Returns:
            Number of groups indexed

        Raises:
            Exception: If indexing fails
        """
        try:
            actions = []
            
            for group in groups:
                action = {
                    "index": {"_id": group.id}
                }
                actions.append(action)
                
                doc = {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat() if group.created_at else None,
                    "updated_by": group.updated_by,
                    "updated_at": group.updated_at.isoformat() if group.updated_at else None,
                    "elasticsearch_synced": True
                }
                actions.append(doc)
            
            if not actions:
                return 0
            
            # Execute bulk operation
            response = self.es_client.bulk(operations=actions, index=self.config_group_index)
            
            # Update elasticsearch_synced flag in database
            for group in groups:
                group.elasticsearch_synced = True
            
            # Count successful operations
            success_count = 0
            for item in response.get("items", []):
                if item.get("index", {}).get("status") in (200, 201):
                    success_count += 1
            
            return success_count
        except Exception as e:
            logger.error(f"Error bulk indexing configuration groups: {str(e)}")
            raise

    def search_configurations(self, query: str, filters: Dict[str, Any] = None, 
                             size: int = 100, from_: int = 0) -> Dict[str, Any]:
        """
        Search for configurations in Elasticsearch.

        Args:
            query: Search query
            filters: Optional filters
            size: Number of results to return
            from_: Starting offset

        Returns:
            Search results
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["key^3", "value^2", "description"]
                                }
                            }
                        ],
                        "filter": []
                    }
                },
                "size": size,
                "from": from_
            }

            if filters:
                for key, value in filters.items():
                    if value is not None:
                        search_body["query"]["bool"]["filter"].append({"term": {key: value}})

            results = self.es_client.search(
                index=self.config_index,
                body=search_body
            )

            return {
                "total": results["hits"]["total"]["value"],
                "results": [hit["_source"] for hit in results["hits"]["hits"]]
            }
        except Exception as e:
            logger.error(f"Error searching configurations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching configurations: {str(e)}"
            )

    def search_configuration_history(self, key: str = None, configuration_id: str = None,
                                    size: int = 100, from_: int = 0) -> Dict[str, Any]:
        """
        Search for configuration history entries in Elasticsearch.

        Args:
            key: Configuration key
            configuration_id: Configuration ID
            size: Number of results to return
            from_: Starting offset

        Returns:
            Search results
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [],
                        "filter": []
                    }
                },
                "size": size,
                "from": from_,
                "sort": [{"created_at": {"order": "desc"}}]
            }

            if key:
                search_body["query"]["bool"]["filter"].append({"term": {"key": key}})
            
            if configuration_id:
                search_body["query"]["bool"]["filter"].append({"term": {"configuration_id": configuration_id}})

            results = self.es_client.search(
                index=self.config_history_index,
                body=search_body
            )

            return {
                "total": results["hits"]["total"]["value"],
                "results": [hit["_source"] for hit in results["hits"]["hits"]]
            }
        except Exception as e:
            logger.error(f"Error searching configuration history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching configuration history: {str(e)}"
            )

    def search_configuration_groups(self, query: str = None, size: int = 100, from_: int = 0) -> Dict[str, Any]:
        """
        Search for configuration groups in Elasticsearch.

        Args:
            query: Search query
            size: Number of results to return
            from_: Starting offset

        Returns:
            Search results
        """
        try:
            search_body = {
                "size": size,
                "from": from_
            }

            if query:
                search_body["query"] = {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "description"]
                    }
                }
            else:
                search_body["query"] = {"match_all": {}}

            results = self.es_client.search(
                index=self.config_group_index,
                body=search_body
            )

            return {
                "total": results["hits"]["total"]["value"],
                "results": [hit["_source"] for hit in results["hits"]["hits"]]
            }
        except Exception as e:
            logger.error(f"Error searching configuration groups: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching configuration groups: {str(e)}"
            )

    def delete_configuration(self, configuration_id: str) -> bool:
        """
        Delete a configuration from Elasticsearch.

        Args:
            configuration_id: ID of the configuration to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.es_client.delete(
                index=self.config_index,
                id=configuration_id
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting configuration {configuration_id}: {str(e)}")
            return False

    def delete_configuration_group(self, group_id: str) -> bool:
        """
        Delete a configuration group from Elasticsearch.

        Args:
            group_id: ID of the configuration group to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.es_client.delete(
                index=self.config_group_index,
                id=group_id
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting configuration group {group_id}: {str(e)}")
            return False

    def sync_configurations(self, configurations: List[Configuration]) -> int:
        """
        Synchronize configurations with Elasticsearch.

        Args:
            configurations: List of configurations to synchronize

        Returns:
            Number of configurations synchronized
        """
        return self.bulk_index_configurations(configurations)

    def sync_configuration_history(self, history_entries: List[ConfigurationHistory]) -> int:
        """
        Synchronize configuration history entries with Elasticsearch.

        Args:
            history_entries: List of configuration history entries to synchronize

        Returns:
            Number of history entries synchronized
        """
        return self.bulk_index_configuration_history(history_entries)

    def get_configuration_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configurations.
        
        Returns:
            Dictionary with configuration statistics
        """
        try:
            # Get total number of configurations
            config_stats = self.es_client.count(index=self.config_index)
            total_count = config_stats.get("count", 0)
            
            # Get counts for aggregations
            aggs_query = {
                "size": 0,
                "aggs": {
                    "by_environment": {
                        "terms": {
                            "field": "environment",
                            "size": 10
                        }
                    },
                    "by_category": {
                        "terms": {
                            "field": "category",
                            "size": 10
                        }
                    },
                    "by_active": {
                        "terms": {
                            "field": "is_active",
                            "size": 2
                        }
                    },
                    "by_encrypted": {
                        "terms": {
                            "field": "is_encrypted",
                            "size": 2
                        }
                    }
                }
            }
            
            aggs_results = self.es_client.search(index=self.config_index, body=aggs_query)
            
            # Process active/inactive counts
            active_count = 0
            inactive_count = 0
            for bucket in aggs_results.get("aggregations", {}).get("by_active", {}).get("buckets", []):
                if bucket["key"] == 1:
                    active_count = bucket["doc_count"]
                else:
                    inactive_count = bucket["doc_count"]
            
            # Process encrypted count
            encrypted_count = 0
            for bucket in aggs_results.get("aggregations", {}).get("by_encrypted", {}).get("buckets", []):
                if bucket["key"] == 1:
                    encrypted_count = bucket["doc_count"]
            
            # Process environment breakdown
            env_stats = {}
            for bucket in aggs_results.get("aggregations", {}).get("by_environment", {}).get("buckets", []):
                env_stats[bucket["key"]] = bucket["doc_count"]
            
            # Process category breakdown
            cat_stats = {}
            for bucket in aggs_results.get("aggregations", {}).get("by_category", {}).get("buckets", []):
                cat_stats[bucket["key"]] = bucket["doc_count"]
            
            return {
                "total_count": total_count,
                "active_count": active_count,
                "inactive_count": inactive_count,
                "encrypted_count": encrypted_count,
                "by_environment": env_stats,
                "by_category": cat_stats
            }
        except Exception as e:
            logger.error(f"Error getting configuration statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting configuration statistics: {str(e)}"
            )

    def get_configuration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about configurations.

        Returns:
            Dictionary with configuration statistics
        """
        try:
            # Get total count
            count_query = {
                "query": {"match_all": {}}
            }
            count_result = self.es_client.count(index=self.config_index, body=count_query)
            total_count = count_result["count"]

            # Get counts by category
            category_query = {
                "size": 0,
                "aggs": {
                    "categories": {
                        "terms": {
                            "field": "category",
                            "size": 20
                        }
                    }
                }
            }
            category_result = self.es_client.search(index=self.config_index, body=category_query)
            categories = {
                bucket["key"]: bucket["doc_count"]
                for bucket in category_result["aggregations"]["categories"]["buckets"]
            }

            # Get counts by environment
            env_query = {
                "size": 0,
                "aggs": {
                    "environments": {
                        "terms": {
                            "field": "environment",
                            "size": 10
                        }
                    }
                }
            }
            env_result = self.es_client.search(index=self.config_index, body=env_query)
            environments = {
                bucket["key"]: bucket["doc_count"]
                for bucket in env_result["aggregations"]["environments"]["buckets"]
            }

            # Get counts by active status
            active_query = {
                "size": 0,
                "aggs": {
                    "active_status": {
                        "terms": {
                            "field": "is_active",
                            "size": 2
                        }
                    }
                }
            }
            active_result = self.es_client.search(index=self.config_index, body=active_query)
            active_status = {
                "active": 0,
                "inactive": 0
            }
            for bucket in active_result["aggregations"]["active_status"]["buckets"]:
                if bucket["key"] == 1:  # True
                    active_status["active"] = bucket["doc_count"]
                else:  # False
                    active_status["inactive"] = bucket["doc_count"]

            # Get recent changes
            recent_query = {
                "query": {"match_all": {}},
                "size": 10,
                "sort": [{"updated_at": {"order": "desc"}}]
            }
            recent_result = self.es_client.search(index=self.config_index, body=recent_query)
            recent_changes = [hit["_source"] for hit in recent_result["hits"]["hits"]]

            return {
                "total_count": total_count,
                "by_category": categories,
                "by_environment": environments,
                "by_status": active_status,
                "recent_changes": recent_changes
            }
        except Exception as e:
            logger.error(f"Error getting configuration statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting configuration statistics: {str(e)}"
            )
