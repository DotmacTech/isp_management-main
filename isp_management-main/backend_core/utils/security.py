"""
Security utilities for the ISP Management Platform.

This module provides functions for password hashing, verification, and other security-related operations.
"""

import hashlib
import secrets
import string
import bcrypt
from typing import Tuple


def generate_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.
    
    Args:
        length: Length of the random string to generate
        
    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    # Generate a salt and hash the password
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def generate_api_key() -> Tuple[str, str]:
    """
    Generate an API key and its hash.
    
    Returns:
        Tuple of (API key, hashed API key)
    """
    api_key = generate_random_string(48)
    hashed_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    return api_key, hashed_key


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        api_key: Plain text API key
        hashed_key: Hashed API key
        
    Returns:
        True if the API key matches the hash, False otherwise
    """
    calculated_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    return calculated_hash == hashed_key
