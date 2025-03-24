"""
Template rendering service for the billing module.
This module provides functions for rendering Jinja2 templates with data.
"""
import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import HTTPException

from backend_core.cache import (
    cache_set, cache_get, cache_delete,
    serialize, deserialize
)
from backend_core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Cache expiration times (in seconds)
TEMPLATE_CACHE_EXPIRY = 3600  # 1 hour

# Set up Jinja2 environment
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(templates_dir),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

# Custom filters
def format_currency(value):
    """Format a number as currency."""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

def date_filter(value, format="%Y-%m-%d"):
    """Format a date."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

def nl2br(value):
    """Convert newlines to <br> tags."""
    if not value:
        return ""
    return value.replace('\n', '<br>')

# Register filters
env.filters['format_currency'] = format_currency
env.filters['date'] = date_filter
env.filters['nl2br'] = nl2br

def get_template_cache_key(template_name: str, context_hash: str) -> str:
    """
    Generate a cache key for a rendered template.
    
    Args:
        template_name: Name of the template
        context_hash: Hash of the template context
        
    Returns:
        str: Cache key
    """
    return f"template:{template_name}:{context_hash}"

def hash_context(context: Dict[str, Any]) -> str:
    """
    Generate a hash for template context.
    
    Args:
        context: Template context
        
    Returns:
        str: Context hash
    """
    # Use a simple serialization of the context as a hash
    serialized = serialize(context)
    import hashlib
    return hashlib.md5(serialized.encode()).hexdigest()

def get_cached_template(template_name: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Get a cached template if available.
    
    Args:
        template_name: Name of the template
        context: Template context
        
    Returns:
        Optional[str]: Cached rendered template or None if not found
    """
    context_hash = hash_context(context)
    cache_key = get_template_cache_key(template_name, context_hash)
    return cache_get(cache_key)

def cache_template(template_name: str, context: Dict[str, Any], rendered_content: str) -> bool:
    """
    Cache a rendered template.
    
    Args:
        template_name: Name of the template
        context: Template context
        rendered_content: Rendered template content
        
    Returns:
        bool: True if successful, False otherwise
    """
    context_hash = hash_context(context)
    cache_key = get_template_cache_key(template_name, context_hash)
    return cache_set(cache_key, rendered_content, TEMPLATE_CACHE_EXPIRY)

def render_template(
    template_name: str,
    context: Dict[str, Any],
    use_cache: bool = True
) -> str:
    """
    Render a template with context.
    
    Args:
        template_name: Name of the template
        context: Template context
        use_cache: Whether to use cache
        
    Returns:
        str: Rendered template
    """
    if use_cache:
        # Try to get from cache
        cached_template = get_cached_template(template_name, context)
        if cached_template:
            logger.debug(f"Template cache hit for {template_name}")
            return cached_template
    
    try:
        # Add common context
        full_context = {
            "company_name": settings.COMPANY_NAME,
            "company_address": settings.COMPANY_ADDRESS,
            "company_email": settings.COMPANY_EMAIL,
            "company_phone": settings.COMPANY_PHONE,
            "company_website": settings.COMPANY_WEBSITE,
            "company_logo_url": settings.COMPANY_LOGO_URL,
            "support_email": settings.SUPPORT_EMAIL,
            "current_year": datetime.now().year,
            **context
        }
        
        # Render template
        template = env.get_template(template_name)
        rendered = template.render(**full_context)
        
        # Cache rendered template
        if use_cache:
            cache_template(template_name, context, rendered)
            
        return rendered
    except Exception as e:
        logger.error(f"Failed to render template {template_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Template rendering error: {str(e)}")

def render_invoice_template(invoice_data: Dict[str, Any], use_cache: bool = True) -> str:
    """
    Render an invoice template.
    
    Args:
        invoice_data: Invoice data
        use_cache: Whether to use cache
        
    Returns:
        str: Rendered invoice template
    """
    return render_template("invoices/invoice_template.html", invoice_data, use_cache)

def render_invoice_reminder_email(reminder_data: Dict[str, Any], use_cache: bool = True) -> str:
    """
    Render an invoice reminder email template.
    
    Args:
        reminder_data: Reminder data
        use_cache: Whether to use cache
        
    Returns:
        str: Rendered email template
    """
    return render_template("emails/invoice_reminder.html", reminder_data, use_cache)

def render_monthly_billing_report(report_data: Dict[str, Any], use_cache: bool = True) -> str:
    """
    Render a monthly billing report template.
    
    Args:
        report_data: Report data
        use_cache: Whether to use cache
        
    Returns:
        str: Rendered report template
    """
    return render_template("reports/monthly_billing_report.html", report_data, use_cache)

def invalidate_template_cache(template_name: str = None) -> bool:
    """
    Invalidate template cache.
    
    Args:
        template_name: Name of the template to invalidate (optional, if None, invalidate all)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if template_name:
        # Invalidate specific template
        # Note: This is a simplified approach that doesn't account for different context hashes
        pattern = f"template:{template_name}:*"
        return cache_delete(pattern)
    else:
        # Invalidate all templates
        pattern = "template:*"
        return cache_delete(pattern)
