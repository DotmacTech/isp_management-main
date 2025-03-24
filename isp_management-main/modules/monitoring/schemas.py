from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"

class MetricType(str, Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_BANDWIDTH = "network_bandwidth"
    LATENCY = "latency"
    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    CONCURRENT_USERS = "concurrent_users"
    QUEUE_SIZE = "queue_size"
    DATABASE_CONNECTIONS = "database_connections"
    CACHE_HIT_RATE = "cache_hit_rate"
    CUSTOM = "custom"

# Base schemas for common fields
class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class ServiceLogBase(BaseModel):
    service_name: str
    log_level: LogLevel
    message: str
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_id: Optional[int] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    response_status: Optional[int] = None
    execution_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ServiceLogCreate(ServiceLogBase):
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ServiceLogResponse(ServiceLogBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SystemMetricBase(BaseModel):
    service_name: str
    host_name: str
    metric_type: MetricType
    value: float
    unit: str
    tags: Optional[Dict[str, str]] = None
    sampling_rate: Optional[float] = 1.0

class SystemMetricCreate(SystemMetricBase):
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SystemMetricResponse(SystemMetricBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class LogRetentionPolicyBase(BaseModel):
    service_name: str
    log_level: LogLevel
    retention_days: int
    is_active: bool = True

class LogRetentionPolicyCreate(LogRetentionPolicyBase, TimestampMixin):
    created_by: int

class LogRetentionPolicyResponse(LogRetentionPolicyBase, TimestampMixin):
    id: int
    created_by: int
    
    model_config = ConfigDict(from_attributes=True)

class AlertConfigurationBase(BaseModel):
    name: str
    description: Optional[str] = None
    service_name: str
    condition_type: str  # threshold, pattern, anomaly
    severity: AlertSeverity = AlertSeverity.WARNING
    is_active: bool = True
    cooldown_minutes: int = 15
    notification_channels: Dict[str, Any] = Field(default_factory=dict)
    
    # Conditional fields based on condition_type
    metric_type: Optional[MetricType] = None
    log_level: Optional[LogLevel] = None
    threshold_value: Optional[float] = None
    pattern: Optional[str] = None
    comparison_operator: Optional[str] = None

    @model_validator(mode='after')
    def validate_condition_fields(self) -> 'AlertConfigurationBase':
        if self.condition_type == 'threshold':
            if not self.metric_type or self.threshold_value is None or not self.comparison_operator:
                raise ValueError("Threshold conditions require metric_type, threshold_value, and comparison_operator")
        elif self.condition_type == 'pattern':
            if not self.log_level or not self.pattern:
                raise ValueError("Pattern conditions require log_level and pattern")
        elif self.condition_type == 'anomaly':
            if not self.metric_type:
                raise ValueError("Anomaly conditions require metric_type")
        return self

class AlertConfigurationCreate(AlertConfigurationBase, TimestampMixin):
    created_by: int

class AlertConfigurationResponse(AlertConfigurationBase, TimestampMixin):
    id: int
    created_by: int
    
    model_config = ConfigDict(from_attributes=True)

class AlertHistoryBase(BaseModel):
    configuration_id: int
    status: AlertStatus = AlertStatus.ACTIVE
    message: str
    triggered_value: Optional[float] = None
    matched_pattern: Optional[str] = None
    source_log_id: Optional[int] = None
    source_metric_id: Optional[int] = None
    notification_sent: bool = False

class AlertHistoryCreate(AlertHistoryBase):
    triggered_at: datetime = Field(default_factory=datetime.utcnow)

class AlertHistoryUpdate(BaseModel):
    status: AlertStatus
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolution_notes: Optional[str] = None

class AlertHistoryResponse(AlertHistoryBase):
    id: int
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class DashboardWidgetBase(BaseModel):
    widget_type: str
    title: str
    data_source: str
    query: str
    refresh_interval_seconds: int = 60
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    visualization_options: Dict[str, Any] = Field(default_factory=dict)

class DashboardWidgetCreate(DashboardWidgetBase):
    pass

class DashboardWidgetResponse(DashboardWidgetBase):
    id: int
    dashboard_id: int
    
    model_config = ConfigDict(from_attributes=True)

class DashboardConfigurationBase(BaseModel):
    name: str
    description: Optional[str] = None
    layout: Dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False

class DashboardConfigurationCreate(DashboardConfigurationBase, TimestampMixin):
    created_by: int
    widgets: Optional[List[DashboardWidgetCreate]] = None

class DashboardConfigurationResponse(DashboardConfigurationBase, TimestampMixin):
    id: int
    created_by: int
    widgets: List[DashboardWidgetResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# Specialized schemas for dashboard metrics and system health
class DashboardMetric(BaseModel):
    name: str
    value: float
    unit: str
    change_percent: Optional[float] = None
    trend: Optional[str] = None

class SystemHealthCheck(BaseModel):
    status: str
    components: Dict[str, str]
    last_updated: datetime

# Health check schemas
class ComponentStatus(BaseModel):
    """
    Schema for component status in health check response.
    """
    status: str  # healthy, warning, unhealthy
    response_time: Optional[float] = None  # in milliseconds
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class HealthCheckResponse(BaseModel):
    """
    Schema for health check response.
    """
    timestamp: datetime
    overall_status: str  # healthy, degraded, unhealthy
    components: Dict[str, ComponentStatus]
    
    class Config:
        orm_mode = True


class ServiceHealthReport(BaseModel):
    """
    Schema for service health report.
    """
    service_name: str
    health_info: Dict[str, Any]
    
    class Config:
        orm_mode = True

# Search and filtering schemas
class LogSearchParams(BaseModel):
    service_names: Optional[List[str]] = None
    log_levels: Optional[List[LogLevel]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[int] = None
    message_contains: Optional[str] = None
    request_path: Optional[str] = None
    limit: int = 100
    offset: int = 0

class MetricSearchParams(BaseModel):
    service_names: Optional[List[str]] = None
    host_names: Optional[List[str]] = None
    metric_types: Optional[List[MetricType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None
    aggregation: Optional[str] = None  # avg, sum, min, max, count
    group_by: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0

class AlertSearchParams(BaseModel):
    service_names: Optional[List[str]] = None
    severities: Optional[List[AlertSeverity]] = None
    statuses: Optional[List[AlertStatus]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0

# Pagination response
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    limit: int
    offset: int
