"""
Common enumerations and constants for the CRM & Ticketing module.
"""

from enum import Enum, auto
from datetime import datetime, timedelta


class TicketStatus(str, Enum):
    """Status of a support ticket."""
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_THIRD_PARTY = "waiting_on_third_party"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    CANCELLED = "cancelled"


class TicketPriority(str, Enum):
    """Priority level of a support ticket."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TicketType(str, Enum):
    """Type of support ticket."""
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    SERVICE_REQUEST = "service_request"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    FEEDBACK = "feedback"
    OTHER = "other"


class ContactType(str, Enum):
    """Type of customer contact."""
    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    OTHER = "other"


class ContactMethod(str, Enum):
    """Method of customer contact."""
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    CHAT = "chat"
    PORTAL = "portal"
    SOCIAL = "social"
    IN_PERSON = "in_person"
    OTHER = "other"


# SLA response time targets in minutes
SLA_RESPONSE_TIMES = {
    # Priority: (first_response, update_frequency, resolution_target)
    TicketPriority.LOW: (24 * 60, 24 * 60, 7 * 24 * 60),  # 24h, 24h, 7 days
    TicketPriority.MEDIUM: (8 * 60, 12 * 60, 3 * 24 * 60),  # 8h, 12h, 3 days
    TicketPriority.HIGH: (4 * 60, 8 * 60, 24 * 60),  # 4h, 8h, 24h
    TicketPriority.URGENT: (60, 4 * 60, 8 * 60),  # 1h, 4h, 8h
    TicketPriority.CRITICAL: (30, 60, 4 * 60),  # 30min, 1h, 4h
}


def get_sla_target_datetime(priority: TicketPriority, sla_type: str) -> datetime:
    """
    Calculate the target datetime for a specific SLA type based on priority.
    
    Args:
        priority: The ticket priority
        sla_type: The type of SLA target ('first_response', 'update', 'resolution')
        
    Returns:
        The target datetime
    """
    now = datetime.utcnow()
    
    if sla_type == "first_response":
        index = 0
    elif sla_type == "update":
        index = 1
    elif sla_type == "resolution":
        index = 2
    else:
        raise ValueError(f"Unknown SLA type: {sla_type}")
    
    minutes = SLA_RESPONSE_TIMES.get(priority, SLA_RESPONSE_TIMES[TicketPriority.MEDIUM])[index]
    return now + timedelta(minutes=minutes)


def calculate_sla_breach(target_time: datetime) -> bool:
    """
    Check if an SLA has been breached.
    
    Args:
        target_time: The target time for the SLA
        
    Returns:
        True if the SLA has been breached, False otherwise
    """
    return datetime.utcnow() > target_time


def get_sla_status(target_time: datetime) -> str:
    """
    Get the status of an SLA.
    
    Args:
        target_time: The target time for the SLA
        
    Returns:
        'breached', 'at_risk', or 'on_track'
    """
    now = datetime.utcnow()
    
    if now > target_time:
        return "breached"
    
    # If within 25% of the target time, consider it at risk
    time_remaining = (target_time - now).total_seconds() / 60  # in minutes
    time_total = (target_time - (now - (target_time - now))).total_seconds() / 60
    
    if time_remaining <= (time_total * 0.25):
        return "at_risk"
    
    return "on_track"
