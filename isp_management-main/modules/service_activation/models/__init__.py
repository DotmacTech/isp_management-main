"""
Models for the service_activation module.

This package contains models for the service_activation module.
"""

from enum import Enum, auto


class ActivationStatus(str, Enum):
    """Enum for service activation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
