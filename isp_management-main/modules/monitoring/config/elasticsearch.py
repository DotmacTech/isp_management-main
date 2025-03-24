"""
Elasticsearch configuration for the Monitoring Module.

This module defines the configuration settings for Elasticsearch integration.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ElasticsearchConfig(BaseModel):
    """
    Configuration settings for Elasticsearch integration.
    """
    enabled: bool = Field(
        default=False,
        description="Enable/disable Elasticsearch integration"
    )
    hosts: List[str] = Field(
        default=["http://localhost:9200"],
        description="Elasticsearch hosts"
    )
    username: Optional[str] = Field(
        default=None,
        description="Username for Elasticsearch authentication"
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for Elasticsearch authentication"
    )
    verify_certs: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )
    log_index_prefix: str = Field(
        default="isp-logs",
        description="Prefix for log indices"
    )
    metric_index_prefix: str = Field(
        default="isp-metrics",
        description="Prefix for metric indices"
    )
    index_date_format: str = Field(
        default="YYYY.MM.dd",
        description="Date format for index names"
    )
    number_of_shards: int = Field(
        default=1,
        description="Number of shards for indices"
    )
    number_of_replicas: int = Field(
        default=0,
        description="Number of replicas for indices"
    )
    sync_batch_size: int = Field(
        default=100,
        description="Number of records to sync in each batch"
    )
    
    @validator("hosts", pre=True)
    def parse_hosts(cls, v):
        """Parse hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v


def load_elasticsearch_config() -> ElasticsearchConfig:
    """
    Load Elasticsearch configuration from environment variables.
    
    Returns:
        ElasticsearchConfig: Elasticsearch configuration
    """
    return ElasticsearchConfig(
        enabled=os.environ.get("ELASTICSEARCH_ENABLED", "false").lower() in ("true", "1", "yes"),
        hosts=os.environ.get("ELASTICSEARCH_HOSTS", "http://localhost:9200"),
        username=os.environ.get("ELASTICSEARCH_USERNAME"),
        password=os.environ.get("ELASTICSEARCH_PASSWORD"),
        verify_certs=os.environ.get("ELASTICSEARCH_VERIFY_CERTS", "true").lower() in ("true", "1", "yes"),
        log_index_prefix=os.environ.get("ELASTICSEARCH_LOG_INDEX_PREFIX", "isp-logs"),
        metric_index_prefix=os.environ.get("ELASTICSEARCH_METRIC_INDEX_PREFIX", "isp-metrics"),
        index_date_format=os.environ.get("ELASTICSEARCH_INDEX_DATE_FORMAT", "YYYY.MM.dd"),
        number_of_shards=int(os.environ.get("ELASTICSEARCH_NUMBER_OF_SHARDS", "1")),
        number_of_replicas=int(os.environ.get("ELASTICSEARCH_NUMBER_OF_REPLICAS", "0")),
        sync_batch_size=int(os.environ.get("ELASTICSEARCH_SYNC_BATCH_SIZE", "100"))
    )


# Create a singleton instance
elasticsearch_config = load_elasticsearch_config()
