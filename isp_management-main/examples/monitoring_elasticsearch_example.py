#!/usr/bin/env python3
"""
Example script demonstrating how to use the Elasticsearch monitoring integration.

This script shows how to:
1. Configure Elasticsearch settings
2. Create and search logs in Elasticsearch
3. Create and search metrics in Elasticsearch
4. Perform health checks and store results in Elasticsearch
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import random

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from isp_management.modules.monitoring.elasticsearch import elasticsearch_client
from isp_management.modules.monitoring.config import settings
from isp_management.modules.monitoring.models import LogLevel, MetricType
from isp_management.backend_core.database import SessionLocal
from isp_management.modules.monitoring.services import (
    LoggingService, 
    MetricsService, 
    MonitoringService
)
from isp_management.modules.monitoring.schemas import (
    ServiceLogCreate,
    SystemMetricCreate
)

# Configure Elasticsearch settings
os.environ["ELASTICSEARCH_ENABLED"] = "true"
os.environ["ELASTICSEARCH_HOSTS"] = "http://localhost:9200"
os.environ["ELASTICSEARCH_LOG_INDEX_PREFIX"] = "isp-logs"
os.environ["ELASTICSEARCH_METRIC_INDEX_PREFIX"] = "isp-metrics"


def main():
    """Main function to demonstrate Elasticsearch monitoring integration."""
    print("ISP Management Platform - Elasticsearch Monitoring Example")
    print("=" * 60)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize services
        logging_service = LoggingService(db)
        metrics_service = MetricsService(db)
        monitoring_service = MonitoringService(db)
        
        # Check if Elasticsearch is enabled
        if not settings.logging.elasticsearch.enabled:
            print("Elasticsearch is not enabled. Please set ELASTICSEARCH_ENABLED=true")
            return
        
        # Check Elasticsearch connection
        print("\nChecking Elasticsearch connection...")
        try:
            info = elasticsearch_client.client.info()
            print(f"Connected to Elasticsearch version {info['version']['number']}")
            print(f"Cluster name: {info['cluster_name']}")
        except Exception as e:
            print(f"Failed to connect to Elasticsearch: {e}")
            print("Please make sure Elasticsearch is running and accessible.")
            return
        
        # Create index templates
        print("\nCreating index templates...")
        elasticsearch_client.create_log_index_template()
        elasticsearch_client.create_metric_index_template()
        print("Index templates created successfully.")
        
        # Generate and index sample logs
        print("\nGenerating sample logs...")
        log_count = 10
        
        for i in range(log_count):
            # Create random log level
            log_level = random.choice([
                LogLevel.DEBUG,
                LogLevel.INFO,
                LogLevel.WARNING,
                LogLevel.ERROR
            ])
            
            # Create random service name
            service_name = random.choice([
                "api_gateway",
                "billing",
                "radius",
                "crm",
                "monitoring"
            ])
            
            # Create log message
            message = f"Sample log message {i+1} from {service_name}"
            
            # Create metadata
            metadata = {
                "sample_id": i+1,
                "timestamp": datetime.utcnow().isoformat(),
                "environment": "example"
            }
            
            # Create log
            log = ServiceLogCreate(
                service_name=service_name,
                log_level=log_level,
                message=message,
                metadata=metadata
            )
            
            # Save log to database and Elasticsearch
            db_log = logging_service.create_log(log)
            
            # Print log details
            print(f"Created log: {service_name} - {log_level.value} - {message}")
        
        # Generate and index sample metrics
        print("\nGenerating sample metrics...")
        metric_count = 10
        
        for i in range(metric_count):
            # Create random metric type
            metric_type = random.choice([
                MetricType.CPU_USAGE,
                MetricType.MEMORY_USAGE,
                MetricType.DISK_USAGE,
                MetricType.NETWORK_SENT,
                MetricType.NETWORK_RECEIVED
            ])
            
            # Create random service name
            service_name = random.choice([
                "api_gateway",
                "billing",
                "radius",
                "crm",
                "monitoring"
            ])
            
            # Create random host name
            host_name = random.choice([
                "server1",
                "server2",
                "server3",
                "server4",
                "server5"
            ])
            
            # Create random value based on metric type
            if metric_type in [MetricType.CPU_USAGE, MetricType.MEMORY_USAGE, MetricType.DISK_USAGE]:
                value = random.uniform(0, 100)
                unit = "percent"
            elif metric_type in [MetricType.NETWORK_SENT, MetricType.NETWORK_RECEIVED]:
                value = random.uniform(0, 1000000)
                unit = "bytes"
            else:
                value = random.uniform(0, 100)
                unit = "count"
            
            # Create tags
            tags = {
                "sample_id": i+1,
                "environment": "example"
            }
            
            # Create metric
            metric = SystemMetricCreate(
                service_name=service_name,
                host_name=host_name,
                metric_type=metric_type,
                value=value,
                unit=unit,
                tags=tags
            )
            
            # Save metric to database and Elasticsearch
            db_metric = metrics_service.create_metric(metric)
            
            # Print metric details
            print(f"Created metric: {service_name} - {host_name} - {metric_type.value} - {value:.2f} {unit}")
        
        # Perform health check
        print("\nPerforming health check...")
        health_check = monitoring_service.check_system_health()
        
        # Print health check results
        print(f"Overall status: {health_check.overall_status}")
        print("Component status:")
        for component_name, component_status in health_check.components.items():
            print(f"  {component_name}: {component_status.status}")
        
        # Search logs
        print("\nSearching logs...")
        logs = elasticsearch_client.search_logs(
            service_name="monitoring",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            limit=5
        )
        
        print(f"Found {len(logs)} logs:")
        for log in logs:
            print(f"  {log.get('timestamp')} - {log.get('service_name')} - {log.get('log_level')} - {log.get('message')}")
        
        # Search metrics
        print("\nSearching metrics...")
        metrics = elasticsearch_client.search_metrics(
            metric_type="cpu_usage",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            limit=5
        )
        
        print(f"Found {len(metrics)} metrics:")
        for metric in metrics:
            print(f"  {metric.get('timestamp')} - {metric.get('service_name')} - {metric.get('host_name')} - {metric.get('metric_type')} - {metric.get('value')} {metric.get('unit')}")
        
        # Demonstrate aggregations
        print("\nPerforming metric aggregations...")
        aggregations = elasticsearch_client.aggregate_metrics(
            metric_type="cpu_usage",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            interval="1m",
            aggregations=["avg", "min", "max"]
        )
        
        print(f"Aggregation results:")
        for bucket in aggregations.get("buckets", []):
            print(f"  {bucket.get('key_as_string')} - Avg: {bucket.get('avg_value'):.2f} - Min: {bucket.get('min_value'):.2f} - Max: {bucket.get('max_value'):.2f}")
        
        print("\nElasticsearch monitoring example completed successfully.")
    
    finally:
        # Close database session
        db.close()


if __name__ == "__main__":
    main()
