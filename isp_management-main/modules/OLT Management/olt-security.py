"""
OLT Security Module

This module provides utilities for secure handling of OLT credentials
and sensitive data through encryption and secure storage.
"""

import os
import base64
import logging
from typing import Tuple, Optional, Dict, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Manager for secure OLT credential handling.
    
    This class provides methods for securely storing, retrieving, and using
    OLT credentials with encryption.
    """
    
    def __init__(self, master_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize the credential manager.
        
        Args:
            master_key: Optional master key for encryption
            salt: Optional salt for key derivation
        """
        # Generate or use provided salt
        self.salt = salt or os.urandom(16)
        
        # Derive or use provided master key
        if master_key:
            self.key = self._derive_key(master_key, self.salt)
        else:
            # Generate a random key if no master key is provided
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
        
        # Store for encrypted credentials
        self.credentials = {}
    
    def _derive_key(self, master_key: str, salt: bytes) -> bytes:
        """
        Derive a key from the master key and salt.
        
        Args:
            master_key: Master key string
            salt: Salt bytes
            
        Returns:
            bytes: Derived key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return key
    
    def encrypt_password(self, password: str) -> bytes:
        """
        Encrypt a password.
        
        Args:
            password: Password to encrypt
            
        Returns:
            bytes: Encrypted password
        """
        return self.cipher.encrypt(password.encode())
    
    def decrypt_password(self, encrypted_password: bytes) -> str:
        """
        Decrypt an encrypted password.
        
        Args:
            encrypted_password: Encrypted password
            
        Returns:
            str: Decrypted password
        """
        return self.cipher.decrypt(encrypted_password).decode()
    
    def store_credentials(self, olt_id: str, username: str, password: str) -> None:
        """
        Store credentials for an OLT.
        
        Args:
            olt_id: Unique identifier for the OLT
            username: OLT username
            password: OLT password
        """
        encrypted_password = self.encrypt_password(password)
        self.credentials[olt_id] = {
            'username': username,
            'encrypted_password': encrypted_password
        }
        logger.debug(f"Stored credentials for OLT {olt_id}")
    
    def get_credentials(self, olt_id: str) -> Tuple[str, str]:
        """
        Get credentials for an OLT.
        
        Args:
            olt_id: Unique identifier for the OLT
            
        Returns:
            Tuple[str, str]: Username and password
            
        Raises:
            KeyError: If credentials for the OLT are not found
        """
        if olt_id not in self.credentials:
            raise KeyError(f"No credentials found for OLT {olt_id}")
        
        creds = self.credentials[olt_id]
        username = creds['username']
        password = self.decrypt_password(creds['encrypted_password'])
        
        return username, password
    
    def delete_credentials(self, olt_id: str) -> bool:
        """
        Delete credentials for an OLT.
        
        Args:
            olt_id: Unique identifier for the OLT
            
        Returns:
            bool: True if credentials were deleted, False if not found
        """
        if olt_id in self.credentials:
            del self.credentials[olt_id]
            logger.debug(f"Deleted credentials for OLT {olt_id}")
            return True
        return False
    
    def get_secure_adapter_kwargs(self, olt_id: str, **kwargs) -> Dict[str, Any]:
        """
        Get adapter kwargs with secure credentials.
        
        This method retrieves the stored credentials for an OLT and combines
        them with additional adapter parameters.
        
        Args:
            olt_id: Unique identifier for the OLT
            **kwargs: Additional adapter parameters
            
        Returns:
            Dict[str, Any]: Combined adapter parameters with credentials
        """
        username, password = self.get_credentials(olt_id)
        return {
            'username': username,
            'password': password,
            **kwargs
        }


class SecureOLTAdapter:
    """
    Wrapper for OLT adapters with secure credential handling.
    
    This class wraps an OLT adapter instance and provides secure handling
    of credentials by encrypting sensitive data in memory.
    """
    
    def __init__(self, adapter_class, host: str, encrypted_password: bytes, 
                encryption_key: bytes, username: str, **kwargs):
        """
        Initialize a secure OLT adapter.
        
        Args:
            adapter_class: OLT adapter class
            host: OLT hostname or IP address
            encrypted_password: Encrypted password
            encryption_key: Key for password decryption
            username: OLT username
            **kwargs: Additional adapter parameters
        """
        self.adapter_class = adapter_class
        self.host = host
        self._encrypted_password = encrypted_password
        self._encryption_key = encryption_key
        self.username = username
        self.kwargs = kwargs
        self._adapter = None
    
    @property
    def password(self) -> str:
        """
        Decrypt and return the password.
        
        This property decrypts the password on-demand to minimize
        exposure of the plaintext password in memory.
        
        Returns:
            str: Decrypted password
        """
        cipher = Fernet(self._encryption_key)
        return cipher.decrypt(self._encrypted_password).decode()
    
    def _get_adapter(self):
        """
        Get or create the underlying adapter instance.
        
        Returns:
            OLTAdapter: The adapter instance
        """
        if not self._adapter:
            self._adapter = self.adapter_class(
                host=self.host,
                username=self.username,
                password=self.password,
                **self.kwargs
            )
        return self._adapter
    
    def __getattr__(self, name):
        """
        Forward attribute access to the underlying adapter.
        
        Args:
            name: Attribute name
            
        Returns:
            Any: The requested attribute from the adapter
        """
        return getattr(self._get_adapter(), name)