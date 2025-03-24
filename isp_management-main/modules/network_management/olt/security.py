"""
OLT Security Module

This module provides security utilities for handling OLT credentials securely.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Manages secure storage and retrieval of OLT device credentials.
    
    This class provides methods for encrypting, decrypting, and securely
    storing credentials for OLT devices.
    """
    
    def __init__(self, key_file: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize the credential manager.
        
        Args:
            key_file: Path to the encryption key file
            salt: Salt for key derivation
        """
        self.key_file = key_file or os.path.expanduser("~/.olt_key")
        self.salt = salt or b'isp_management_salt'
        self._encryption_key = None
    
    def _get_encryption_key(self) -> bytes:
        """
        Get or generate the encryption key.
        
        Returns:
            bytes: The encryption key
        """
        if self._encryption_key:
            return self._encryption_key
        
        # Check if key file exists
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, 'rb') as f:
                    self._encryption_key = f.read()
                return self._encryption_key
            except Exception as e:
                logger.warning(f"Error reading key file: {e}")
        
        # Generate a new key
        key = Fernet.generate_key()
        
        # Save the key to file with restricted permissions
        try:
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Set file permissions to be readable only by the owner
            os.chmod(self.key_file, 0o600)
        except Exception as e:
            logger.warning(f"Error saving key file: {e}")
        
        self._encryption_key = key
        return key
    
    def derive_key_from_password(self, password: str) -> bytes:
        """
        Derive an encryption key from a password.
        
        Args:
            password: The password to derive the key from
            
        Returns:
            bytes: The derived key
        """
        password_bytes = password.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.
        
        Args:
            password: The password to encrypt
            
        Returns:
            str: The encrypted password as a base64-encoded string
        """
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(password.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt an encrypted password.
        
        Args:
            encrypted_password: The encrypted password as a base64-encoded string
            
        Returns:
            str: The decrypted password
        """
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_password)
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    
    def store_credentials(self, device_id: str, username: str, password: str) -> None:
        """
        Store credentials for a device.
        
        Args:
            device_id: Unique identifier for the device
            username: The username
            password: The password
        """
        encrypted_password = self.encrypt_password(password)
        
        # In a real implementation, these would be stored in a secure database
        # For demonstration purposes, we'll just log a message
        logger.info(f"Stored credentials for device {device_id}")
    
    def retrieve_credentials(self, device_id: str) -> Tuple[str, str]:
        """
        Retrieve credentials for a device.
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            Tuple[str, str]: The username and password
        """
        # In a real implementation, these would be retrieved from a secure database
        # For demonstration purposes, we'll just raise an error
        raise NotImplementedError("Credential retrieval not implemented")
    
    def delete_credentials(self, device_id: str) -> None:
        """
        Delete credentials for a device.
        
        Args:
            device_id: Unique identifier for the device
        """
        # In a real implementation, these would be deleted from a secure database
        # For demonstration purposes, we'll just log a message
        logger.info(f"Deleted credentials for device {device_id}")
    
    def rotate_encryption_key(self) -> None:
        """
        Rotate the encryption key.
        
        This method generates a new encryption key and re-encrypts all stored
        credentials with the new key.
        """
        # In a real implementation, this would retrieve all credentials,
        # decrypt them with the old key, and re-encrypt them with a new key
        # For demonstration purposes, we'll just generate a new key
        
        # Generate a new key
        new_key = Fernet.generate_key()
        
        # Save the key to file with restricted permissions
        try:
            with open(self.key_file, 'wb') as f:
                f.write(new_key)
            
            # Set file permissions to be readable only by the owner
            os.chmod(self.key_file, 0o600)
        except Exception as e:
            logger.warning(f"Error saving key file: {e}")
        
        self._encryption_key = new_key
        logger.info("Encryption key rotated successfully")
