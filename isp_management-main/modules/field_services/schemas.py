"""
Pydantic schemas for the Field Services Module.

These schemas define the data structures for job scheduling, technician management,
route optimization, and inventory management.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# Enums for validation
class JobStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class JobPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobType(str, Enum):
    INSTALLATION = "installation"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"
    UPGRADE = "upgrade"
    INSPECTION = "inspection"
    TROUBLESHOOTING = "troubleshooting"


class TechnicianStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    BUSY = "busy"
    AVAILABLE = "available"


class InventoryStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    DEFECTIVE = "defective"
    UNDER_REPAIR = "under_repair"
    DEPLETED = "depleted"


class InventoryTransactionType(str, Enum):
    ALLOCATION = "allocation"
    RETURN = "return"
    USAGE = "usage"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    INITIAL = "initial"


class NotificationType(str, Enum):
    JOB_ASSIGNMENT = "job_assignment"
    JOB_UPDATE = "job_update"
    JOB_COMPLETION = "job_completion"
    SLA_ALERT = "sla_alert"
    INVENTORY_ALERT = "inventory_alert"
    SYSTEM_NOTIFICATION = "system_notification"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InventoryTypeEnum(str, Enum):
    EQUIPMENT = "equipment"
    TOOL = "tool"
    PART = "part"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    SOFTWARE = "software"


# Base schemas
class TechnicianBase(BaseModel):
    name: str
    email: str
    phone: str
    skills: List[str]
    certification_level: str
    region: str
    max_jobs_per_day: int = Field(5, ge=1, le=20)


class TechnicianCreate(TechnicianBase):
    user_id: Optional[int] = None
    status: TechnicianStatus = TechnicianStatus.ACTIVE
    home_location_lat: float
    home_location_lon: float


class TechnicianUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None
    certification_level: Optional[str] = None
    region: Optional[str] = None
    status: Optional[TechnicianStatus] = None
    max_jobs_per_day: Optional[int] = Field(None, ge=1, le=20)
    home_location_lat: Optional[float] = None
    home_location_lon: Optional[float] = None


class TechnicianResponse(TechnicianBase):
    id: int
    user_id: Optional[int]
    status: TechnicianStatus
    home_location_lat: float
    home_location_lon: float
    current_location_lat: Optional[float]
    current_location_lon: Optional[float]
    last_location_update: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class TechnicianList(BaseModel):
    items: List[TechnicianResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


# Notification schemas
class TechnicianNotificationBase(BaseModel):
    technician_id: int
    title: str
    message: str
    notification_type: Union[NotificationType, str]
    priority: Union[NotificationPriority, str] = NotificationPriority.MEDIUM
    job_id: Optional[int] = None
    expiry_date: Optional[datetime] = None

    @field_validator('notification_type', mode='before')
    def validate_notification_type(cls, v):
        if isinstance(v, str):
            try:
                return NotificationType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid notification type: {v}")
        return v

    @field_validator('priority', mode='before')
    def validate_priority(cls, v):
        if isinstance(v, str):
            try:
                return NotificationPriority(v.lower())
            except ValueError:
                raise ValueError(f"Invalid notification priority: {v}")
        return v


class TechnicianNotificationCreate(TechnicianNotificationBase):
    pass


class TechnicianNotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[Union[NotificationPriority, str]] = None
    is_read: Optional[bool] = None
    expiry_date: Optional[datetime] = None


class TechnicianNotificationResponse(TechnicianNotificationBase):
    id: int
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class TechnicianNotificationList(BaseModel):
    items: List[TechnicianNotificationResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


# Mobile schemas
class MobileJobUpdate(BaseModel):
    job_id: int
    status: Optional[str] = None
    notes: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MobileLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class MobileInventoryUsage(BaseModel):
    inventory_id: int
    quantity: int = Field(..., gt=0)
    job_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MobileSyncRequest(BaseModel):
    technician_id: int
    last_sync_time: Optional[datetime] = None
    device_id: str
    app_version: str
    job_updates: Optional[List[MobileJobUpdate]] = []
    location_update: Optional[MobileLocationUpdate] = None
    inventory_usage: Optional[List[MobileInventoryUsage]] = []


class MobileSyncResponse(BaseModel):
    technician_id: int
    sync_time: datetime
    sync_hash: str
    jobs: List[Dict[str, Any]]
    notifications: List[Dict[str, Any]]
    inventory: List[Dict[str, Any]]
    updated_job_ids: List[int]
    links: Optional[List[Dict[str, str]]] = None


# Job schemas
class JobFilterParams(BaseModel):
    status: Optional[str] = None
    technician_id: Optional[int] = None
    customer_id: Optional[int] = None
    priority: Optional[str] = None
    job_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    location_radius_km: Optional[float] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    required_skills: Optional[List[str]] = None
    sla_status: Optional[str] = None


class JobBase(BaseModel):
    title: str
    description: str
    customer_id: int
    job_type: JobType
    priority: JobPriority = JobPriority.MEDIUM
    estimated_duration_minutes: int = Field(..., ge=15, le=480)
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    location_lat: float
    location_lon: float
    location_address: str
    required_skills: List[str] = []
    required_equipment: List[str] = []


class JobCreate(JobBase):
    technician_id: Optional[int] = None
    status: JobStatus = JobStatus.PENDING
    sla_deadline: Optional[datetime] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    technician_id: Optional[int] = None
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_address: Optional[str] = None
    required_skills: Optional[List[str]] = None
    required_equipment: Optional[List[str]] = None
    notes: Optional[str] = None
    sla_deadline: Optional[datetime] = None


class JobResponse(JobBase):
    id: int
    technician_id: Optional[int]
    status: JobStatus
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    created_by: int
    updated_by: Optional[int]
    notes: Optional[str]
    sla_deadline: Optional[datetime]
    sla_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class JobList(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


class RouteOptimizationRequest(BaseModel):
    date: date
    technician_ids: List[int] = []
    consider_skills: bool = True
    consider_equipment: bool = True
    consider_priority: bool = True
    max_travel_time_minutes: int = Field(60, ge=15, le=180)


class TechnicianRoute(BaseModel):
    technician_id: int
    technician_name: str
    jobs: List[JobResponse]
    total_travel_time_minutes: int
    total_job_time_minutes: int
    total_distance_km: float
    route_efficiency_score: float


class RouteOptimizationResponse(BaseModel):
    date: date
    routes: List[TechnicianRoute]
    total_technicians: int
    total_jobs: int
    average_jobs_per_technician: float
    average_travel_time_minutes: float
    average_distance_km: float
    optimization_score: float
    links: Optional[List[Dict[str, str]]] = None


# SLA schemas
class SLADefinitionBase(BaseModel):
    job_type: JobType
    priority: JobPriority
    response_time_minutes: int = Field(..., ge=0)
    resolution_time_minutes: int = Field(..., ge=0)
    description: Optional[str] = None


class SLADefinitionCreate(SLADefinitionBase):
    name: str


class SLADefinitionUpdate(BaseModel):
    response_time_minutes: Optional[int] = Field(None, ge=0)
    resolution_time_minutes: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SLADefinitionResponse(SLADefinitionBase):
    id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class SLADefinitionList(BaseModel):
    items: List[SLADefinitionResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


# Inventory schemas
class InventoryBase(BaseModel):
    name: str
    description: str
    sku: Optional[str] = None
    inventory_type: InventoryTypeEnum = InventoryTypeEnum.EQUIPMENT
    category: str
    quantity: int = Field(0, ge=0)
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    unit_cost: Optional[float] = None
    location: Optional[str] = None


class InventoryCreate(InventoryBase):
    status: InventoryStatus = InventoryStatus.AVAILABLE
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    is_active: bool = True


class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    inventory_type: Optional[InventoryTypeEnum] = None
    status: Optional[InventoryStatus] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    unit_cost: Optional[float] = None
    location: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    is_active: Optional[bool] = None


class InventoryResponse(InventoryBase):
    id: int
    status: InventoryStatus
    model_number: Optional[str]
    manufacturer: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryList(BaseModel):
    items: List[InventoryResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


class TechnicianInventoryBase(BaseModel):
    technician_id: int
    inventory_id: int
    quantity: int = Field(..., ge=0)


class TechnicianInventoryCreate(TechnicianInventoryBase):
    pass


class TechnicianInventoryUpdate(BaseModel):
    quantity: int = Field(..., ge=0)


class TechnicianInventoryResponse(TechnicianInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class TechnicianInventoryList(BaseModel):
    items: List[TechnicianInventoryResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


class InventoryTransactionBase(BaseModel):
    inventory_id: int
    transaction_type: InventoryTransactionType
    quantity: int
    notes: Optional[str] = None
    reference_number: Optional[str] = None


class InventoryTransactionCreate(InventoryTransactionBase):
    technician_id: Optional[int] = None
    job_id: Optional[int] = None


class InventoryTransactionResponse(InventoryTransactionBase):
    id: int
    technician_id: Optional[int]
    job_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionList(BaseModel):
    items: List[InventoryTransactionResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


class InventoryItemBase(BaseModel):
    name: str
    description: str
    category: str
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: int = Field(1, ge=0)
    unit_cost: Optional[float] = None
    location: str
    minimum_stock_level: Optional[int] = None


class InventoryItemCreate(InventoryItemBase):
    status: InventoryStatus = InventoryStatus.AVAILABLE
    assigned_to: Optional[int] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    unit_cost: Optional[float] = None
    location: Optional[str] = None
    status: Optional[InventoryStatus] = None
    assigned_to: Optional[int] = None
    minimum_stock_level: Optional[int] = None
    notes: Optional[str] = None


class InventoryItemResponse(InventoryItemBase):
    id: int
    status: InventoryStatus
    assigned_to: Optional[int]
    last_maintenance_date: Optional[date]
    next_maintenance_date: Optional[date]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    links: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryItemList(BaseModel):
    items: List[InventoryItemResponse]
    total: int
    page: int
    page_size: int
    links: Optional[List[Dict[str, str]]] = None


class SLAPerformanceMetrics(BaseModel):
    total_jobs: int
    jobs_completed_on_time: int
    jobs_completed_late: int
    jobs_in_progress: int
    average_response_time_minutes: float
    average_resolution_time_minutes: float
    sla_compliance_percentage: float
    performance_by_technician: Dict[str, Any]
    performance_by_job_type: Dict[str, Any]
    period_start: datetime
    period_end: datetime
