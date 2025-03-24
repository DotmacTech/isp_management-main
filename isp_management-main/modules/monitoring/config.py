"""
Configuration settings for the Monitoring Module.

This module provides configuration settings for logging, metrics, alerts,
and other monitoring-related functionality.
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, Field, validator
import json


class ElasticsearchSettings(BaseSettings):
    """Elasticsearch configuration settings."""
    
    enabled: bool = Field(
        default=False,
        env="ELASTICSEARCH_ENABLED",
        description="Enable Elasticsearch integration"
    )
    
    hosts: List[str] = Field(
        default=["http://localhost:9200"],
        env="ELASTICSEARCH_HOSTS",
        description="Elasticsearch hosts"
    )
    
    username: Optional[str] = Field(
        default=None,
        env="ELASTICSEARCH_USERNAME",
        description="Elasticsearch username"
    )
    
    password: Optional[str] = Field(
        default=None,
        env="ELASTICSEARCH_PASSWORD",
        description="Elasticsearch password"
    )
    
    verify_certs: bool = Field(
        default=True,
        env="ELASTICSEARCH_VERIFY_CERTS",
        description="Verify SSL certificates"
    )
    
    log_index_prefix: str = Field(
        default="isp-logs",
        env="ELASTICSEARCH_LOG_INDEX_PREFIX",
        description="Prefix for log indices"
    )
    
    metric_index_prefix: str = Field(
        default="isp-metrics",
        env="ELASTICSEARCH_METRIC_INDEX_PREFIX",
        description="Prefix for metric indices"
    )
    
    index_date_format: str = Field(
        default="%Y.%m.%d",
        env="ELASTICSEARCH_INDEX_DATE_FORMAT",
        description="Date format for index names"
    )
    
    number_of_shards: int = Field(
        default=1,
        env="ELASTICSEARCH_NUMBER_OF_SHARDS",
        description="Number of shards for indices"
    )
    
    number_of_replicas: int = Field(
        default=1,
        env="ELASTICSEARCH_NUMBER_OF_REPLICAS",
        description="Number of replicas for indices"
    )
    
    @validator("hosts", pre=True)
    def parse_hosts(cls, v):
        """Parse hosts from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        env="LOGGING_LEVEL",
        description="Default logging level"
    )
    
    retention_days: int = Field(
        default=90,
        env="LOGGING_RETENTION_DAYS",
        description="Number of days to retain logs"
    )
    
    elasticsearch: ElasticsearchSettings = Field(
        default_factory=ElasticsearchSettings,
        description="Elasticsearch settings"
    )
    
    sensitive_fields: List[str] = Field(
        default=[
            "password", "token", "secret", "key", "authorization",
            "credit_card", "ssn", "social_security", "auth"
        ],
        env="LOGGING_SENSITIVE_FIELDS",
        description="Sensitive fields to redact in logs"
    )
    
    @validator("sensitive_fields", pre=True)
    def parse_sensitive_fields(cls, v):
        """Parse sensitive fields from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v


class MetricsSettings(BaseSettings):
    """Metrics configuration settings."""
    
    retention_days: int = Field(
        default=30,
        env="METRICS_RETENTION_DAYS",
        description="Number of days to retain metrics"
    )
    
    collection_interval: int = Field(
        default=60,
        env="METRICS_COLLECTION_INTERVAL",
        description="Interval in seconds for collecting metrics"
    )
    
    system_metrics_enabled: bool = Field(
        default=True,
        env="METRICS_SYSTEM_ENABLED",
        description="Enable system metrics collection"
    )
    
    network_metrics_enabled: bool = Field(
        default=True,
        env="METRICS_NETWORK_ENABLED",
        description="Enable network metrics collection"
    )
    
    service_metrics_enabled: bool = Field(
        default=True,
        env="METRICS_SERVICE_ENABLED",
        description="Enable service metrics collection"
    )
    
    customer_metrics_enabled: bool = Field(
        default=True,
        env="METRICS_CUSTOMER_ENABLED",
        description="Enable customer metrics collection"
    )


class AlertSettings(BaseSettings):
    """Alert configuration settings."""
    
    enabled: bool = Field(
        default=True,
        env="ALERTS_ENABLED",
        description="Enable alert system"
    )
    
    evaluation_interval: int = Field(
        default=60,
        env="ALERTS_EVALUATION_INTERVAL",
        description="Interval in seconds for evaluating alert conditions"
    )
    
    notification_channels: List[str] = Field(
        default=["redis"],
        env="ALERTS_NOTIFICATION_CHANNELS",
        description="Channels for alert notifications (redis, email, slack, webhook)"
    )
    
    default_severity: str = Field(
        default="WARNING",
        env="ALERTS_DEFAULT_SEVERITY",
        description="Default severity for alerts"
    )
    
    @validator("notification_channels", pre=True)
    def parse_notification_channels(cls, v):
        """Parse notification channels from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v


class DashboardSettings(BaseSettings):
    """Dashboard configuration settings."""
    
    enabled: bool = Field(
        default=True,
        env="DASHBOARDS_ENABLED",
        description="Enable dashboards"
    )
    
    default_refresh_interval: int = Field(
        default=60,
        env="DASHBOARDS_DEFAULT_REFRESH_INTERVAL",
        description="Default refresh interval in seconds for dashboards"
    )
    
    max_widgets_per_dashboard: int = Field(
        default=20,
        env="DASHBOARDS_MAX_WIDGETS",
        description="Maximum number of widgets per dashboard"
    )


class MonitoringSettings(BaseSettings):
    """Monitoring module configuration settings."""
    
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings,
        description="Logging settings"
    )
    
    metrics: MetricsSettings = Field(
        default_factory=MetricsSettings,
        description="Metrics settings"
    )
    
    alerts: AlertSettings = Field(
        default_factory=AlertSettings,
        description="Alert settings"
    )
    
    dashboards: DashboardSettings = Field(
        default_factory=DashboardSettings,
        description="Dashboard settings"
    )
    
    health_check_services: Dict[str, str] = Field(
        default={
            "api_gateway": "http://localhost:8000/health",
            "database": "postgresql://localhost:5432",
            "redis": "redis://localhost:6379",
            "elasticsearch": "http://localhost:9200"
        },
        env="MONITORING_HEALTH_CHECK_SERVICES",
        description="Services to check in health checks"
    )
    
    @validator("health_check_services", pre=True)
    def parse_health_check_services(cls, v):
        """Parse health check services from string or dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Not valid JSON, return empty dict
                return {}
        return v
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "MONITORING_"
        env_nested_delimiter = "__"
        case_sensitive = False


# Create settings instance
settings = MonitoringSettings()
