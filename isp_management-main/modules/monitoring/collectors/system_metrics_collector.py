"""
System Metrics Collector for ISP Management Platform.

This module collects system metrics including CPU, memory, disk, and network usage
from various components of the ISP Management Platform.
"""

import os
import logging
import time
import psutil
import socket
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from modules.monitoring.models import SystemMetric, MetricType
from modules.monitoring.schemas import SystemMetricCreate
from modules.monitoring.services.metrics_service import MetricsService
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "60"))  # seconds
HOSTNAME = socket.gethostname()


class SystemMetricsCollector:
    """
    Collector for system metrics.
    
    This class is responsible for collecting various system metrics including:
    - CPU usage (overall and per core)
    - Memory usage
    - Disk usage (overall and per mount point)
    - Network bandwidth (sent/received)
    - Process-specific metrics
    """

    def __init__(self, db: Session):
        """Initialize the collector with database session."""
        self.db = db
        self.metrics_service = MetricsService(db)
        self.es_client = ElasticsearchClient()
        self.hostname = HOSTNAME
        self.platform_info = self._get_platform_info()
        
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get platform information."""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        
    def collect_cpu_metrics(self) -> List[SystemMetricCreate]:
        """
        Collect CPU usage metrics.
        
        Returns:
            List of SystemMetricCreate objects
        """
        metrics = []
        
        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.CPU_USAGE,
                value=cpu_percent,
                unit="%",
                tags={"type": "overall"},
                timestamp=datetime.utcnow()
            )
        )
        
        # Per-core CPU usage
        per_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        for i, cpu_percent in enumerate(per_cpu_percent):
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.CPU_USAGE,
                    value=cpu_percent,
                    unit="%",
                    tags={"type": "per_core", "core": str(i)},
                    timestamp=datetime.utcnow()
                )
            )
            
        # CPU load averages (on Unix systems)
        if hasattr(psutil, "getloadavg"):
            load_1, load_5, load_15 = psutil.getloadavg()
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.CPU_USAGE,
                    value=load_1,
                    unit="load",
                    tags={"type": "load_average", "interval": "1min"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.CPU_USAGE,
                    value=load_5,
                    unit="load",
                    tags={"type": "load_average", "interval": "5min"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.CPU_USAGE,
                    value=load_15,
                    unit="load",
                    tags={"type": "load_average", "interval": "15min"},
                    timestamp=datetime.utcnow()
                )
            )
            
        return metrics
        
    def collect_memory_metrics(self) -> List[SystemMetricCreate]:
        """
        Collect memory usage metrics.
        
        Returns:
            List of SystemMetricCreate objects
        """
        metrics = []
        
        # Virtual memory
        virtual_memory = psutil.virtual_memory()
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.MEMORY_USAGE,
                value=virtual_memory.percent,
                unit="%",
                tags={"type": "virtual", "subtype": "percent"},
                timestamp=datetime.utcnow()
            )
        )
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.MEMORY_USAGE,
                value=virtual_memory.used / (1024 * 1024),  # Convert to MB
                unit="MB",
                tags={"type": "virtual", "subtype": "used"},
                timestamp=datetime.utcnow()
            )
        )
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.MEMORY_USAGE,
                value=virtual_memory.total / (1024 * 1024),  # Convert to MB
                unit="MB",
                tags={"type": "virtual", "subtype": "total"},
                timestamp=datetime.utcnow()
            )
        )
        
        # Swap memory
        swap_memory = psutil.swap_memory()
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.MEMORY_USAGE,
                value=swap_memory.percent,
                unit="%",
                tags={"type": "swap", "subtype": "percent"},
                timestamp=datetime.utcnow()
            )
        )
        metrics.append(
            SystemMetricCreate(
                service_name="system",
                host_name=self.hostname,
                metric_type=MetricType.MEMORY_USAGE,
                value=swap_memory.used / (1024 * 1024),  # Convert to MB
                unit="MB",
                tags={"type": "swap", "subtype": "used"},
                timestamp=datetime.utcnow()
            )
        )
        
        return metrics
        
    def collect_disk_metrics(self) -> List[SystemMetricCreate]:
        """
        Collect disk usage metrics.
        
        Returns:
            List of SystemMetricCreate objects
        """
        metrics = []
        
        # Disk partitions
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.DISK_USAGE,
                        value=usage.percent,
                        unit="%",
                        tags={
                            "mountpoint": partition.mountpoint,
                            "device": partition.device,
                            "fstype": partition.fstype,
                            "subtype": "percent"
                        },
                        timestamp=datetime.utcnow()
                    )
                )
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.DISK_USAGE,
                        value=usage.used / (1024 * 1024 * 1024),  # Convert to GB
                        unit="GB",
                        tags={
                            "mountpoint": partition.mountpoint,
                            "device": partition.device,
                            "fstype": partition.fstype,
                            "subtype": "used"
                        },
                        timestamp=datetime.utcnow()
                    )
                )
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.DISK_USAGE,
                        value=usage.total / (1024 * 1024 * 1024),  # Convert to GB
                        unit="GB",
                        tags={
                            "mountpoint": partition.mountpoint,
                            "device": partition.device,
                            "fstype": partition.fstype,
                            "subtype": "total"
                        },
                        timestamp=datetime.utcnow()
                    )
                )
            except (PermissionError, FileNotFoundError):
                # Skip partitions that can't be accessed
                continue
                
        # Disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.DISK_USAGE,
                    value=disk_io.read_bytes / (1024 * 1024),  # Convert to MB
                    unit="MB",
                    tags={"type": "io", "subtype": "read_bytes"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.DISK_USAGE,
                    value=disk_io.write_bytes / (1024 * 1024),  # Convert to MB
                    unit="MB",
                    tags={"type": "io", "subtype": "write_bytes"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.DISK_USAGE,
                    value=disk_io.read_count,
                    unit="count",
                    tags={"type": "io", "subtype": "read_count"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.DISK_USAGE,
                    value=disk_io.write_count,
                    unit="count",
                    tags={"type": "io", "subtype": "write_count"},
                    timestamp=datetime.utcnow()
                )
            )
        except (AttributeError, PermissionError):
            # Skip disk I/O if not available
            pass
            
        return metrics
        
    def collect_network_metrics(self) -> List[SystemMetricCreate]:
        """
        Collect network usage metrics.
        
        Returns:
            List of SystemMetricCreate objects
        """
        metrics = []
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.bytes_sent / (1024 * 1024),  # Convert to MB
                    unit="MB",
                    tags={"type": "io", "subtype": "bytes_sent"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.bytes_recv / (1024 * 1024),  # Convert to MB
                    unit="MB",
                    tags={"type": "io", "subtype": "bytes_recv"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.packets_sent,
                    unit="count",
                    tags={"type": "io", "subtype": "packets_sent"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.packets_recv,
                    unit="count",
                    tags={"type": "io", "subtype": "packets_recv"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.errin,
                    unit="count",
                    tags={"type": "io", "subtype": "errors_in"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=net_io.errout,
                    unit="count",
                    tags={"type": "io", "subtype": "errors_out"},
                    timestamp=datetime.utcnow()
                )
            )
        except (AttributeError, PermissionError):
            # Skip network I/O if not available
            pass
            
        # Per-interface network I/O
        try:
            net_io_per_nic = psutil.net_io_counters(pernic=True)
            for interface, counters in net_io_per_nic.items():
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.NETWORK_BANDWIDTH,
                        value=counters.bytes_sent / (1024 * 1024),  # Convert to MB
                        unit="MB",
                        tags={"type": "io", "subtype": "bytes_sent", "interface": interface},
                        timestamp=datetime.utcnow()
                    )
                )
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.NETWORK_BANDWIDTH,
                        value=counters.bytes_recv / (1024 * 1024),  # Convert to MB
                        unit="MB",
                        tags={"type": "io", "subtype": "bytes_recv", "interface": interface},
                        timestamp=datetime.utcnow()
                    )
                )
        except (AttributeError, PermissionError):
            # Skip per-interface network I/O if not available
            pass
            
        # Network connections
        try:
            connections = psutil.net_connections()
            connection_count = len(connections)
            established_count = sum(1 for conn in connections if conn.status == 'ESTABLISHED')
            listen_count = sum(1 for conn in connections if conn.status == 'LISTEN')
            
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=connection_count,
                    unit="count",
                    tags={"type": "connections", "subtype": "total"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=established_count,
                    unit="count",
                    tags={"type": "connections", "subtype": "established"},
                    timestamp=datetime.utcnow()
                )
            )
            metrics.append(
                SystemMetricCreate(
                    service_name="system",
                    host_name=self.hostname,
                    metric_type=MetricType.NETWORK_BANDWIDTH,
                    value=listen_count,
                    unit="count",
                    tags={"type": "connections", "subtype": "listening"},
                    timestamp=datetime.utcnow()
                )
            )
        except (AttributeError, PermissionError):
            # Skip network connections if not available
            pass
            
        return metrics
        
    def collect_process_metrics(self, process_names: List[str] = None) -> List[SystemMetricCreate]:
        """
        Collect process-specific metrics.
        
        Args:
            process_names: List of process names to monitor (None for all)
            
        Returns:
            List of SystemMetricCreate objects
        """
        metrics = []
        
        # Get all processes
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name']
                
                # Skip if not in the list of processes to monitor
                if process_names and proc_name not in process_names:
                    continue
                    
                # Get detailed process info
                process = psutil.Process(proc_info['pid'])
                
                # CPU usage
                cpu_percent = proc_info['cpu_percent'] or process.cpu_percent(interval=0.1)
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.CPU_USAGE,
                        value=cpu_percent,
                        unit="%",
                        tags={
                            "type": "process",
                            "process_name": proc_name,
                            "pid": str(proc_info['pid']),
                            "username": proc_info['username']
                        },
                        timestamp=datetime.utcnow()
                    )
                )
                
                # Memory usage
                memory_percent = proc_info['memory_percent'] or process.memory_percent()
                memory_info = process.memory_info()
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.MEMORY_USAGE,
                        value=memory_percent,
                        unit="%",
                        tags={
                            "type": "process",
                            "process_name": proc_name,
                            "pid": str(proc_info['pid']),
                            "username": proc_info['username']
                        },
                        timestamp=datetime.utcnow()
                    )
                )
                metrics.append(
                    SystemMetricCreate(
                        service_name="system",
                        host_name=self.hostname,
                        metric_type=MetricType.MEMORY_USAGE,
                        value=memory_info.rss / (1024 * 1024),  # Convert to MB
                        unit="MB",
                        tags={
                            "type": "process",
                            "process_name": proc_name,
                            "pid": str(proc_info['pid']),
                            "username": proc_info['username'],
                            "subtype": "rss"
                        },
                        timestamp=datetime.utcnow()
                    )
                )
                
                # I/O counters
                try:
                    io_counters = process.io_counters()
                    metrics.append(
                        SystemMetricCreate(
                            service_name="system",
                            host_name=self.hostname,
                            metric_type=MetricType.DISK_USAGE,
                            value=io_counters.read_bytes / (1024 * 1024),  # Convert to MB
                            unit="MB",
                            tags={
                                "type": "process",
                                "process_name": proc_name,
                                "pid": str(proc_info['pid']),
                                "username": proc_info['username'],
                                "subtype": "read_bytes"
                            },
                            timestamp=datetime.utcnow()
                        )
                    )
                    metrics.append(
                        SystemMetricCreate(
                            service_name="system",
                            host_name=self.hostname,
                            metric_type=MetricType.DISK_USAGE,
                            value=io_counters.write_bytes / (1024 * 1024),  # Convert to MB
                            unit="MB",
                            tags={
                                "type": "process",
                                "process_name": proc_name,
                                "pid": str(proc_info['pid']),
                                "username": proc_info['username'],
                                "subtype": "write_bytes"
                            },
                            timestamp=datetime.utcnow()
                        )
                    )
                except (psutil.AccessDenied, AttributeError):
                    # Skip I/O counters if not available
                    pass
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes that can't be accessed
                continue
                
        return metrics
        
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all system metrics.
        
        Returns:
            Dictionary with collection results
        """
        logger.info("Starting system metrics collection")
        start_time = time.time()
        
        all_metrics = []
        
        # Collect CPU metrics
        try:
            cpu_metrics = self.collect_cpu_metrics()
            all_metrics.extend(cpu_metrics)
            logger.debug(f"Collected {len(cpu_metrics)} CPU metrics")
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {str(e)}")
            
        # Collect memory metrics
        try:
            memory_metrics = self.collect_memory_metrics()
            all_metrics.extend(memory_metrics)
            logger.debug(f"Collected {len(memory_metrics)} memory metrics")
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {str(e)}")
            
        # Collect disk metrics
        try:
            disk_metrics = self.collect_disk_metrics()
            all_metrics.extend(disk_metrics)
            logger.debug(f"Collected {len(disk_metrics)} disk metrics")
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {str(e)}")
            
        # Collect network metrics
        try:
            network_metrics = self.collect_network_metrics()
            all_metrics.extend(network_metrics)
            logger.debug(f"Collected {len(network_metrics)} network metrics")
        except Exception as e:
            logger.error(f"Error collecting network metrics: {str(e)}")
            
        # Collect process metrics for important processes
        important_processes = [
            "python", "postgres", "redis-server", "elasticsearch", "kibana", "nginx", "celery"
        ]
        try:
            process_metrics = self.collect_process_metrics(important_processes)
            all_metrics.extend(process_metrics)
            logger.debug(f"Collected {len(process_metrics)} process metrics")
        except Exception as e:
            logger.error(f"Error collecting process metrics: {str(e)}")
            
        # Save metrics to database
        saved_count = 0
        for metric in all_metrics:
            try:
                self.metrics_service.create_metric(metric)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving metric: {str(e)}")
                
        # Calculate execution time
        execution_time = time.time() - start_time
        
        result = {
            "total_metrics": len(all_metrics),
            "saved_metrics": saved_count,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"System metrics collection completed in {execution_time:.2f} seconds. "
                   f"Collected {len(all_metrics)} metrics, saved {saved_count}.")
        
        return result


