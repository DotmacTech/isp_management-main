"""
Pytest configuration file for the ISP Management Platform.
"""

import sys
import os
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Ensure modules directory is recognized as a package
modules_path = project_root / 'modules'
if modules_path.exists():
    sys.path.insert(0, str(modules_path.parent))

# Set up environment variables for testing
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('TESTING', 'True')

# Import pytest fixtures
import pytest
from fastapi.testclient import TestClient

# Create a fixture for the test client
@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    """
    from main import app
    return TestClient(app)

# Create a fixture for database session
@pytest.fixture
def db_session():
    """
    Create a database session for testing.
    This uses an in-memory SQLite database.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    # Create an in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables
    from backend_core.database import Base
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
