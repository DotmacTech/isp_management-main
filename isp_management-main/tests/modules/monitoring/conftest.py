"""
Pytest configuration for service availability monitoring tests.
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)

# Import mock modules first
from tests.modules.monitoring.mock_modules import MockElasticsearchClient

# Import test configuration to set up environment
from tests.test_config import setup_import_compatibility
setup_import_compatibility()

# Import mock routes
from tests.modules.monitoring.mock_routes import router
# Override the real routes with our mock
sys.modules['modules.monitoring.routes'] = MagicMock(router=router)

try:
    # Now we can safely import from models
    from modules.monitoring.models.service_availability import Base, ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow, ProtocolType, StatusType, SeverityLevel
except ImportError as e:
    print(f"Error importing service_availability module: {e}")
    # Handle the import error, for example by using a mock or a fallback
    # For this example, we will just pass
    pass

# Import SQLAlchemy components
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@pytest.fixture(scope="session")
def db_engine():
    """Create a database engine for testing."""
    # Use in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables
    try:
        Base.metadata.create_all(engine)
    except NameError:
        print("Base is not defined, skipping table creation")
    
    yield engine
    
    # Drop tables
    try:
        Base.metadata.drop_all(engine)
    except NameError:
        print("Base is not defined, skipping table drop")


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for testing."""
    # Create a new session for each test
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    
    yield session
    
    # Rollback any changes
    session.rollback()
    session.close()


@pytest.fixture
def mock_elasticsearch_client():
    """Provide a mock Elasticsearch client for testing."""
    return MockElasticsearchClient()


@pytest.fixture
def sample_service_endpoints(db_session):
    """Create sample service endpoints for testing."""
    # HTTP endpoint
    http_endpoint = ServiceEndpoint(
        id="test-http",
        name="Test HTTP Service",
        url="http://example.com",
        protocol=ProtocolType.HTTP,
        check_interval=60,
        timeout=5,
        retries=3,
        expected_status_code=200,
        is_active=True
    )
    
    # HTTPS endpoint
    https_endpoint = ServiceEndpoint(
        id="test-https",
        name="Test HTTPS Service",
        url="https://example.com",
        protocol=ProtocolType.HTTPS,
        check_interval=60,
        timeout=5,
        retries=3,
        expected_status_code=200,
        expected_response_pattern="Welcome",
        is_active=True
    )
    
    # TCP endpoint
    tcp_endpoint = ServiceEndpoint(
        id="test-tcp",
        name="Test TCP Service",
        url="example.com:80",
        protocol=ProtocolType.TCP,
        check_interval=60,
        timeout=5,
        retries=3,
        is_active=True
    )
    
    # UDP endpoint
    udp_endpoint = ServiceEndpoint(
        id="test-udp",
        name="Test UDP Service",
        url="example.com:53",
        protocol=ProtocolType.UDP,
        check_interval=60,
        timeout=5,
        retries=3,
        is_active=True
    )
    
    # DNS endpoint
    dns_endpoint = ServiceEndpoint(
        id="test-dns",
        name="Test DNS Service",
        url="example.com",
        protocol=ProtocolType.DNS,
        check_interval=60,
        timeout=5,
        retries=3,
        is_active=True
    )
    
    # ICMP endpoint
    icmp_endpoint = ServiceEndpoint(
        id="test-icmp",
        name="Test ICMP Service",
        url="example.com",
        protocol=ProtocolType.ICMP,
        check_interval=60,
        timeout=5,
        retries=3,
        is_active=True
    )
    
    # Inactive endpoint
    inactive_endpoint = ServiceEndpoint(
        id="test-inactive",
        name="Test Inactive Service",
        url="http://example.com",
        protocol=ProtocolType.HTTP,
        check_interval=60,
        timeout=5,
        retries=3,
        expected_status_code=200,
        is_active=False
    )
    
    # Add endpoints to database
    db_session.add_all([
        http_endpoint, https_endpoint, tcp_endpoint, 
        udp_endpoint, dns_endpoint, icmp_endpoint, inactive_endpoint
    ])
    db_session.commit()
    
    return {
        "http": http_endpoint,
        "https": https_endpoint,
        "tcp": tcp_endpoint,
        "udp": udp_endpoint,
        "dns": dns_endpoint,
        "icmp": icmp_endpoint,
        "inactive": inactive_endpoint
    }


@pytest.fixture
def sample_maintenance_window(db_session, sample_service_endpoints):
    """Create a sample maintenance window for testing."""
    # Create maintenance window for HTTP endpoint
    http_endpoint = sample_service_endpoints["http"]
    
    maintenance_window = MaintenanceWindow(
        id="test-maintenance",
        endpoint_id=http_endpoint.id,
        name="Test Maintenance",
        description="Test maintenance window",
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=1),
        is_active=True
    )
    
    db_session.add(maintenance_window)
    db_session.commit()
    
    return maintenance_window
