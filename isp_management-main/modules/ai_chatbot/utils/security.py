"""
Security utilities for the AI Chatbot Integration Module.

This module provides security-related functions for the AI Chatbot Integration Module,
including API key management, request signing, and data masking.
"""

import os
import hmac
import hashlib
import base64
import json
import logging
import re
from typing import Dict, List, Any, Optional, Union

from fastapi import HTTPException, status
from datetime import datetime, timedelta

from core.security import create_access_token, verify_password, get_password_hash
from ..config.settings import chatbot_settings

# Initialize logger
logger = logging.getLogger(__name__)


def mask_sensitive_data(data: Union[Dict[str, Any], List[Any], str]) -> Union[Dict[str, Any], List[Any], str]:
    """
    Mask sensitive data in a dictionary, list, or string.
    
    Args:
        data: The data to mask
        
    Returns:
        The masked data
    """
    if not chatbot_settings.MASK_SENSITIVE_DATA:
        return data
    
    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if any(field.lower() in key.lower() for field in chatbot_settings.SENSITIVE_FIELDS):
                if isinstance(value, str) and value:
                    if len(value) <= 8:
                        masked_data[key] = "****"
                    else:
                        masked_data[key] = value[:4] + "****" + value[-4:]
                else:
                    masked_data[key] = "****"
            elif isinstance(value, (dict, list)):
                masked_data[key] = mask_sensitive_data(value)
            else:
                masked_data[key] = value
        return masked_data
    
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    
    elif isinstance(data, str):
        # Mask common patterns like credit card numbers, SSNs, etc.
        # Credit card pattern: 16 digits, optionally separated by spaces or dashes
        cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        # SSN pattern: 9 digits, optionally separated by dashes
        ssn_pattern = r"\b\d{3}[-]?\d{2}[-]?\d{4}\b"
        
        # Mask credit card numbers
        data = re.sub(cc_pattern, "****-****-****-****", data)
        # Mask SSNs
        data = re.sub(ssn_pattern, "***-**-****", data)
        
        return data
    
    else:
        return data


def generate_hmac_signature(payload: Union[str, bytes, Dict[str, Any]], secret_key: str) -> str:
    """
    Generate an HMAC signature for a payload.
    
    Args:
        payload: The payload to sign
        secret_key: The secret key to use for signing
        
    Returns:
        The HMAC signature
    """
    if isinstance(payload, dict):
        payload = json.dumps(payload, sort_keys=True).encode()
    elif isinstance(payload, str):
        payload = payload.encode()
    
    signature = hmac.new(
        secret_key.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_hmac_signature(payload: Union[str, bytes, Dict[str, Any]], signature: str, secret_key: str) -> bool:
    """
    Verify an HMAC signature for a payload.
    
    Args:
        payload: The payload to verify
        signature: The signature to verify
        secret_key: The secret key used for signing
        
    Returns:
        Whether the signature is valid
    """
    expected_signature = generate_hmac_signature(payload, secret_key)
    return hmac.compare_digest(signature, expected_signature)


def generate_api_key() -> str:
    """
    Generate a random API key.
    
    Returns:
        A random API key
    """
    # Generate 32 random bytes and encode as base64
    random_bytes = os.urandom(32)
    api_key = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
    
    return api_key


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.
    
    Args:
        api_key: The API key to encrypt
        
    Returns:
        The encrypted API key
    """
    # Use the password hashing function from core.security
    return get_password_hash(api_key)


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verify an API key against a hashed API key.
    
    Args:
        api_key: The API key to verify
        hashed_api_key: The hashed API key to verify against
        
    Returns:
        Whether the API key is valid
    """
    # Use the password verification function from core.security
    return verify_password(api_key, hashed_api_key)


def sanitize_user_input(input_text: str) -> str:
    """
    Sanitize user input to prevent prompt injection and other attacks.
    
    Args:
        input_text: The input text to sanitize
        
    Returns:
        The sanitized input text
    """
    # Remove any control characters
    sanitized = re.sub(r"[\x00-\x1F\x7F]", "", input_text)
    
    # Remove any potential prompt injection patterns
    # This is a basic example and should be expanded based on the specific AI service being used
    injection_patterns = [
        r"ignore previous instructions",
        r"disregard previous",
        r"ignore all instructions",
        r"system prompt",
        r"you are now",
        r"new persona"
    ]
    
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
    
    return sanitized
