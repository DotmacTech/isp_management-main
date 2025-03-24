"""
Core utility functions for the ISP Management Platform.

This module provides utility functions that are used across
different modules of the ISP Management Platform.
"""

import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable

# Configure logging
logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID with an optional prefix.
    
    Args:
        prefix: Optional prefix for the ID.
    
    Returns:
        A unique ID string.
    """
    return f"{prefix}{uuid.uuid4().hex}"


def generate_uuid() -> str:
    """
    Generate a UUID string.
    
    Returns:
        UUID string.
    """
    return str(uuid.uuid4())


def format_datetime(dt: datetime) -> str:
    """
    Format a datetime object to ISO 8601 format.
    
    Args:
        dt: Datetime object to format.
    
    Returns:
        ISO 8601 formatted datetime string.
    """
    return dt.isoformat() if dt else None


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse an ISO 8601 formatted datetime string.
    
    Args:
        dt_str: ISO 8601 formatted datetime string.
    
    Returns:
        Datetime object or None if parsing fails.
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        logger.error(f"Failed to parse datetime: {dt_str}")
        return None


def to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert an object to a dictionary.
    
    Args:
        obj: Object to convert.
    
    Returns:
        Dictionary representation of the object.
    """
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return obj.to_dict()
    
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    
    return obj


def from_dict(cls: Any, data: Dict[str, Any]) -> Any:
    """
    Create an object from a dictionary.
    
    Args:
        cls: Class to instantiate.
        data: Dictionary containing object data.
    
    Returns:
        Instance of the class.
    """
    if hasattr(cls, "from_dict") and callable(getattr(cls, "from_dict")):
        return cls.from_dict(data)
    
    return cls(**data)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load a JSON string.
    
    Args:
        json_str: JSON string to load.
        default: Default value to return if loading fails.
    
    Returns:
        Loaded JSON data or default value if loading fails.
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.error(f"Failed to decode JSON: {json_str}")
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump an object to a JSON string.
    
    Args:
        obj: Object to dump.
        default: Default string to return if dumping fails.
    
    Returns:
        JSON string or default string if dumping fails.
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, OverflowError):
        logger.error(f"Failed to encode JSON: {obj}")
        return default


def retry(max_attempts: int = 3, delay: float = 1.0, 
          backoff: float = 2.0, exceptions: tuple = (Exception,),
          logger: Optional[logging.Logger] = None) -> Callable:
    """
    Retry decorator for functions that might fail temporarily.
    
    Args:
        max_attempts: Maximum number of attempts.
        delay: Initial delay between attempts in seconds.
        backoff: Backoff multiplier.
        exceptions: Tuple of exceptions to catch.
        logger: Logger to use for logging retries.
    
    Returns:
        Decorated function.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            local_logger = logger or logging.getLogger(func.__module__)
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        local_logger.error(f"Final attempt {attempt}/{max_attempts} failed: {e}")
                        raise
                    
                    local_logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}. "
                                         f"Retrying in {current_delay:.2f}s...")
                    
                    # Sleep and increase backoff
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
        
        return wrapper
    
    return decorator