def collect_system_metrics(db: Session) -> Dict[str, Any]:
    """
    Collect system metrics.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with collection results
    """
    collector = SystemMetricsCollector(db)
    return collector.collect_all_metrics()


def sync_system_metrics_to_elasticsearch(db: Session, limit: int = 100) -> Dict[str, Any]:
    """
    Sync unsynced system metrics to Elasticsearch.
    
    Args:
        db: Database session
        limit: Maximum number of metrics to sync
        
    Returns:
        Dictionary with sync results
    """
    es_client = ElasticsearchClient()
    
    # Get unsynced metrics
    from sqlalchemy import select
    from modules.monitoring.models import SystemMetric
    
    stmt = select(SystemMetric).where(SystemMetric.elasticsearch_synced == False).limit(limit)
    result = db.execute(stmt)
    metrics = result.scalars().all()
    
    if not metrics:
        return {"synced": 0, "message": "No unsynced metrics found"}
    
    # Prepare metrics for bulk indexing
    bulk_data = []
    for metric in metrics:
        bulk_data.append({
            "index": {
                "_index": "system-metrics",
                "_id": str(metric.id)
            }
        })
        bulk_data.append({
            "id": metric.id,
            "service_name": metric.service_name,
            "host_name": metric.host_name,
            "metric_type": metric.metric_type.value,
            "value": metric.value,
            "unit": metric.unit,
            "tags": metric.tags,
            "timestamp": metric.timestamp.isoformat(),
            "sampling_rate": metric.sampling_rate
        })
    
    # Bulk index to Elasticsearch
    if bulk_data:
        response = es_client.bulk_index(bulk_data)
        
        # Update synced status in database
        for metric in metrics:
            metric.elasticsearch_synced = True
        db.commit()
        
        return {
            "synced": len(metrics),
            "message": f"Successfully synced {len(metrics)} metrics to Elasticsearch"
        }
    
    return {"synced": 0, "message": "No metrics to sync"}


def cleanup_old_system_metrics(db: Session, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old system metrics from the database.
    
    Args:
        db: Database session
        days_to_keep: Number of days to keep metrics
        
    Returns:
        Dictionary with cleanup results
    """
    from sqlalchemy import delete
    from modules.monitoring.models import SystemMetric
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    stmt = delete(SystemMetric).where(SystemMetric.timestamp < cutoff_date)
    result = db.execute(stmt)
    db.commit()
    
    return {
        "deleted": result.rowcount,
        "message": f"Deleted {result.rowcount} metrics older than {days_to_keep} days"
    }
