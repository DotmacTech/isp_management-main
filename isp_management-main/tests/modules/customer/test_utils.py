"""
Tests for the Customer Management Module utility functions.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import re
import os
from unittest.mock import patch, mock_open
from datetime import datetime

from modules.customer.utils import (
    generate_customer_number,
    validate_email,
    validate_phone,
    is_valid_tax_id,
    generate_verification_token,
    mask_sensitive_data,
    sanitize_filename,
    get_mime_type
)


def test_generate_customer_number():
    """Test generating a customer number."""
    # Test with a prefix
    customer_number = generate_customer_number(prefix="CUST")
    assert customer_number.startswith("CUST-")
    assert len(customer_number) > 5  # Prefix + hyphen + at least one character
    
    # Test without a prefix
    customer_number = generate_customer_number()
    assert re.match(r"^C-\d{6}-\d{4}$", customer_number)  # Default format: C-YYMMDD-XXXX


def test_validate_email():
    """Test email validation."""
    # Valid emails
    assert validate_email("user@example.com") == True
    assert validate_email("user.name@example.co.uk") == True
    assert validate_email("user+tag@example.com") == True
    
    # Invalid emails
    assert validate_email("user@") == False
    assert validate_email("user@.com") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@example") == False
    assert validate_email("user.example.com") == False
    assert validate_email("") == False
    assert validate_email(None) == False


def test_validate_phone():
    """Test phone number validation."""
    # Valid phone numbers
    assert validate_phone("+1234567890") == True
    assert validate_phone("+44 1234 567890") == True
    assert validate_phone("+1 (123) 456-7890") == True
    
    # Invalid phone numbers
    assert validate_phone("1234567890") == False  # No + prefix
    assert validate_phone("+12345") == False  # Too short
    assert validate_phone("+abcdefghij") == False  # Non-numeric
    assert validate_phone("") == False
    assert validate_phone(None) == False


def test_is_valid_tax_id():
    """Test tax ID validation."""
    # This is a placeholder test since tax ID validation is country-specific
    # In a real implementation, you would test specific formats for each country
    
    # Assume a simple format for testing
    assert is_valid_tax_id("123-45-6789") == True
    assert is_valid_tax_id("12-3456789") == True
    
    # Invalid formats
    assert is_valid_tax_id("12345") == False  # Too short
    assert is_valid_tax_id("") == False
    assert is_valid_tax_id(None) == False


def test_generate_verification_token():
    """Test generating a verification token."""
    # Generate a token
    token = generate_verification_token()
    
    # Check that it's a string of appropriate length
    assert isinstance(token, str)
    assert len(token) >= 32  # Tokens should be reasonably long for security
    
    # Generate another token and ensure it's different
    another_token = generate_verification_token()
    assert token != another_token


def test_mask_sensitive_data():
    """Test masking sensitive data."""
    # Test masking an email
    email = "user@example.com"
    masked_email = mask_sensitive_data(email, data_type="email")
    assert masked_email != email
    assert "@example.com" in masked_email
    assert "user" not in masked_email
    
    # Test masking a phone number
    phone = "+1234567890"
    masked_phone = mask_sensitive_data(phone, data_type="phone")
    assert masked_phone != phone
    assert masked_phone.endswith("7890")
    assert "+123456" not in masked_phone
    
    # Test masking a credit card
    card = "4111111111111111"
    masked_card = mask_sensitive_data(card, data_type="credit_card")
    assert masked_card != card
    assert masked_card.endswith("1111")
    assert "4111111111" not in masked_card


def test_sanitize_filename():
    """Test sanitizing filenames."""
    # Test with a normal filename
    filename = "document.pdf"
    sanitized = sanitize_filename(filename)
    assert sanitized == "document.pdf"
    
    # Test with spaces and special characters
    filename = "my document with spaces!.pdf"
    sanitized = sanitize_filename(filename)
    assert " " not in sanitized
    assert "!" not in sanitized
    assert sanitized.endswith(".pdf")
    
    # Test with path traversal attempt
    filename = "../../../etc/passwd"
    sanitized = sanitize_filename(filename)
    assert "/" not in sanitized
    assert ".." not in sanitized


def test_get_mime_type():
    """Test getting MIME type from a file."""
    # Mock the open function and os.path.exists
    with patch("builtins.open", mock_open(read_data=b"PDF")), \
         patch("os.path.exists", return_value=True):
        
        # Test with a PDF file
        mime_type = get_mime_type("/path/to/document.pdf")
        assert mime_type is not None
        
        # In a real test, you would check for specific MIME types,
        # but since we're mocking the file, we can't test the actual detection
    
    # Test with a non-existent file
    with patch("os.path.exists", return_value=False):
        mime_type = get_mime_type("/path/to/nonexistent.file")
        assert mime_type is None


# Add more tests for other utility functions as needed
