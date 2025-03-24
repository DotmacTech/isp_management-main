"""
Test configuration for the ISP Management Platform.

This module sets up the test environment, including database connections,
mocking external services, and configuring test fixtures.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_config")

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Add project root to Python path to ensure imports work correctly
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables for testing
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ELASTICSEARCH_HOSTS"] = "http://localhost:9200"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SERVICE_CHECK_INTERVAL"] = "60"
os.environ["OUTAGE_DETECTION_THRESHOLD"] = "3"
os.environ["SERVICE_CHECK_TIMEOUT"] = "5"

# Import mock dependencies first to ensure they're registered before any real imports
try:
    from tests.mock_dependencies import setup_mock_dependencies
    mock_deps = setup_mock_dependencies()
    logger.info("Successfully set up mock dependencies")
except ImportError as e:
    logger.error(f"Error setting up mock dependencies: {e}")
    raise

# Create module-level imports to ensure they're available
try:
    import backend_core
    import modules
    logger.info("Successfully imported core modules")
except ImportError as e:
    logger.error(f"Error importing core modules: {e}")
    raise

# Create symbolic links for import compatibility if needed
def setup_import_compatibility():
    """
    Create symbolic links to ensure import compatibility between
    different module structures used in the application.
    """
    try:
        # Check if we need to create a compatibility layer
        isp_management_dir = PROJECT_ROOT / "isp_management"
        if not isp_management_dir.exists():
            # Create directory
            isp_management_dir.mkdir(exist_ok=True)
            
            # Create symbolic links for backend_core and modules
            backend_core_link = isp_management_dir / "backend_core"
            modules_link = isp_management_dir / "modules"
            
            if not backend_core_link.exists():
                os.symlink(PROJECT_ROOT / "backend_core", backend_core_link)
                logger.info(f"Created symbolic link for backend_core at {backend_core_link}")
            
            if not modules_link.exists():
                os.symlink(PROJECT_ROOT / "modules", modules_link)
                logger.info(f"Created symbolic link for modules at {modules_link}")
            
            # Create __init__.py file
            init_file = isp_management_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                logger.info(f"Created __init__.py at {init_file}")
                
            logger.info("Import compatibility layer set up successfully")
        else:
            logger.info("Import compatibility layer already exists")
    except Exception as e:
        logger.error(f"Error setting up import compatibility: {e}")
        raise

# Set up database for testing
def setup_test_database(engine=None):
    """
    Set up a test database for testing.
    
    Args:
        engine: SQLAlchemy engine to use. If None, creates an in-memory SQLite database.
        
    Returns:
        SQLAlchemy engine
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create engine if not provided
    if engine is None:
        engine = create_engine(os.environ["DATABASE_URL"], echo=False)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Return engine and session factory
    return engine, SessionLocal

# Set up import compatibility
setup_import_compatibility()
