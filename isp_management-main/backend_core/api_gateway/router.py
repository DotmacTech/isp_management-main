"""
Router implementation for the API Gateway.

This module provides routing functionality to direct API requests to the
appropriate microservices based on path, headers, or other criteria.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi.routing import APIRoute


@dataclass
class RouteMetrics:
    """Metrics for a route."""
    path: str
    methods: Set[str]
    service: str
    version: Optional[str]
    hit_count: int


class Router:
    """
    Router for directing API requests to appropriate services.
    
    This class implements routing functionality to direct requests based on
    path, headers, or other criteria, and maintains a registry of available
    routes.
    """
    
    def __init__(self):
        """Initialize the router."""
        self.logger = logging.getLogger("api_gateway_router")
        self.routes: Dict[str, Dict] = {}
        self.hit_counts: Dict[str, int] = {}
    
    def register_routes(self, routes: List[APIRoute], prefix: str, version: Optional[str] = None):
        """
        Register routes with the router.
        
        Args:
            routes: List of FastAPI routes
            prefix: URL prefix for the routes
            version: API version (optional)
        """
        for route in routes:
            path = f"{prefix}{route.path}"
            
            # Initialize hit count
            if path not in self.hit_counts:
                self.hit_counts[path] = 0
            
            # Store route information
            self.routes[path] = {
                "path": path,
                "methods": route.methods,
                "name": route.name,
                "service": prefix.strip("/"),
                "version": version,
                "endpoint": route.endpoint,
            }
            
            self.logger.info(f"Registered route: {path} ({', '.join(route.methods)})")
    
    def get_all_routes(self) -> List[Dict]:
        """
        Get all registered routes.
        
        Returns:
            List[Dict]: All registered routes
        """
        return [
            {
                "path": info["path"],
                "methods": list(info["methods"]),
                "name": info["name"],
                "service": info["service"],
                "version": info["version"],
            }
            for info in self.routes.values()
        ]
    
    def get_route_by_path(self, path: str) -> Optional[Dict]:
        """
        Get route information for a specific path.
        
        Args:
            path: The API path
            
        Returns:
            Optional[Dict]: Route information if found, None otherwise
        """
        # Check for exact match
        if path in self.routes:
            # Increment hit count
            self.hit_counts[path] += 1
            return self.routes[path]
        
        # Check for pattern matches
        for route_path, info in self.routes.items():
            # This is a simplified check - in a real implementation, we would
            # use a more sophisticated pattern matching algorithm
            if self._path_matches_pattern(path, route_path):
                # Increment hit count
                self.hit_counts[route_path] += 1
                return info
        
        return None
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches a pattern.
        
        Args:
            path: The actual path
            pattern: The pattern to match against
            
        Returns:
            bool: True if the path matches the pattern
        """
        # This is a simplified implementation - in a real system, we would
        # use a more sophisticated pattern matching algorithm
        
        # Convert FastAPI path pattern to regex pattern
        import re
        regex_pattern = pattern
        
        # Replace path parameters with regex patterns
        regex_pattern = re.sub(r"{([^}]+)}", r"([^/]+)", regex_pattern)
        
        # Add start and end anchors
        regex_pattern = f"^{regex_pattern}$"
        
        # Check if the path matches the pattern
        return bool(re.match(regex_pattern, path))
    
    def get_metrics(self) -> List[RouteMetrics]:
        """
        Get metrics for all routes.
        
        Returns:
            List[RouteMetrics]: Route metrics
        """
        metrics = []
        
        for path, info in self.routes.items():
            metrics.append(RouteMetrics(
                path=path,
                methods=set(info["methods"]),
                service=info["service"],
                version=info["version"],
                hit_count=self.hit_counts.get(path, 0)
            ))
        
        return metrics
