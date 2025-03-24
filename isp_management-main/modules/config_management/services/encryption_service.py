"""
Encryption service for the Configuration Management Module.

This service provides methods for encrypting and decrypting sensitive configuration data
using industry-standard encryption algorithms.
"""

import base64
import os
import json
import logging
from typing import Any, Dict, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive configuration data."""
    
    def __init__(self, key: str = None):
        """
        Initialize the encryption service.
        
        Args:
            key: Encryption key (if not provided, will use environment variable or generate one)
        """
        self.key = key or os.environ.get("CONFIG_ENCRYPTION_KEY")
        
        if not self.key:
            # Generate a key if not provided
            logger.warning("No encryption key provided, generating a temporary one")
            self.key = Fernet.generate_key().decode()
            logger.warning(f"Generated temporary encryption key: {self.key}")
            logger.warning("This key will be lost when the service restarts. Set CONFIG_ENCRYPTION_KEY environment variable for persistence.")
        
        # Derive a Fernet key from the provided key
        if not isinstance(self.key, bytes):
            self.key = self.key.encode()
        
        # Use PBKDF2 to derive a key if the provided key is not in the correct format
        if len(self.key) != 32:
            salt = b"isp_management_salt"  # In production, this should be stored securely
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(self.key))
            self.fernet = Fernet(derived_key)
        else:
            # If key is already in the correct format, use it directly
            self.fernet = Fernet(base64.urlsafe_b64encode(self.key))
    
    def encrypt(self, value: Any) -> str:
        """
        Encrypt a value.
        
        Args:
            value: Value to encrypt (will be converted to JSON string first)
            
        Returns:
            Encrypted value as a base64-encoded string
        """
        try:
            # Convert value to JSON string
            value_str = json.dumps(value)
            
            # Encrypt the value
            encrypted = self.fernet.encrypt(value_str.encode())
            
            # Return as base64-encoded string
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Error encrypting value: {str(e)}")
            raise
    
    def decrypt(self, encrypted_value: str) -> Any:
        """
        Decrypt a value.
        
        Args:
            encrypted_value: Encrypted value as a base64-encoded string
            
        Returns:
            Decrypted value (parsed from JSON)
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_value)
            
            # Decrypt the value
            decrypted = self.fernet.decrypt(encrypted_bytes)
            
            # Parse from JSON
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Error decrypting value: {str(e)}")
            raise
