"""
Configuration management for the UNMS module.

This module provides configuration loading, validation, and access.
"""

from .settings import get_config, UNMSConfig

__all__ = ["get_config", "UNMSConfig"]
