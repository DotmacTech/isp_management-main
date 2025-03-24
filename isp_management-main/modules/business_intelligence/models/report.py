"""
Database models for the Business Intelligence and Reporting module.

This module provides the database models for report templates, scheduled reports,
report executions, and related entities.
"""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Enum, 
    ForeignKey, JSON, Table, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from backend_core.database import Base


class ReportType(str, enum.Enum):
    """Enumeration of report types."""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    CUSTOMER = "customer"
    USAGE = "usage"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    """Enumeration of report output formats."""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    HTML = "html"
    JSON = "json"


class ReportFrequency(str, enum.Enum):
    """Enumeration of report scheduling frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class DeliveryMethod(str, enum.Enum):
    """Enumeration of report delivery methods."""
    EMAIL = "email"
    API = "api"
    DOWNLOAD = "download"
    DASHBOARD = "dashboard"
    FILE_STORAGE = "file_storage"


class ReportTemplate(Base):
    """
    Model for report templates.
    
    A report template defines the structure, query parameters, and presentation
    of a report that can be executed on demand or scheduled.
    """
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False)
    template_data = Column(JSON, nullable=False)  # JSON structure defining the report
    query_definition = Column(JSON, nullable=False)  # JSON structure defining the data query
    parameters_schema = Column(JSON, nullable=True)  # JSON schema for report parameters
    is_system = Column(Boolean, default=False)  # Whether this is a system-defined template
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    scheduled_reports = relationship("ScheduledReport", back_populates="template", cascade="all, delete-orphan")
    report_executions = relationship("ReportExecution", back_populates="template", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, name='{self.name}', type='{self.report_type}')>"


class ScheduledReport(Base):
    """
    Model for scheduled reports.
    
    A scheduled report is a configuration that specifies when and how a report template
    should be executed and delivered automatically.
    """
    __tablename__ = "scheduled_reports"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)
    frequency = Column(Enum(ReportFrequency), nullable=False)
    cron_expression = Column(String(100), nullable=True)  # For custom schedules
    parameters = Column(JSON, nullable=True)  # Parameters to apply when generating the report
    delivery_method = Column(Enum(DeliveryMethod), nullable=False)
    delivery_config = Column(JSON, nullable=False)  # JSON config for delivery (email addresses, etc.)
    is_active = Column(Boolean, default=True)
    last_execution_time = Column(DateTime, nullable=True)
    next_execution_time = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    template = relationship("ReportTemplate", back_populates="scheduled_reports")
    created_by = relationship("User", foreign_keys=[created_by_id])
    executions = relationship("ReportExecution", back_populates="scheduled_report", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScheduledReport(id={self.id}, name='{self.name}', frequency='{self.frequency}')>"


class ReportStatus(str, enum.Enum):
    """Enumeration of report execution statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ReportExecution(Base):
    """
    Model for report executions.
    
    A report execution represents a single instance of a report being generated,
    either on-demand or as part of a scheduled execution.
    """
    __tablename__ = "report_executions"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)
    scheduled_report_id = Column(Integer, ForeignKey("scheduled_reports.id"), nullable=True)
    parameters = Column(JSON, nullable=True)  # Parameters used for this execution
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    formats = Column(JSON, nullable=False)  # List of output formats generated
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)  # Time taken to generate the report
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    template = relationship("ReportTemplate", back_populates="report_executions")
    scheduled_report = relationship("ScheduledReport", back_populates="executions")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    outputs = relationship("ReportOutput", back_populates="execution", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ReportExecution(id={self.id}, template_id={self.template_id}, status='{self.status}')>"


class ReportOutput(Base):
    """
    Model for report output files.
    
    A report output represents a generated file in a specific format for a report execution.
    """
    __tablename__ = "report_outputs"
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("report_executions.id"), nullable=False)
    format = Column(Enum(ReportFormat), nullable=False)
    file_path = Column(String(512), nullable=False)  # Path to the generated file
    file_size = Column(Integer, nullable=False)  # Size in bytes
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    execution = relationship("ReportExecution", back_populates="outputs")
    
    def __repr__(self):
        return f"<ReportOutput(id={self.id}, execution_id={self.execution_id}, format='{self.format}')>"


class ReportAccessLog(Base):
    """
    Model for report access logs.
    
    Tracks access to reports for audit and security purposes.
    """
    __tablename__ = "report_access_logs"
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("report_executions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_time = Column(DateTime, server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False)  # e.g., "view", "download", "email"
    
    # Relationships
    execution = relationship("ReportExecution")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ReportAccessLog(id={self.id}, execution_id={self.execution_id}, user_id={self.user_id})>"


class DataSource(Base):
    """
    Model for data sources.
    
    A data source defines a connection to a specific data repository that can be
    used for report generation.
    """
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False)  # e.g., "database", "api", "file"
    connection_details = Column(JSON, nullable=False)  # Connection parameters (encrypted)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', type='{self.source_type}')>"


# Many-to-many relationship between report templates and data sources
report_template_data_sources = Table(
    "report_template_data_sources",
    Base.metadata,
    Column("template_id", Integer, ForeignKey("report_templates.id"), primary_key=True),
    Column("data_source_id", Integer, ForeignKey("data_sources.id"), primary_key=True)
)
