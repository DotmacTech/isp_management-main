#!/usr/bin/env python3
"""
Network Performance Collector for ISP Management Platform

This module collects network performance metrics from various sources and sends them
to Elasticsearch for monitoring and alerting purposes.
"""

import os
import time
import logging
import subprocess
import json
import socket
import ipaddress
from datetime import datetime
import random  # For demo/testing purposes only
from typing import Dict, List, Any, Optional, Union

import requests
from sqlalchemy.orm import Session

from modules.monitoring.elasticsearch import ElasticsearchClient
from modules.core.database import get_db
from modules.monitoring.models import SystemMetric, NetworkNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkPerformanceCollector:
    """Collects network performance metrics and sends them to Elasticsearch."""

    def __init__(self, db_session: Session):
        """
        Initialize the collector.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.es_client = ElasticsearchClient()
        self.metrics: List[Dict[str, Any]] = []
        
        # Load configuration
        self.config = {
            "ping_count": int(os.getenv("PING_COUNT", "5")),
            "ping_timeout": int(os.getenv("PING_TIMEOUT", "2")),
            "traceroute_timeout": int(os.getenv("TRACEROUTE_TIMEOUT", "5")),
            "collection_interval": int(os.getenv("COLLECTION_INTERVAL", "300")),
            "snmp_community": os.getenv("SNMP_COMMUNITY", "public"),
            "snmp_version": os.getenv("SNMP_VERSION", "2c"),
            "snmp_timeout": int(os.getenv("SNMP_TIMEOUT", "5")),
        }

    def collect_latency(self, target_ip: str, node_id: str) -> Dict[str, Any]:
        """
        Collect network latency metrics using ping.
        
        Args:
            target_ip: IP address to ping
            node_id: Identifier for the network node
            
        Returns:
            Dictionary containing latency metrics
        """
        try:
            # In production, use actual ping command
            # For demo/testing, generate random values
            avg_latency = random.uniform(5.0, 100.0)
            min_latency = avg_latency * 0.8
            max_latency = avg_latency * 1.2
            
            # In production, use this:
            # cmd = ["ping", "-c", str(self.config["ping_count"]), "-W", 
            #        str(self.config["ping_timeout"]), target_ip]
            # result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse the output to extract min/avg/max latency
            
            return {
                "metric_type": "NETWORK_LATENCY",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "target_ip": target_ip,
                "value": avg_latency,
                "min_latency": min_latency,
                "max_latency": max_latency,
                "unit": "ms",
                "metadata": {
                    "collection_method": "ping",
                    "ping_count": self.config["ping_count"]
                }
            }
        except Exception as e:
            logger.error(f"Error collecting latency for {target_ip}: {str(e)}")
            return {
                "metric_type": "NETWORK_LATENCY",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "target_ip": target_ip,
                "value": -1,
                "error": str(e),
                "unit": "ms",
                "metadata": {
                    "collection_method": "ping",
                    "ping_count": self.config["ping_count"],
                    "error": True
                }
            }

    def collect_packet_loss(self, target_ip: str, node_id: str) -> Dict[str, Any]:
        """
        Collect packet loss metrics using ping.
        
        Args:
            target_ip: IP address to ping
            node_id: Identifier for the network node
            
        Returns:
            Dictionary containing packet loss metrics
        """
        try:
            # In production, use actual ping command
            # For demo/testing, generate random values
            packet_loss = random.uniform(0.0, 5.0)
            
            # In production, use this:
            # cmd = ["ping", "-c", str(self.config["ping_count"]), "-W", 
            #        str(self.config["ping_timeout"]), target_ip]
            # result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse the output to extract packet loss percentage
            
            return {
                "metric_type": "NETWORK_PACKET_LOSS",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "target_ip": target_ip,
                "value": packet_loss,
                "unit": "%",
                "metadata": {
                    "collection_method": "ping",
                    "ping_count": self.config["ping_count"]
                }
            }
        except Exception as e:
            logger.error(f"Error collecting packet loss for {target_ip}: {str(e)}")
            return {
                "metric_type": "NETWORK_PACKET_LOSS",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "target_ip": target_ip,
                "value": 100.0,
                "error": str(e),
                "unit": "%",
                "metadata": {
                    "collection_method": "ping",
                    "ping_count": self.config["ping_count"],
                    "error": True
                }
            }

    def collect_bandwidth_utilization(self, node_id: str, interface: str = "eth0") -> Dict[str, Any]:
        """
        Collect bandwidth utilization metrics using SNMP or API.
        
        Args:
            node_id: Identifier for the network node
            interface: Network interface to monitor
            
        Returns:
            Dictionary containing bandwidth utilization metrics
        """
        try:
            # In production, use actual SNMP or API calls
            # For demo/testing, generate random values
            utilization = random.uniform(10.0, 95.0)
            
            return {
                "metric_type": "NETWORK_BANDWIDTH_UTILIZATION",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "interface": interface,
                "value": utilization,
                "unit": "%",
                "metadata": {
                    "collection_method": "snmp",
                    "snmp_version": self.config["snmp_version"],
                    "interface": interface
                }
            }
        except Exception as e:
            logger.error(f"Error collecting bandwidth utilization for {node_id}: {str(e)}")
            return {
                "metric_type": "NETWORK_BANDWIDTH_UTILIZATION",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "interface": interface,
                "value": -1,
                "error": str(e),
                "unit": "%",
                "metadata": {
                    "collection_method": "snmp",
                    "snmp_version": self.config["snmp_version"],
                    "interface": interface,
                    "error": True
                }
            }

    def collect_connection_count(self, node_id: str) -> Dict[str, Any]:
        """
        Collect connection count metrics.
        
        Args:
            node_id: Identifier for the network node
            
        Returns:
            Dictionary containing connection count metrics
        """
        try:
            # In production, use actual commands or API calls
            # For demo/testing, generate random values
            connection_count = random.randint(100, 10000)
            
            return {
                "metric_type": "NETWORK_CONNECTION_COUNT",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "value": connection_count,
                "unit": "connections",
                "metadata": {
                    "collection_method": "netstat"
                }
            }
        except Exception as e:
            logger.error(f"Error collecting connection count for {node_id}: {str(e)}")
            return {
                "metric_type": "NETWORK_CONNECTION_COUNT",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": node_id,
                "value": -1,
                "error": str(e),
                "unit": "connections",
                "metadata": {
                    "collection_method": "netstat",
                    "error": True
                }
            }

    def collect_service_availability(self, service_name: str, endpoint: str) -> Dict[str, Any]:
        """
        Collect service availability metrics.
        
        Args:
            service_name: Name of the service to check
            endpoint: Endpoint URL or IP:port to check
            
        Returns:
            Dictionary containing service availability metrics
        """
        try:
            start_time = time.time()
            
            # In production, use actual HTTP requests or socket connections
            # For demo/testing, generate random values
            is_available = random.random() > 0.05  # 95% chance of being available
            response_time = random.uniform(5.0, 500.0) if is_available else -1
            
            # In production, use this:
            # if endpoint.startswith(('http://', 'https://')):
            #     response = requests.get(endpoint, timeout=5)
            #     is_available = 200 <= response.status_code < 300
            #     response_time = (time.time() - start_time) * 1000
            # else:
            #     host, port = endpoint.split(':')
            #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #     sock.settimeout(5)
            #     result = sock.connect_ex((host, int(port)))
            #     is_available = result == 0
            #     response_time = (time.time() - start_time) * 1000
            #     sock.close()
            
            return {
                "metric_type": "SERVICE_UPTIME",
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": service_name,
                "endpoint": endpoint,
                "value": 100.0 if is_available else 0.0,
                "status": "UP" if is_available else "DOWN",
                "response_time": response_time,
                "unit": "%",
                "metadata": {
                    "collection_method": "http_check" if endpoint.startswith(('http://', 'https://')) else "socket_check"
                }
            }
        except Exception as e:
            logger.error(f"Error checking service availability for {service_name} at {endpoint}: {str(e)}")
            return {
                "metric_type": "SERVICE_UPTIME",
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": service_name,
                "endpoint": endpoint,
                "value": 0.0,
                "status": "ERROR",
                "response_time": -1,
                "error": str(e),
                "unit": "%",
                "metadata": {
                    "collection_method": "http_check" if endpoint.startswith(('http://', 'https://')) else "socket_check",
                    "error": True
                }
            }

    def collect_customer_data_usage(self, customer_id: str) -> Dict[str, Any]:
        """
        Collect customer data usage metrics.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Dictionary containing customer data usage metrics
        """
        try:
            # In production, query the database or RADIUS logs
            # For demo/testing, generate random values
            data_usage = random.uniform(1, 500) * 1024 * 1024  # 1-500 MB
            quota = 1024 * 1024 * 1024  # 1 GB
            quota_percentage = (data_usage / quota) * 100
            
            return {
                "metric_type": "CUSTOMER_DATA_USAGE",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "value": data_usage,
                "unit": "bytes",
                "metadata": {
                    "collection_method": "radius_logs",
                    "traffic_type": random.choice(["web", "streaming", "download", "other"]),
                    "quota": quota,
                    "quota_percentage": quota_percentage,
                    "plan_type": random.choice(["basic", "standard", "premium", "business"])
                }
            }
        except Exception as e:
            logger.error(f"Error collecting data usage for customer {customer_id}: {str(e)}")
            return {
                "metric_type": "CUSTOMER_DATA_USAGE",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "value": -1,
                "error": str(e),
                "unit": "bytes",
                "metadata": {
                    "collection_method": "radius_logs",
                    "error": True
                }
            }

    def collect_customer_session_count(self, customer_id: str) -> Dict[str, Any]:
        """
        Collect customer session count metrics.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Dictionary containing customer session count metrics
        """
        try:
            # In production, query the database or RADIUS logs
            # For demo/testing, generate random values
            session_count = random.randint(1, 10)
            
            return {
                "metric_type": "CUSTOMER_SESSION_COUNT",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "value": session_count,
                "unit": "sessions",
                "metadata": {
                    "collection_method": "radius_logs",
                    "plan_type": random.choice(["basic", "standard", "premium", "business"])
                }
            }
        except Exception as e:
            logger.error(f"Error collecting session count for customer {customer_id}: {str(e)}")
            return {
                "metric_type": "CUSTOMER_SESSION_COUNT",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": customer_id,
                "value": -1,
                "error": str(e),
                "unit": "sessions",
                "metadata": {
                    "collection_method": "radius_logs",
                    "error": True
                }
            }

    def collect_all_metrics(self) -> None:
        """Collect all network performance metrics."""
        logger.info("Starting network performance metrics collection")
        self.metrics = []
        
        try:
            # Get all network nodes from the database
            network_nodes = self.db_session.query(NetworkNode).all()
            
            if not network_nodes:
                # For demo/testing, create some dummy nodes
                network_nodes = [
                    {"id": "router-1", "ip_address": "192.168.1.1", "type": "router"},
                    {"id": "switch-1", "ip_address": "192.168.1.2", "type": "switch"},
                    {"id": "ap-1", "ip_address": "192.168.1.3", "type": "access_point"},
                    {"id": "server-1", "ip_address": "192.168.1.10", "type": "server"}
                ]
            
            # Collect metrics for each network node
            for node in network_nodes:
                node_id = node.id if hasattr(node, 'id') else node["id"]
                ip_address = node.ip_address if hasattr(node, 'ip_address') else node["ip_address"]
                
                # Collect various metrics
                self.metrics.append(self.collect_latency(ip_address, node_id))
                self.metrics.append(self.collect_packet_loss(ip_address, node_id))
                self.metrics.append(self.collect_bandwidth_utilization(node_id))
                self.metrics.append(self.collect_connection_count(node_id))
            
            # Collect service availability metrics
            services = [
                {"name": "radius", "endpoint": "192.168.1.20:1812"},
                {"name": "billing", "endpoint": "http://192.168.1.21:8080/api/health"},
                {"name": "crm", "endpoint": "http://192.168.1.22:8080/api/health"},
                {"name": "dns", "endpoint": "192.168.1.23:53"}
            ]
            
            for service in services:
                self.metrics.append(self.collect_service_availability(service["name"], service["endpoint"]))
            
            # Collect customer usage metrics
            # In production, get customer IDs from the database
            customer_ids = [f"customer-{i}" for i in range(1, 21)]  # 20 customers
            
            for customer_id in customer_ids:
                self.metrics.append(self.collect_customer_data_usage(customer_id))
                self.metrics.append(self.collect_customer_session_count(customer_id))
            
            logger.info(f"Collected {len(self.metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Error during metrics collection: {str(e)}")
    
    def save_to_database(self) -> None:
        """Save collected metrics to the database."""
        try:
            for metric in self.metrics:
                # Create a SystemMetric object for each metric
                system_metric = SystemMetric(
                    metric_type=metric["metric_type"],
                    timestamp=datetime.fromisoformat(metric["timestamp"]),
                    value=float(metric["value"]),
                    unit=metric["unit"],
                    metadata=json.dumps(metric["metadata"]) if "metadata" in metric else None
                )
                
                # Add additional fields based on metric type
                if metric["metric_type"] in ["NETWORK_LATENCY", "NETWORK_PACKET_LOSS"]:
                    system_metric.node_id = metric["node_id"]
                    system_metric.target = metric["target_ip"]
                elif metric["metric_type"] == "NETWORK_BANDWIDTH_UTILIZATION":
                    system_metric.node_id = metric["node_id"]
                    system_metric.interface = metric["interface"]
                elif metric["metric_type"] == "NETWORK_CONNECTION_COUNT":
                    system_metric.node_id = metric["node_id"]
                elif metric["metric_type"] == "SERVICE_UPTIME":
                    system_metric.service_name = metric["service_name"]
                    system_metric.endpoint = metric["endpoint"]
                    system_metric.status = metric["status"]
                elif metric["metric_type"] in ["CUSTOMER_DATA_USAGE", "CUSTOMER_SESSION_COUNT"]:
                    system_metric.customer_id = metric["customer_id"]
                
                self.db_session.add(system_metric)
            
            self.db_session.commit()
            logger.info(f"Saved {len(self.metrics)} metrics to database")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving metrics to database: {str(e)}")
    
    def send_to_elasticsearch(self) -> None:
        """Send collected metrics to Elasticsearch."""
        if not self.metrics:
            logger.warning("No metrics to send to Elasticsearch")
            return
        
        try:
            # Use the ElasticsearchClient to bulk index metrics
            self.es_client.bulk_index_metrics(self.metrics)
            logger.info(f"Sent {len(self.metrics)} metrics to Elasticsearch")
            
        except Exception as e:
            logger.error(f"Error sending metrics to Elasticsearch: {str(e)}")
    
    def run(self) -> None:
        """Run the collector in a loop."""
        logger.info("Starting network performance collector")
        
        try:
            while True:
                self.collect_all_metrics()
                self.save_to_database()
                self.send_to_elasticsearch()
                
                # Sleep until next collection interval
                logger.info(f"Sleeping for {self.config['collection_interval']} seconds")
                time.sleep(self.config["collection_interval"])
                
        except KeyboardInterrupt:
            logger.info("Collector stopped by user")
        except Exception as e:
            logger.error(f"Collector stopped due to error: {str(e)}")


def main():
    """Main entry point for the collector."""
    # Get database session
    db = next(get_db())
    
    try:
        collector = NetworkPerformanceCollector(db)
        collector.run()
    finally:
        db.close()


if __name__ == "__main__":
    main()
