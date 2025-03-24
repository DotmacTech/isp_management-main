"""
Security utilities for the Integration Management Module.

This module provides utilities for encrypting and decrypting sensitive credentials,
generating secure tokens, and validating webhook signatures.
"""

import os
import base64
import json
import hmac
import hashlib
import secrets
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class CredentialEncryptor:
    """Class for encrypting and decrypting sensitive credentials."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryptor with an encryption key.
        
        If no key is provided, it will use the INTEGRATION_ENCRYPTION_KEY environment variable.
        """
        if encryption_key is None:
            encryption_key = os.environ.get("INTEGRATION_ENCRYPTION_KEY")
            
        if not encryption_key:
            raise ValueError(
                "Encryption key not provided. Set the INTEGRATION_ENCRYPTION_KEY environment variable."
            )
            
        # Derive a key from the provided encryption key
        salt = b'isp_management_salt'  # In production, this should be stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary of credentials.
        
        Args:
            data: Dictionary containing sensitive credentials
            
        Returns:
            Encrypted data as a string
        """
        # Convert dictionary to JSON string
        json_data = json.dumps(data)
        
        # Encrypt the JSON string
        encrypted_data = self.cipher.encrypt(json_data.encode())
        
        # Return the encrypted data as a base64-encoded string
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt an encrypted string back to a dictionary.
        
        Args:
            encrypted_data: Encrypted data as a string
            
        Returns:
            Dictionary containing decrypted credentials
        """
        try:
            # Decode the base64-encoded string
            decoded_data = base64.urlsafe_b64decode(encrypted_data)
            
            # Decrypt the data
            decrypted_data = self.cipher.decrypt(decoded_data)
            
            # Parse the JSON string back to a dictionary
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")


class WebhookSignatureValidator:
    """Class for validating webhook signatures."""
    
    @staticmethod
    def generate_signature(payload: Union[str, bytes, Dict[str, Any]], secret_key: str) -> str:
        """
        Generate a signature for a webhook payload.
        
        Args:
            payload: Webhook payload (string, bytes, or dictionary)
            secret_key: Secret key for signing
            
        Returns:
            HMAC signature as a hexadecimal string
        """
        # Convert dictionary to JSON string if needed
        if isinstance(payload, dict):
            payload = json.dumps(payload, sort_keys=True)
        
        # Convert string to bytes if needed
        if isinstance(payload, str):
            payload = payload.encode()
        
        # Generate HMAC signature
        signature = hmac.new(
            secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def validate_signature(
        payload: Union[str, bytes, Dict[str, Any]],
        signature: str,
        secret_key: str
    ) -> bool:
        """
        Validate a webhook signature.
        
        Args:
            payload: Webhook payload (string, bytes, or dictionary)
            signature: Signature to validate
            secret_key: Secret key for validation
            
        Returns:
            True if the signature is valid, False otherwise
        """
        expected_signature = WebhookSignatureValidator.generate_signature(payload, secret_key)
        return hmac.compare_digest(expected_signature, signature)


class TokenGenerator:
    """Class for generating and validating secure tokens."""
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key.
        
        Returns:
            Secure API key as a string
        """
        return f"ik_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """
        Generate a secure webhook secret.
        
        Returns:
            Secure webhook secret as a string
        """
        return f"whsec_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_rotation_token(expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Generate a token for credential rotation.
        
        Args:
            expiry_hours: Number of hours until the token expires
            
        Returns:
            Dictionary containing the token and expiry timestamp
        """
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        return {
            "token": token,
            "expires_at": expiry.isoformat()
        }
    
    @staticmethod
    def is_token_valid(token_data: Dict[str, Any], token: str) -> bool:
        """
        Check if a token is valid and not expired.
        
        Args:
            token_data: Dictionary containing token information
            token: Token to validate
            
        Returns:
            True if the token is valid and not expired, False otherwise
        """
        if token_data.get("token") != token:
            return False
        
        expiry_str = token_data.get("expires_at")
        if not expiry_str:
            return False
        
        try:
            expiry = datetime.fromisoformat(expiry_str)
            return datetime.utcnow() < expiry
        except ValueError:
            return False


# Initialize the token generator
_token_generator = TokenGenerator()

# Expose the token generator's methods as module-level functions
def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Secure API key as a string
    """
    return _token_generator.generate_api_key()

def generate_webhook_secret() -> str:
    """
    Generate a secure webhook secret.
    
    Returns:
        Secure webhook secret as a string
    """
    return _token_generator.generate_webhook_secret()

def generate_rotation_token(expiry_hours: int = 24) -> Dict[str, Any]:
    """
    Generate a token for credential rotation.
    
    Args:
        expiry_hours: Number of hours until the token expires
        
    Returns:
        Dictionary containing the token and expiry timestamp
    """
    return _token_generator.generate_rotation_token(expiry_hours)

def is_token_valid(token_data: Dict[str, Any], token: str) -> bool:
    """
    Check if a token is valid and not expired.
    
    Args:
        token_data: Dictionary containing token information
        token: Token to validate
        
    Returns:
        True if the token is valid and not expired, False otherwise
    """
    return _token_generator.is_token_valid(token_data, token)
