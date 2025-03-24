"""
Utility functions for the Customer Management Module.
"""

import re
import random
import string
import secrets
from datetime import datetime
from typing import Optional


def generate_customer_number() -> str:
    """
    Generate a unique customer number.
    
    Returns:
        A unique customer number in the format 'C-YYYYMMDD-XXXXX'
        where YYYYMMDD is the current date and XXXXX is a random 5-digit number.
    """
    date_part = datetime.utcnow().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=5))
    return f"C-{date_part}-{random_part}"


def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email:
        return False
        
    # Simple regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate a phone number.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone number is valid, False otherwise
    """
    if not phone:
        return False
        
    # Remove common separators and spaces
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check if it's a valid phone number (simple check)
    # Allow + at the beginning for international numbers
    pattern = r'^\+?[0-9]{8,15}$'
    return bool(re.match(pattern, cleaned))


def generate_verification_token(length: int = 32) -> str:
    """
    Generate a secure verification token.
    
    Args:
        length: Length of the token
        
    Returns:
        A secure random token
    """
    return secrets.token_urlsafe(length)


def generate_portal_id(customer_id: int, prefix: str = "1000") -> str:
    """
    Generate a portal ID for customer login and PPPoE authentication.
    
    Args:
        customer_id: Customer ID
        prefix: Prefix for portal ID (default: "1000")
        
    Returns:
        Portal ID in format PREFIX + CUSTOMERID (e.g., 100000016)
    """
    return f"{prefix}{customer_id:08d}"


def format_customer_name(customer) -> str:
    """
    Format a customer's name for display.
    
    Args:
        customer: Customer object
        
    Returns:
        Formatted name
    """
    if customer.customer_type.value == 'individual':
        if customer.first_name and customer.last_name:
            return f"{customer.first_name} {customer.last_name}"
        elif customer.first_name:
            return customer.first_name
        else:
            return "Unknown"
    else:
        return customer.company_name or "Unknown Company"


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data like credit card numbers or personal IDs.
    
    Args:
        data: Data to mask
        visible_chars: Number of characters to leave visible at the end
        
    Returns:
        Masked data
    """
    if not data:
        return ""
        
    if len(data) <= visible_chars:
        return "*" * len(data)
        
    masked_part = "*" * (len(data) - visible_chars)
    visible_part = data[-visible_chars:]
    
    return f"{masked_part}{visible_part}"


def calculate_subscription_status(
    subscription_state: str,
    subscription_end_date: Optional[datetime] = None
) -> str:
    """
    Calculate a human-readable subscription status.
    
    Args:
        subscription_state: Current subscription state
        subscription_end_date: Subscription end date
        
    Returns:
        Human-readable status
    """
    if subscription_state == "active":
        if subscription_end_date:
            days_left = (subscription_end_date - datetime.utcnow()).days
            if days_left <= 0:
                return "Expired"
            elif days_left <= 7:
                return f"Active (expires in {days_left} days)"
            else:
                return "Active"
        else:
            return "Active (no expiration)"
    elif subscription_state == "trial":
        if subscription_end_date:
            days_left = (subscription_end_date - datetime.utcnow()).days
            if days_left <= 0:
                return "Trial expired"
            else:
                return f"Trial ({days_left} days left)"
        else:
            return "Trial"
    else:
        return subscription_state.capitalize()


def is_valid_tax_id(tax_id: str, country_code: str = "US") -> bool:
    """
    Validate a tax ID based on country-specific rules.
    
    Args:
        tax_id: Tax ID to validate
        country_code: ISO country code
        
    Returns:
        True if tax ID is valid, False otherwise
    """
    if not tax_id:
        return False
        
    # Remove spaces and common separators
    cleaned = re.sub(r'[\s\-\.]', '', tax_id)
    
    # Validate based on country
    if country_code == "US":
        # US EIN format: XX-XXXXXXX (9 digits)
        return bool(re.match(r'^[0-9]{9}$', cleaned))
    elif country_code == "GB":
        # UK VAT format: GB XXX XXXX XX or GBXXX XXXX XX (9 digits)
        return bool(re.match(r'^GB[0-9]{9}$', cleaned))
    elif country_code == "EU":
        # Generic EU VAT format: 2 letter country code + 8-12 characters
        return bool(re.match(r'^[A-Z]{2}[0-9A-Za-z]{8,12}$', cleaned))
    else:
        # Generic validation: at least 8 alphanumeric characters
        return bool(re.match(r'^[0-9A-Za-z]{8,}$', cleaned))


def generate_password(length: int = 12) -> str:
    """
    Generate a secure random password.
    
    Args:
        length: Length of the password
        
    Returns:
        A secure random password
    """
    # Ensure at least one of each: uppercase, lowercase, digit, special
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice('!@#$%^&*()-_=+[]{}|;:,.<>?')
    
    # Fill the rest with a mix of characters
    remaining_length = length - 4
    remaining_chars = ''.join(random.choices(
        string.ascii_uppercase + string.ascii_lowercase + string.digits + '!@#$%^&*()-_=+[]{}|;:,.<>?',
        k=remaining_length
    ))
    
    # Combine all parts and shuffle
    all_chars = uppercase + lowercase + digit + special + remaining_chars
    char_list = list(all_chars)
    random.shuffle(char_list)
    
    return ''.join(char_list)
