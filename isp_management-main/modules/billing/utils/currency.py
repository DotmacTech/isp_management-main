"""
Currency utilities for the billing module.

This module provides functions for currency formatting and conversion.
"""

import locale
from decimal import Decimal
from typing import Dict, Union, Optional


def format_currency(amount: Union[Decimal, float, int], currency: str = "USD") -> str:
    """
    Format currency amount with the appropriate symbol and decimal places.
    
    Args:
        amount: The amount to format
        currency: The currency code (default: USD)
        
    Returns:
        A formatted currency string
    """
    # Convert to Decimal for precision if not already
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Format based on currency
    currency_formats = {
        "USD": "${:.2f}",
        "EUR": "€{:.2f}",
        "GBP": "£{:.2f}",
        "JPY": "¥{:.0f}",  # JPY typically has no decimal places
        "CAD": "C${:.2f}",
        "AUD": "A${:.2f}",
        "CHF": "CHF {:.2f}",
        "CNY": "¥{:.2f}",
        "INR": "₹{:.2f}",
        "NGN": "₦{:.2f}",
    }
    
    # Use the appropriate format or a generic one if currency not found
    format_str = currency_formats.get(currency, "{:.2f} " + currency)
    
    return format_str.format(amount)


def convert_currency(
    amount: Union[Decimal, float, int],
    from_currency: str,
    to_currency: str,
    exchange_rates: Optional[Dict[str, float]] = None
) -> Decimal:
    """
    Convert an amount from one currency to another using exchange rates.
    
    Args:
        amount: The amount to convert
        from_currency: The source currency code
        to_currency: The target currency code
        exchange_rates: A dictionary of exchange rates relative to USD
                       (if None, will use default rates)
                       
    Returns:
        The converted amount as a Decimal
    """
    # Convert to Decimal for precision if not already
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # No conversion needed if currencies are the same
    if from_currency == to_currency:
        return amount
    
    # Use provided exchange rates or fallback to defaults
    # These are example rates - in a real system, these would be fetched from an API
    default_rates = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.75,
        "JPY": 110.0,
        "CAD": 1.25,
        "AUD": 1.35,
        "CHF": 0.92,
        "CNY": 6.45,
        "INR": 74.5,
        "NGN": 410.0,
    }
    
    rates = exchange_rates or default_rates
    
    # Ensure both currencies are in the rates dictionary
    if from_currency not in rates or to_currency not in rates:
        raise ValueError(f"Exchange rate not available for {from_currency} or {to_currency}")
    
    # Convert to USD as an intermediate step (if not already USD)
    usd_amount = amount
    if from_currency != "USD":
        usd_amount = amount / Decimal(str(rates[from_currency]))
    
    # Convert from USD to target currency (if not USD)
    if to_currency == "USD":
        return usd_amount
    else:
        return usd_amount * Decimal(str(rates[to_currency]))
