"""
Configuration initialization for the Monitoring module.

This module provides access to configuration settings for the monitoring module.
"""

from .settings import MonitoringSettings

# Export the settings instance for easy import
settings = MonitoringSettings()

__all__ = ["settings", "MonitoringSettings"]
