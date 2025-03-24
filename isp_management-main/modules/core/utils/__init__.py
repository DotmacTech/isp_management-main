"""
Utils package for the core module.
"""

# Import directly from the module to avoid circular imports
import uuid

def generate_uuid() -> str:
    """
    Generate a UUID string.
    
    Returns:
        UUID string.
    """
    return str(uuid.uuid4())

__all__ = ["generate_uuid"]
