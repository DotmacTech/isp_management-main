"""
Metrics collection and reporting for the ISP Management Platform.

This module provides utilities for collecting, aggregating, and reporting
metrics to monitoring systems like Prometheus, StatsD, or Elasticsearch.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import os
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

# Determine which metrics backend to use based on environment configuration
METRICS_BACKEND = os.environ.get("METRICS_BACKEND", "logging").lower()


class MetricsCollector:
    """
    Metrics collector for the ISP Management Platform.
    
    This class provides methods for collecting and reporting metrics
    to the configured monitoring backend.
    """
    
    def __init__(self, namespace: str):
        """
        Initialize the metrics collector.
        
        Args:
            namespace: Namespace for the metrics (e.g., module name)
        """
        self.namespace = namespace
        self.backend = METRICS_BACKEND
        self._initialize_backend()
    
    def _initialize_backend(self) -> None:
        """Initialize the metrics backend based on configuration."""
        # For testing purposes, if the environment is set to test, use logging backend
        if os.environ.get("TESTING", "false").lower() == "true":
            logger.info(f"Using logging metrics backend for {self.namespace} (test environment)")
            self.backend = "logging"
            return
            
        if self.backend == "prometheus":
            try:
                from prometheus_client import Counter, Gauge, Histogram, Summary
                
                self.counters = {}
                self.gauges = {}
                self.histograms = {}
                self.summaries = {}
                
                logger.info(f"Initialized Prometheus metrics backend for {self.namespace}")
            except ImportError:
                logger.warning("Prometheus client not installed, falling back to logging")
                self.backend = "logging"
        
        elif self.backend == "statsd":
            try:
                import statsd
                
                self.client = statsd.StatsClient(
                    host=os.environ.get("STATSD_HOST", "localhost"),
                    port=int(os.environ.get("STATSD_PORT", 8125)),
                    prefix=self.namespace
                )
                
                logger.info(f"Initialized StatsD metrics backend for {self.namespace}")
            except ImportError:
                logger.warning("StatsD client not installed, falling back to logging")
                self.backend = "logging"
        
        elif self.backend == "elasticsearch":
            try:
                from elasticsearch import Elasticsearch
                
                # Skip Elasticsearch initialization if we can't connect to it
                if os.environ.get("SKIP_ELASTICSEARCH", "false").lower() == "true":
                    logger.warning("Skipping Elasticsearch initialization, falling back to logging")
                    self.backend = "logging"
                    return
                
                self.client = Elasticsearch(
                    hosts=[os.environ.get("ELASTICSEARCH_HOST", "http://localhost:9200")],
                    basic_auth=(
                        os.environ.get("ELASTICSEARCH_USER", "elastic"),
                        os.environ.get("ELASTICSEARCH_PASSWORD", "changeme")
                    ),
                    request_timeout=5  # Short timeout for faster failure
                )
                self.index = f"metrics-{self.namespace}"
                
                # Test connection
                try:
                    if not self.client.ping():
                        logger.warning("Could not connect to Elasticsearch, falling back to logging")
                        self.backend = "logging"
                except Exception as e:
                    logger.warning(f"Error connecting to Elasticsearch: {e}, falling back to logging")
                    self.backend = "logging"
                else:
                    logger.info(f"Initialized Elasticsearch metrics backend for {self.namespace}")
            except ImportError:
                logger.warning("Elasticsearch client not installed, falling back to logging")
                self.backend = "logging"
        
        else:
            logger.info(f"Using logging metrics backend for {self.namespace}")
            self.backend = "logging"
    
    def _format_tags(self, tags: Dict[str, str]) -> str:
        """
        Format tags for logging.
        
        Args:
            tags: Dictionary of tags
            
        Returns:
            Formatted tags string
        """
        if not tags:
            return ""
        
        return ", ".join([f"{k}={v}" for k, v in tags.items()])
    
    def increment(self, metric: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric: Metric name
            value: Value to increment by
            tags: Optional tags for the metric
        """
        tags = tags or {}
        
        if self.backend == "prometheus":
            from prometheus_client import Counter
            
            # Create counter if it doesn't exist
            if metric not in self.counters:
                self.counters[metric] = Counter(
                    f"{self.namespace}_{metric}",
                    f"{metric} counter",
                    list(tags.keys())
                )
            
            # Increment counter
            self.counters[metric].labels(**tags).inc(value)
        
        elif self.backend == "statsd":
            # Format metric name with tags
            metric_name = metric
            if tags:
                tag_str = ",".join([f"{k}={v}" for k, v in tags.items()])
                metric_name = f"{metric}[{tag_str}]"
            
            # Increment counter
            self.client.incr(metric_name, value)
        
        elif self.backend == "elasticsearch":
            # Create document
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "counter",
                "metric": metric,
                "value": value,
                "tags": tags
            }
            
            # Index document
            try:
                self.client.index(index=self.index, document=doc)
            except Exception as e:
                logger.error(f"Error indexing metric to Elasticsearch: {str(e)}")
        
        else:
            # Log metric
            tags_str = self._format_tags(tags)
            logger.info(f"METRIC: {self.namespace}.{metric} +{value} {tags_str}")
    
    def gauge(self, metric: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            metric: Metric name
            value: Gauge value
            tags: Optional tags for the metric
        """
        tags = tags or {}
        
        if self.backend == "prometheus":
            from prometheus_client import Gauge
            
            # Create gauge if it doesn't exist
            if metric not in self.gauges:
                self.gauges[metric] = Gauge(
                    f"{self.namespace}_{metric}",
                    f"{metric} gauge",
                    list(tags.keys())
                )
            
            # Set gauge value
            self.gauges[metric].labels(**tags).set(value)
        
        elif self.backend == "statsd":
            # Format metric name with tags
            metric_name = metric
            if tags:
                tag_str = ",".join([f"{k}={v}" for k, v in tags.items()])
                metric_name = f"{metric}[{tag_str}]"
            
            # Set gauge value
            self.client.gauge(metric_name, value)
        
        elif self.backend == "elasticsearch":
            # Create document
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "gauge",
                "metric": metric,
                "value": value,
                "tags": tags
            }
            
            # Index document
            try:
                self.client.index(index=self.index, document=doc)
            except Exception as e:
                logger.error(f"Error indexing metric to Elasticsearch: {str(e)}")
        
        else:
            # Log metric
            tags_str = self._format_tags(tags)
            logger.info(f"METRIC: {self.namespace}.{metric} = {value} {tags_str}")
    
    def record(self, metric: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing or histogram metric.
        
        Args:
            metric: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        tags = tags or {}
        
        if self.backend == "prometheus":
            from prometheus_client import Histogram
            
            # Create histogram if it doesn't exist
            if metric not in self.histograms:
                self.histograms[metric] = Histogram(
                    f"{self.namespace}_{metric}",
                    f"{metric} histogram",
                    list(tags.keys())
                )
            
            # Record value
            self.histograms[metric].labels(**tags).observe(value)
        
        elif self.backend == "statsd":
            # Format metric name with tags
            metric_name = metric
            if tags:
                tag_str = ",".join([f"{k}={v}" for k, v in tags.items()])
                metric_name = f"{metric}[{tag_str}]"
            
            # Record timing
            self.client.timing(metric_name, value * 1000)  # Convert to milliseconds
        
        elif self.backend == "elasticsearch":
            # Create document
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "histogram",
                "metric": metric,
                "value": value,
                "tags": tags
            }
            
            # Index document
            try:
                self.client.index(index=self.index, document=doc)
            except Exception as e:
                logger.error(f"Error indexing metric to Elasticsearch: {str(e)}")
        
        else:
            # Log metric
            tags_str = self._format_tags(tags)
            logger.info(f"METRIC: {self.namespace}.{metric} = {value} {tags_str}")


def timed(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator for timing function execution.
    
    Args:
        metric_name: Name of the metric to record
        tags: Optional tags for the metric
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the namespace from the module name, safely
            try:
                module_parts = func.__module__.split(".")
                namespace = "test_metrics" if len(module_parts) < 2 else module_parts[-2]
            except (AttributeError, IndexError):
                namespace = "unknown"
            
            # Create metrics collector
            collector = MetricsCollector(namespace)
            
            # Record start time
            start_time = time.time()
            
            try:
                # Call the function
                result = func(*args, **kwargs)
                
                # Record success tag
                metric_tags = tags.copy() if tags else {}
                metric_tags["status"] = "success"
                
                return result
            except Exception as e:
                # Record error tag
                metric_tags = tags.copy() if tags else {}
                metric_tags["status"] = "error"
                metric_tags["error"] = str(e)
                
                # Re-raise the exception
                raise
            finally:
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Record metric
                collector.record(metric_name, execution_time, metric_tags)
        
        return wrapper
    
    return decorator
