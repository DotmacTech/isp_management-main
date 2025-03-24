"""
API versioning implementation for the API Gateway.

This module provides functionality to manage multiple API versions, allowing
for backward compatibility and smooth transitions between API versions.
"""

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from backend_core.config import settings


class VersioningStrategy(str, Enum):
    """Strategies for API versioning."""
    URL_PATH = "url_path"         # e.g., /v1/users
    QUERY_PARAM = "query_param"   # e.g., /users?version=1
    HEADER = "header"             # e.g., X-API-Version: 1
    CONTENT_TYPE = "content_type" # e.g., application/vnd.api.v1+json


class APIVersionManager:
    """
    Manager for API versioning.
    
    This class implements functionality to manage multiple API versions,
    supporting different versioning strategies and providing tools for
    deprecating and migrating between versions.
    """
    
    def __init__(self):
        """Initialize the API version manager."""
        self.logger = logging.getLogger("api_version_manager")
        self.versions: Dict[str, Dict] = {}
        self.default_version = "1"
        self.strategy = VersioningStrategy.URL_PATH
        self.header_name = "X-API-Version"
        self.query_param_name = "version"
    
    def configure(self, strategy: VersioningStrategy, default_version: str):
        """
        Configure the versioning strategy.
        
        Args:
            strategy: The versioning strategy to use
            default_version: The default API version
        """
        self.strategy = strategy
        self.default_version = default_version
        self.logger.info(f"Configured API versioning: strategy={strategy}, default={default_version}")
    
    def register_version(self, version: str, description: str, deprecated: bool = False):
        """
        Register an API version.
        
        Args:
            version: The API version (e.g., "1", "2")
            description: Description of this version
            deprecated: Whether this version is deprecated
        """
        self.versions[version] = {
            "version": version,
            "description": description,
            "deprecated": deprecated,
            "endpoints": set(),
        }
        self.logger.info(f"Registered API version {version}: {description}")
    
    def register_endpoint(self, version: str, path: str):
        """
        Register an endpoint for a specific API version.
        
        Args:
            version: The API version
            path: The endpoint path
        """
        if version not in self.versions:
            self.logger.warning(f"Attempted to register endpoint for unknown version: {version}")
            return
        
        self.versions[version]["endpoints"].add(path)
    
    def get_versioned_prefix(self, prefix: str, version: str) -> str:
        """
        Get a versioned URL prefix based on the configured strategy.
        
        Args:
            prefix: The original URL prefix
            version: The API version
            
        Returns:
            str: The versioned URL prefix
        """
        if self.strategy == VersioningStrategy.URL_PATH:
            # Add version to URL path
            return f"/v{version}{prefix}"
        
        # For other strategies, the prefix remains unchanged
        return prefix
    
    def extract_version(self, path: str, headers: Dict[str, str], query_params: Dict[str, str]) -> str:
        """
        Extract the API version from a request based on the configured strategy.
        
        Args:
            path: The request path
            headers: The request headers
            query_params: The request query parameters
            
        Returns:
            str: The extracted API version, or the default version if not found
        """
        if self.strategy == VersioningStrategy.URL_PATH:
            # Extract from URL path
            match = re.match(r"^/v([^/]+)", path)
            if match:
                return match.group(1)
        
        elif self.strategy == VersioningStrategy.QUERY_PARAM:
            # Extract from query parameter
            if self.query_param_name in query_params:
                return query_params[self.query_param_name]
        
        elif self.strategy == VersioningStrategy.HEADER:
            # Extract from header
            header_name = self.header_name.lower()
            if header_name in headers:
                return headers[header_name]
        
        elif self.strategy == VersioningStrategy.CONTENT_TYPE:
            # Extract from Content-Type header
            if "content-type" in headers:
                content_type = headers["content-type"]
                match = re.search(r"application/vnd\.api\.v([^+]+)\+json", content_type)
                if match:
                    return match.group(1)
        
        # Return default version if not found
        return self.default_version
    
    def is_deprecated(self, version: str) -> bool:
        """
        Check if an API version is deprecated.
        
        Args:
            version: The API version
            
        Returns:
            bool: True if the version is deprecated
        """
        if version not in self.versions:
            return False
        
        return self.versions[version]["deprecated"]
    
    def get_all_versions(self) -> List[Dict]:
        """
        Get information about all registered API versions.
        
        Returns:
            List[Dict]: Information about all versions
        """
        return [
            {
                "version": info["version"],
                "description": info["description"],
                "deprecated": info["deprecated"],
                "endpoint_count": len(info["endpoints"]),
            }
            for info in self.versions.values()
        ]
