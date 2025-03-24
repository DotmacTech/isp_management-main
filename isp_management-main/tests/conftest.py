"""
Test configuration for the ISP Management Platform.

This module contains pytest fixtures and configuration for testing.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Add the project root and modules to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))
modules_path = project_root / 'modules'
if modules_path.exists():
    sys.path.insert(0, str(modules_path.parent))

# Import models directly to create tables
from backend_core.models import Base, User
from backend_core.auth_service import AuthService

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    """Create a SQLAlchemy engine for testing."""
    engine = create_engine(
        TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
    
    # Remove the test database file if it exists
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    # Create a new session for each test
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    from main import app
    
    # Use test configurations
    app.state.testing = True
    
    return app


@pytest.fixture
def client(test_app, db_session):
    """Create a test client with a database session."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Apply the override
    from backend_core.dependencies import get_db
    test_app.dependency_overrides[get_db] = override_get_db
    
    # Create and return the test client
    return TestClient(test_app)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    # Create a test user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    
    # Hash the password
    user.hashed_password = AuthService.get_password_hash("password123")
    
    # Add to the database
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_admin(db_session):
    """Create a test admin user."""
    # Create a test admin user
    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    
    # Hash the password
    admin.hashed_password = AuthService.get_password_hash("adminpass")
    
    # Add to the database
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    return admin


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    # Create a mock Redis client
    redis_mock = MagicMock()
    
    # Mock common Redis methods
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 3600
    
    # Apply the patch
    with patch("backend_core.cache.redis_client", redis_mock):
        yield redis_mock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    # Set environment variables for testing
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    
    yield


# Module-specific fixtures

@pytest.fixture
def mock_monitoring_service():
    """Mock the monitoring service for testing."""
    with patch("modules.monitoring.services.monitoring_service.MonitoringService") as mock_service:
        instance = mock_service.return_value
        instance.get_metrics.return_value = {"cpu": 50, "memory": 60, "disk": 70}
        instance.get_alerts.return_value = []
        yield instance


@pytest.fixture
def mock_customer_service():
    """Mock the customer service for testing."""
    with patch("modules.customer.services.customer_service.CustomerService") as mock_service:
        instance = mock_service.return_value
        instance.get_customer.return_value = {
            "id": 1,
            "name": "Test Customer",
            "email": "customer@example.com",
            "active": True
        }
        yield instance
