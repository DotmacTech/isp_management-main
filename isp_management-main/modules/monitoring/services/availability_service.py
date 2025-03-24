"""
Service for monitoring service availability.
"""

import os
import logging
import socket
import time
import requests
import dns.resolver
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, ServiceAlert, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel, NotificationType
)
from modules.monitoring.schemas.service_availability import (
    ServiceEndpointCreate, ServiceEndpointUpdate,
    ServiceStatusCreate, ServiceOutageCreate, ServiceAlertCreate,
    MaintenanceWindowCreate, MaintenanceWindowUpdate
)
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
SERVICE_CHECK_TIMEOUT = int(os.getenv("SERVICE_CHECK_TIMEOUT", "5"))
SERVICE_CHECK_RETRIES = int(os.getenv("SERVICE_CHECK_RETRIES", "3"))
OUTAGE_DETECTION_THRESHOLD = int(os.getenv("OUTAGE_DETECTION_THRESHOLD", "3"))
OUTAGE_VERIFICATION_ENABLED = os.getenv("OUTAGE_VERIFICATION_ENABLED", "true").lower() == "true"


class AvailabilityService:
    """Service for monitoring service availability."""

    def __init__(self, db: Session):
        """Initialize the service with database session."""
        self.db = db
        self.es_client = ElasticsearchClient()

    # Service Endpoint CRUD operations
    def create_endpoint(self, endpoint: ServiceEndpointCreate) -> ServiceEndpoint:
        """Create a new service endpoint."""
        db_endpoint = ServiceEndpoint(**endpoint.model_dump())
        self.db.add(db_endpoint)
        self.db.commit()
        self.db.refresh(db_endpoint)
        logger.info(f"Created service endpoint: {db_endpoint.id}")
        return db_endpoint

    def get_endpoint(self, endpoint_id: str) -> Optional[ServiceEndpoint]:
        """Get a service endpoint by ID."""
        return self.db.query(ServiceEndpoint).filter(ServiceEndpoint.id == endpoint_id).first()

    def get_all_endpoints(
        self, 
        protocol: Optional[str] = None, 
        is_active: Optional[bool] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[ServiceEndpoint], int]:
        """Get all service endpoints with optional filtering."""
        query = self.db.query(ServiceEndpoint)
        
        if protocol:
            query = query.filter(ServiceEndpoint.protocol == protocol)
        
        if is_active is not None:
            query = query.filter(ServiceEndpoint.is_active == is_active)
        
        total = query.count()
        endpoints = query.offset(skip).limit(limit).all()
        
        return endpoints, total

    def update_endpoint(self, endpoint_id: str, endpoint: ServiceEndpointUpdate) -> Optional[ServiceEndpoint]:
        """Update a service endpoint."""
        db_endpoint = self.get_endpoint(endpoint_id)
        if not db_endpoint:
            return None
        
        update_data = endpoint.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_endpoint, key, value)
        
        self.db.commit()
        self.db.refresh(db_endpoint)
        logger.info(f"Updated service endpoint: {db_endpoint.id}")
        return db_endpoint

    def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete a service endpoint."""
        db_endpoint = self.get_endpoint(endpoint_id)
        if not db_endpoint:
            return False
        
        self.db.delete(db_endpoint)
        self.db.commit()
        logger.info(f"Deleted service endpoint: {endpoint_id}")
        return True

    # Service Status operations
    def check_service(self, endpoint_id: str) -> ServiceStatus:
        """Check the status of a service endpoint."""
        db_endpoint = self.get_endpoint(endpoint_id)
        if not db_endpoint:
            raise ValueError(f"Service endpoint not found: {endpoint_id}")
        
        # Check if service is in maintenance
        if self.is_in_maintenance(endpoint_id):
            logger.info(f"Service {endpoint_id} is in maintenance, skipping check")
            return self._create_status(db_endpoint, StatusType.MAINTENANCE, 0, "Service in maintenance")
        
        # Check service based on protocol
        start_time = time.time()
        status, message = self._check_by_protocol(db_endpoint)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Create and save status
        service_status = self._create_status(db_endpoint, status, response_time, message)
        
        # Check for outage
        if status == StatusType.DOWN:
            self._handle_potential_outage(db_endpoint, service_status)
        elif status == StatusType.UP:
            self._check_for_recovery(db_endpoint)
        
        return service_status

    def _check_by_protocol(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check service status based on protocol."""
        protocol = endpoint.protocol
        
        try:
            if protocol in (ProtocolType.HTTP, ProtocolType.HTTPS):
                return self._check_http(endpoint)
            elif protocol == ProtocolType.TCP:
                return self._check_tcp(endpoint)
            elif protocol == ProtocolType.UDP:
                return self._check_udp(endpoint)
            elif protocol == ProtocolType.ICMP:
                return self._check_icmp(endpoint)
            elif protocol == ProtocolType.DNS:
                return self._check_dns(endpoint)
            else:
                logger.warning(f"Unsupported protocol for service check: {protocol}")
                return StatusType.UNKNOWN, f"Unsupported protocol: {protocol}"
        except Exception as e:
            logger.error(f"Error checking service {endpoint.id}: {str(e)}")
            return StatusType.DOWN, f"Error: {str(e)}"

    def _check_http(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check HTTP/HTTPS service."""
        url = endpoint.url
        if not url.startswith(('http://', 'https://')):
            url = f"{endpoint.protocol.value}://{url}"
        
        try:
            response = requests.get(
                url, 
                timeout=endpoint.timeout or SERVICE_CHECK_TIMEOUT,
                verify=False  # Disable SSL verification for testing
            )
            
            # Check status code if expected is specified
            if endpoint.expected_status_code and response.status_code != endpoint.expected_status_code:
                return StatusType.DEGRADED, f"Unexpected status code: {response.status_code}"
            
            # Check response pattern if specified
            if endpoint.expected_response_pattern and endpoint.expected_response_pattern not in response.text:
                return StatusType.DEGRADED, "Expected response pattern not found"
            
            # Check if status code indicates success
            if 200 <= response.status_code < 300:
                return StatusType.UP, f"HTTP {response.status_code}"
            elif 300 <= response.status_code < 400:
                return StatusType.DEGRADED, f"HTTP {response.status_code} redirect"
            elif 400 <= response.status_code < 500:
                return StatusType.DEGRADED, f"HTTP {response.status_code} client error"
            else:
                return StatusType.DOWN, f"HTTP {response.status_code} server error"
        
        except requests.exceptions.Timeout:
            return StatusType.DOWN, "Connection timeout"
        except requests.exceptions.ConnectionError:
            return StatusType.DOWN, "Connection error"
        except requests.exceptions.RequestException as e:
            return StatusType.DOWN, f"Request error: {str(e)}"

    def _check_tcp(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check TCP service."""
        host = endpoint.url
        port = endpoint.port
        
        if not port:
            return StatusType.UNKNOWN, "Port not specified for TCP check"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(endpoint.timeout or SERVICE_CHECK_TIMEOUT)
        
        try:
            sock.connect((host, port))
            sock.close()
            return StatusType.UP, f"TCP connection successful to {host}:{port}"
        except socket.timeout:
            return StatusType.DOWN, f"TCP connection timeout to {host}:{port}"
        except socket.error as e:
            return StatusType.DOWN, f"TCP connection error to {host}:{port}: {str(e)}"
        finally:
            sock.close()

    def _check_udp(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check UDP service (basic check)."""
        # UDP checks are less reliable without application-specific logic
        host = endpoint.url
        port = endpoint.port
        
        if not port:
            return StatusType.UNKNOWN, "Port not specified for UDP check"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(endpoint.timeout or SERVICE_CHECK_TIMEOUT)
        
        try:
            sock.connect((host, port))
            # Just testing if we can establish a connection
            return StatusType.UP, f"UDP socket created for {host}:{port}"
        except socket.error as e:
            return StatusType.DOWN, f"UDP socket error for {host}:{port}: {str(e)}"
        finally:
            sock.close()

    def _check_icmp(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check ICMP (ping) service."""
        host = endpoint.url
        
        # Use ping command for simplicity
        response = os.system(f"ping -c 1 -W {endpoint.timeout or SERVICE_CHECK_TIMEOUT} {host} > /dev/null 2>&1")
        
        if response == 0:
            return StatusType.UP, f"Ping successful to {host}"
        else:
            return StatusType.DOWN, f"Ping failed to {host}"

    def _check_dns(self, endpoint: ServiceEndpoint) -> Tuple[StatusType, str]:
        """Check DNS service."""
        host = endpoint.url
        
        try:
            answers = dns.resolver.resolve(host, 'A')
            if answers:
                return StatusType.UP, f"DNS resolution successful for {host}"
            else:
                return StatusType.DEGRADED, f"DNS resolution returned no results for {host}"
        except dns.resolver.NXDOMAIN:
            return StatusType.DOWN, f"DNS name not found: {host}"
        except dns.resolver.Timeout:
            return StatusType.DOWN, f"DNS resolution timeout for {host}"
        except dns.exception.DNSException as e:
            return StatusType.DOWN, f"DNS resolution error for {host}: {str(e)}"

    def _create_status(
        self, 
        endpoint: ServiceEndpoint, 
        status: StatusType, 
        response_time: float, 
        message: str
    ) -> ServiceStatus:
        """Create and save a service status record."""
        status_data = ServiceStatusCreate(
            endpoint_id=endpoint.id,
            status=status,
            response_time=response_time,
            status_message=message
        )
        
        db_status = ServiceStatus(**status_data.model_dump())
        self.db.add(db_status)
        self.db.commit()
        self.db.refresh(db_status)
        
        # Index in Elasticsearch asynchronously
        self._index_status_to_elasticsearch(db_status)
        
        return db_status

    def _index_status_to_elasticsearch(self, status: ServiceStatus) -> None:
        """Index service status in Elasticsearch."""
        try:
            index_name = f"isp-service-status-{datetime.utcnow().strftime('%Y.%m.%d')}"
            doc = status.to_dict()
            
            self.es_client.index(index=index_name, body=doc)
            
            # Mark as synced
            status.elasticsearch_synced = True
            self.db.commit()
        except Exception as e:
            logger.error(f"Error indexing service status to Elasticsearch: {str(e)}")

    def get_service_status(
        self, 
        endpoint_id: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ServiceStatus]:
        """Get status history for a service endpoint."""
        query = self.db.query(ServiceStatus).filter(ServiceStatus.endpoint_id == endpoint_id)
        
        if start_time:
            query = query.filter(ServiceStatus.timestamp >= start_time)
        
        if end_time:
            query = query.filter(ServiceStatus.timestamp <= end_time)
        
        return query.order_by(desc(ServiceStatus.timestamp)).limit(limit).all()

    def get_latest_status(self, endpoint_id: str) -> Optional[ServiceStatus]:
        """Get the latest status for a service endpoint."""
        return (
            self.db.query(ServiceStatus)
            .filter(ServiceStatus.endpoint_id == endpoint_id)
            .order_by(desc(ServiceStatus.timestamp))
            .first()
        )

    def get_status_summary(self) -> Dict[str, int]:
        """Get a summary of service statuses."""
        result = (
            self.db.query(
                ServiceStatus.status,
                func.count(ServiceStatus.id).label("count")
            )
            .join(ServiceEndpoint)
            .filter(ServiceEndpoint.is_active == True)
            .group_by(ServiceStatus.status)
            .all()
        )
        
        summary = {status.value: 0 for status in StatusType}
        for status, count in result:
            summary[status.value] = count
        
        return summary
