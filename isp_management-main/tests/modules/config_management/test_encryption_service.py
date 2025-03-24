"""
Unit tests for the Configuration Management Module's encryption service.

This module tests the functionality of the EncryptionService class, which
is responsible for encrypting and decrypting sensitive configuration data.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
import base64
from datetime import datetime
from unittest.mock import patch, MagicMock

from modules.config_management.services.encryption_service import EncryptionService


class TestEncryptionService:
    """Tests for the EncryptionService class."""
    
    def test_init_with_key(self):
        """Test initializing the encryption service with a key."""
        service = EncryptionService(key="test_encryption_key")
        assert service.key is not None
    
    def test_init_without_key(self):
        """Test initializing the encryption service without a key."""
        with patch('os.environ.get', return_value=None), \
             patch('modules.config_management.services.encryption_service.Fernet.generate_key', 
                  return_value=b'generated_key'):
            service = EncryptionService()
            assert service.key is not None
    
    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string value."""
        service = EncryptionService(key="test_encryption_key_for_unit_tests_only")
        
        original_value = "sensitive data"
        encrypted_value = service.encrypt(original_value)
        
        # Verify the value was encrypted (should be different from original)
        assert encrypted_value != original_value
        
        # Decrypt and verify it matches the original
        decrypted_value = service.decrypt(encrypted_value)
        assert decrypted_value == original_value
    
    def test_encrypt_decrypt_dict(self):
        """Test encrypting and decrypting a dictionary value."""
        service = EncryptionService(key="test_encryption_key_for_unit_tests_only")
        
        original_value = {
            "api_key": "secret_key",
            "username": "admin",
            "password": "secure_password"
        }
        
        encrypted_value = service.encrypt(original_value)
        
        # Verify the value was encrypted (should be different from original)
        assert encrypted_value != original_value
        assert isinstance(encrypted_value, str)
        
        # Decrypt and verify it matches the original
        decrypted_value = service.decrypt(encrypted_value)
        assert decrypted_value == original_value
        assert isinstance(decrypted_value, dict)
    
    def test_encrypt_decrypt_list(self):
        """Test encrypting and decrypting a list value."""
        service = EncryptionService(key="test_encryption_key_for_unit_tests_only")
        
        original_value = ["secret1", "secret2", "secret3"]
        
        encrypted_value = service.encrypt(original_value)
        
        # Verify the value was encrypted (should be different from original)
        assert encrypted_value != original_value
        assert isinstance(encrypted_value, str)
        
        # Decrypt and verify it matches the original
        decrypted_value = service.decrypt(encrypted_value)
        assert decrypted_value == original_value
        assert isinstance(decrypted_value, list)
    
    def test_encrypt_decrypt_complex_structure(self):
        """Test encrypting and decrypting a complex nested structure."""
        service = EncryptionService(key="test_encryption_key_for_unit_tests_only")
        
        original_value = {
            "user": {
                "id": 1,
                "name": "Admin User",
                "credentials": {
                    "api_keys": ["key1", "key2"],
                    "tokens": {
                        "access": "access_token",
                        "refresh": "refresh_token"
                    }
                }
            },
            "settings": [
                {"name": "setting1", "value": True},
                {"name": "setting2", "value": 42}
            ]
        }
        
        encrypted_value = service.encrypt(original_value)
        
        # Verify the value was encrypted (should be different from original)
        assert encrypted_value != original_value
        assert isinstance(encrypted_value, str)
        
        # Decrypt and verify it matches the original
        decrypted_value = service.decrypt(encrypted_value)
        assert decrypted_value == original_value
        assert isinstance(decrypted_value, dict)
        assert isinstance(decrypted_value["user"]["credentials"]["api_keys"], list)
        assert isinstance(decrypted_value["user"]["credentials"]["tokens"], dict)
        assert isinstance(decrypted_value["settings"], list)
    
    def test_different_keys_incompatible(self):
        """Test that values encrypted with one key cannot be decrypted with another."""
        service1 = EncryptionService(key="test_encryption_key_1")
        service2 = EncryptionService(key="test_encryption_key_2")
        
        original_value = "sensitive data"
        encrypted_value = service1.encrypt(original_value)
        
        # Attempting to decrypt with a different key should raise an exception
        with pytest.raises(Exception):
            service2.decrypt(encrypted_value)
    
    def test_invalid_encrypted_value(self):
        """Test handling of invalid encrypted values."""
        service = EncryptionService(key="test_encryption_key_for_unit_tests_only")
        
        # Attempt to decrypt an invalid value
        with pytest.raises(Exception):
            service.decrypt("not_a_valid_encrypted_value")
        
        # Attempt to decrypt a valid base64 string but not encrypted by this service
        with pytest.raises(Exception):
            service.decrypt(base64.b64encode(b"not_encrypted_by_this_service").decode())
