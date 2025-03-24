"""
Configuration settings for the Monitoring Module.

This module provides configuration settings for logging, metrics, alerts,
and other monitoring-related functionality.
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class ElasticsearchSettings(BaseSettings):
    """Elasticsearch configuration settings."""
    
    enabled: bool = Field(
        default=False,
        description="Enable Elasticsearch integration"
    )
    
    hosts: List[str] = Field(
        default=["http://localhost:9200"],
        description="Elasticsearch hosts"
    )
    
    username: Optional[str] = Field(
        default=None,
        description="Elasticsearch username"
    )
    
    password: Optional[str] = Field(
        default=None,
        description="Elasticsearch password"
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
    
    alert_index_prefix: str = Field(
        default="isp-alerts",
        description="Prefix for alert indices"
    )
    
    index_settings: Dict[str, Any] = Field(
        default={
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "5s"
        },
        description="Default settings for indices"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="ELASTICSEARCH_",
        env_file=".env",
        extra="ignore"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        description="Default logging level"
    )
    
    retention_days: int = Field(
        default=90,
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
        description="Sensitive fields to redact in logs"
    )
    
    @field_validator("sensitive_fields", mode="before")
    @classmethod
    def parse_sensitive_fields(cls, v):
        """Parse sensitive fields from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v
    
    model_config = SettingsConfigDict(
        env_prefix="LOGGING_",
        env_file=".env",
        extra="ignore"
    )


class MetricsSettings(BaseSettings):
    """Metrics configuration settings."""
    
    retention_days: int = Field(
        default=30,
        description="Number of days to retain metrics"
    )
    
    collection_interval: int = Field(
        default=60,
        description="Interval in seconds for collecting metrics"
    )
    
    system_metrics_enabled: bool = Field(
        default=True,
        description="Enable system metrics collection"
    )
    
    network_metrics_enabled: bool = Field(
        default=True,
        description="Enable network metrics collection"
    )
    
    service_metrics_enabled: bool = Field(
        default=True,
        description="Enable service metrics collection"
    )
    
    customer_metrics_enabled: bool = Field(
        default=True,
        description="Enable customer metrics collection"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="METRICS_",
        env_file=".env",
        extra="ignore"
    )


class AlertSettings(BaseSettings):
    """Alert configuration settings."""
    
    enabled: bool = Field(
        default=True,
        description="Enable alert system"
    )
    
    evaluation_interval: int = Field(
        default=60,
        description="Interval in seconds for evaluating alert conditions"
    )
    
    notification_channels: List[str] = Field(
        default=["redis"],
        description="Channels for alert notifications (redis, email, slack, webhook)"
    )
    
    default_severity: str = Field(
        default="WARNING",
        description="Default severity for alerts"
    )
    
    @field_validator("notification_channels", mode="before")
    @classmethod
    def parse_notification_channels(cls, v):
        """Parse notification channels from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v
    
    model_config = SettingsConfigDict(
        env_prefix="ALERTS_",
        env_file=".env",
        extra="ignore"
    )


class DashboardSettings(BaseSettings):
    """Dashboard configuration settings."""
    
    enabled: bool = Field(
        default=True,
        description="Enable dashboards"
    )
    
    default_refresh_interval: int = Field(
        default=60,
        description="Default refresh interval in seconds for dashboards"
    )
    
    max_widgets_per_dashboard: int = Field(
        default=20,
        description="Maximum number of widgets per dashboard"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="DASHBOARDS_",
        env_file=".env",
        extra="ignore"
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
        description="Services to check in health checks"
    )
    
    @field_validator("health_check_services", mode="before")
    @classmethod
    def parse_health_check_services(cls, v):
        """Parse health check services from string or dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Try to parse as comma-separated key-value pairs
                result = {}
                pairs = v.split(",")
                for pair in pairs:
                    if ":" in pair:
                        key, value = pair.split(":", 1)
                        result[key.strip()] = value.strip()
                return result
        return v
    
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        env_file=".env",
        extra="ignore"
    )


# Create settings instance
settings = MonitoringSettings()
