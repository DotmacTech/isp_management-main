"""
Database models for the Field Services Module.

These models define the database structure for job scheduling, technician management,
route optimization, and inventory management.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Date, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend_core.database import Base
from backend_core.mixins import TimestampMixin
from backend_core.models import Customer  # Import the existing Customer model


class JobStatusEnum(enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class JobPriorityEnum(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobTypeEnum(enum.Enum):
    INSTALLATION = "installation"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"
    UPGRADE = "upgrade"
    INSPECTION = "inspection"
    TROUBLESHOOTING = "troubleshooting"


class TechnicianStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    BUSY = "busy"
    AVAILABLE = "available"
    ON_JOB = "on_job"


class InventoryStatusEnum(enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    DEFECTIVE = "defective"
    UNDER_REPAIR = "under_repair"
    DEPLETED = "depleted"


class InventoryType(enum.Enum):
    EQUIPMENT = "equipment"
    TOOL = "tool"
    PART = "part"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    SOFTWARE = "software"


class InventoryTransactionTypeEnum(enum.Enum):
    ALLOCATION = "allocation"
    RETURN = "return"
    USAGE = "usage"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    INITIAL = "initial"  # Added for initial inventory creation


class NotificationTypeEnum(enum.Enum):
    JOB_ASSIGNMENT = "job_assignment"
    JOB_UPDATE = "job_update"
    JOB_COMPLETION = "job_completion"
    SLA_ALERT = "sla_alert"
    INVENTORY_ALERT = "inventory_alert"
    SYSTEM_NOTIFICATION = "system_notification"


class NotificationPriorityEnum(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Technician(Base, TimestampMixin):
    """Model for field service technicians."""
    __tablename__ = "field_technicians"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(20), nullable=False)
    skills = Column(JSON, nullable=False, default=list)
    certification_level = Column(String(50), nullable=True)
    region = Column(String(100), nullable=True)
    status = Column(Enum(TechnicianStatusEnum), nullable=False, default=TechnicianStatusEnum.ACTIVE)
    max_jobs_per_day = Column(Integer, nullable=True, default=5)
    home_location_lat = Column(Float, nullable=True)
    home_location_lon = Column(Float, nullable=True)
    current_location_lat = Column(Float, nullable=True)
    current_location_lon = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)

    # Relationships
    jobs = relationship("Job", back_populates="technician")
    notifications = relationship("TechnicianNotification", back_populates="technician")
    inventory_items = relationship("TechnicianInventory", back_populates="technician")


class Job(Base, TimestampMixin):
    """Model for field service jobs."""
    __tablename__ = "field_jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"), nullable=True)
    job_type = Column(Enum(JobTypeEnum), nullable=False)
    status = Column(Enum(JobStatusEnum), nullable=False, default=JobStatusEnum.PENDING)
    priority = Column(Enum(JobPriorityEnum), nullable=False, default=JobPriorityEnum.MEDIUM)
    estimated_duration_minutes = Column(Integer, nullable=False)
    scheduled_start_time = Column(DateTime, nullable=True)
    scheduled_end_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    location_address = Column(String(255), nullable=False)
    required_skills = Column(JSON, nullable=True, default=list)
    required_equipment = Column(JSON, nullable=True, default=list)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    sla_deadline = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    technician = relationship("Technician", back_populates="jobs")
    job_history = relationship("JobHistory", back_populates="job")
    inventory_transactions = relationship("InventoryTransaction", back_populates="job")


class Inventory(Base, TimestampMixin):
    """Model for inventory items in the system."""
    __tablename__ = "field_inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    sku = Column(String(100), nullable=True, unique=True)
    model_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    unit_cost = Column(Float, nullable=True)
    total_quantity = Column(Integer, nullable=False, default=0)
    minimum_stock_level = Column(Integer, nullable=True)
    reorder_point = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    inventory_type = Column(Enum(InventoryType), nullable=False, default=InventoryType.EQUIPMENT)
    min_quantity = Column(Integer, nullable=True)
    max_quantity = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    status = Column(Enum(InventoryStatusEnum), nullable=False, default=InventoryStatusEnum.AVAILABLE)
    
    # Relationships
    technician_inventory = relationship("TechnicianInventory", back_populates="inventory")
    inventory_transactions = relationship("InventoryTransaction", back_populates="inventory")


class TechnicianInventory(Base, TimestampMixin):
    """Model for tracking inventory assigned to technicians."""
    __tablename__ = "field_technician_inventory"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("field_inventory_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    
    # Relationships
    technician = relationship("Technician", back_populates="inventory_items")
    inventory = relationship("Inventory", back_populates="technician_inventory")


class InventoryTransaction(Base, TimestampMixin):
    """Model for tracking inventory transactions."""
    __tablename__ = "field_inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("field_inventory_items.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("field_jobs.id"), nullable=True)
    transaction_type = Column(Enum(InventoryTransactionTypeEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="inventory_transactions")
    technician = relationship("Technician")
    job = relationship("Job", back_populates="inventory_transactions")


class InventoryItem(Base, TimestampMixin):
    """Model for field service inventory items."""
    __tablename__ = "field_inventory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    serial_number = Column(String(100), nullable=True, unique=True)
    model_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Float, nullable=True)
    location = Column(String(200), nullable=False)
    status = Column(Enum(InventoryStatusEnum), nullable=False, default=InventoryStatusEnum.AVAILABLE)
    assigned_to = Column(Integer, ForeignKey("field_technicians.id"), nullable=True)
    minimum_stock_level = Column(Integer, nullable=True)
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    assigned_technician = relationship("Technician", foreign_keys=[assigned_to])
    job_materials = relationship("JobMaterial", back_populates="inventory_item")


class JobMaterial(Base, TimestampMixin):
    """Model for materials used in jobs."""
    __tablename__ = "field_job_materials"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("field_jobs.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("field_inventory.id"), nullable=False)
    quantity_used = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="job_materials")
    inventory_item = relationship("InventoryItem", back_populates="job_materials")


class TechnicianAvailability(Base, TimestampMixin):
    """Model for technician availability schedule."""
    __tablename__ = "field_technician_availability"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    reason = Column(String(255), nullable=True)

    # Relationships
    technician = relationship("Technician")


class SLADefinition(Base, TimestampMixin):
    """Model for Service Level Agreement definitions."""
    __tablename__ = "field_sla_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    job_type = Column(Enum(JobTypeEnum), nullable=False)
    priority = Column(Enum(JobPriorityEnum), nullable=False)
    response_time_minutes = Column(Integer, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class JobHistory(Base, TimestampMixin):
    """Model for tracking job status changes and events."""
    __tablename__ = "field_job_history"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("field_jobs.id"), nullable=False)
    status_from = Column(Enum(JobStatusEnum), nullable=True)
    status_to = Column(Enum(JobStatusEnum), nullable=False)
    notes = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="job_history")


class TechnicianNotification(Base, TimestampMixin):
    """Model for notifications sent to technicians."""
    __tablename__ = "field_technician_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationTypeEnum), nullable=False)
    priority = Column(Enum(NotificationPriorityEnum), nullable=False, default=NotificationPriorityEnum.MEDIUM)
    job_id = Column(Integer, ForeignKey("field_jobs.id"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    # Relationships
    technician = relationship("Technician", back_populates="notifications")
    job = relationship("Job")
