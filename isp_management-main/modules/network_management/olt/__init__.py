"""
OLT Management Module

This module provides functionality for managing Optical Line Terminals (OLTs)
from different vendors using a common adapter interface.
"""

from .factory import OLTAdapterFactory

__all__ = ['OLTAdapterFactory']
