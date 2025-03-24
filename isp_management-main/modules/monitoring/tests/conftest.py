"""
Pytest fixtures for the monitoring module tests.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from modules.monitoring.models import Base

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/isp_management_test")

# Create test database engine
test_engine = create_engine(DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    yield test_engine
    
    # Drop tables after tests
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    
    yield session
    
    # Rollback the transaction and close the session
    session.close()
    transaction.rollback()
    connection.close()
