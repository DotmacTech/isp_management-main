# Configuration Management Module

## Overview
The Configuration Management Module provides a centralized system for managing configurations across the ISP Management Platform. It enables dynamic updates, version control, and secure storage of sensitive configuration data.

## Features
- **Centralized Configuration Management**: Store and manage all system configurations in a single location
- **Environment-specific Configurations**: Define different configuration values for development, testing, staging, and production environments
- **Dynamic Updates**: Update configurations at runtime without requiring system restarts
- **Version Control**: Track changes to configurations with full history and audit trail
- **Secure Storage**: Encrypt sensitive configuration values for enhanced security
- **Configuration Grouping**: Organize related configurations into logical groups
- **Validation**: Validate configuration values against JSON schemas
- **Caching**: Cache frequently accessed configurations to improve performance
- **RESTful API**: Manage configurations through a comprehensive REST API
- **Elasticsearch Integration**: Index and search configurations using Elasticsearch for efficient retrieval and monitoring

## Directory Structure
```
modules/config_management/
├── __init__.py                  # Module initialization
├── endpoints.py                 # Module endpoints registration
├── models/                      # Database models
│   ├── __init__.py
│   └── configuration.py         # Configuration models
├── routes/                      # API routes
│   ├── __init__.py
│   └── configuration_routes.py  # Configuration API routes
├── schemas/                     # Pydantic schemas
│   ├── __init__.py
│   └── configuration.py         # Configuration schemas
├── services/                    # Business logic
│   ├── __init__.py
│   ├── cache_service.py         # Caching service
│   ├── configuration_service.py # Configuration management service
│   ├── elasticsearch_service.py # Elasticsearch integration service
│   └── encryption_service.py    # Encryption service
├── tasks.py                     # Celery tasks for background processing
└── tests/                       # Unit tests
    ├── __init__.py
    ├── conftest.py              # Test fixtures
    ├── test_cache_service.py    # Cache service tests
    ├── test_configuration_routes.py # API route tests
    ├── test_configuration_service.py # Configuration service tests
    ├── test_elasticsearch_service.py # Elasticsearch service tests
    └── test_encryption_service.py # Encryption service tests
```

## Models
### Configuration
The main configuration model that stores key-value pairs with metadata:
- `id`: Unique identifier
- `key`: Configuration key (e.g., "system.max_connections")
- `value`: Configuration value (can be any JSON-serializable value)
- `description`: Optional description
- `environment`: Target environment (development, testing, staging, production, or all)
- `category`: Category for organization (system, security, network, etc.)
- `is_encrypted`: Whether the value is encrypted
- `validation_schema`: Optional JSON schema for validation
- `version`: Configuration version
- `is_active`: Whether the configuration is active

### ConfigurationHistory
Tracks changes to configurations:
- `configuration_id`: Reference to the configuration
- `key`: Configuration key at the time of the change
- `value`: Configuration value at the time of the change
- `action`: Action performed (create, update, delete)
- `version`: Configuration version at the time of the change

### ConfigurationGroup
Groups related configurations:
- `name`: Group name
- `description`: Optional description

## Services
### ConfigurationService
Provides methods for managing configurations:
- CRUD operations for configurations and groups
- Validation against JSON schemas
- Version control and history tracking

### EncryptionService
Handles encryption and decryption of sensitive configuration data:
- Encrypts values before storage
- Decrypts values when retrieved
- Uses industry-standard encryption algorithms

### CacheService
Caches frequently accessed configurations:
- In-memory caching with TTL
- Automatic cleanup of expired entries
- Bulk operations for efficiency

### ElasticsearchService
Provides methods for Elasticsearch integration:
- Indexing and searching configurations
- Getting configuration statistics
- Synchronizing configurations with Elasticsearch

## API Endpoints
### Configuration API
- `GET /configurations`: List all configurations
- `GET /configurations/{key}`: Get a specific configuration
- `POST /configurations`: Create a new configuration
- `PUT /configurations/{key}`: Update a configuration
- `DELETE /configurations/{key}`: Delete a configuration
- `GET /configurations/{key}/history`: Get configuration history
- `POST /configurations/bulk`: Bulk update configurations

### Elasticsearch Integration API
- `GET /configurations/search`: Search configurations using Elasticsearch
- `GET /configurations/statistics`: Get statistics about configurations
- `POST /configurations/sync`: Sync all configurations to Elasticsearch

## Elasticsearch Integration
The Configuration Management Module integrates with Elasticsearch to provide efficient searching and monitoring of configurations. This integration enables:

### Features
- **Full-text Search**: Search configurations by key, value, description, and other attributes
- **Advanced Filtering**: Filter search results by environment, category, and active status
- **Configuration Statistics**: Get statistics about configurations, such as counts by environment and category
- **Change Monitoring**: Track changes to configurations over time
- **Bulk Indexing**: Efficiently index large numbers of configurations
- **Automatic Synchronization**: Keep Elasticsearch in sync with the database through scheduled Celery tasks

### Indices
The integration creates and maintains the following Elasticsearch indices:
- **configurations**: Stores current configuration data
- **configuration-history**: Stores the history of configuration changes
- **configuration-groups**: Stores configuration group data

### Celery Tasks
The module includes the following Celery tasks for background processing:
- **sync_configurations_to_elasticsearch**: Synchronizes all configurations, history, and groups to Elasticsearch (runs every 3 hours)
- **cleanup_configuration_history**: Cleans up old configuration history entries to prevent the database from growing too large (runs monthly)

### Usage
To use the Elasticsearch integration, ensure that Elasticsearch is running and properly configured in your environment. The integration will automatically create the necessary indices if they don't exist.

Example of searching configurations:
```python
from modules.config_management.services.configuration_service import ConfigurationService
from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService

# Initialize services
es_service = ConfigurationElasticsearchService()
config_service = ConfigurationService(db=db, es_service=es_service)

# Search configurations
results = config_service.search_configurations(
    query="network settings",
    environment="production",
    category="network",
    active_only=True
)

# Get configuration statistics
stats = config_service.get_configuration_statistics()
```

## Usage Examples
### Retrieving a Configuration
```python
from modules.config_management.services.configuration_service import ConfigurationService
from backend_core.database import get_db

# Get the database session
db = next(get_db())

# Create the configuration service
config_service = ConfigurationService(db)

# Get a configuration value
max_connections = config_service.get_configuration_value("system.max_connections")
```

### Creating a Configuration
```python
from modules.config_management.services.configuration_service import ConfigurationService
from modules.config_management.models.configuration import ConfigEnvironment, ConfigCategory
from backend_core.database import get_db

# Get the database session
db = next(get_db())

# Create the configuration service
config_service = ConfigurationService(db)

# Create a new configuration
config_data = {
    "key": "system.log_level",
    "value": "INFO",
    "description": "System log level",
    "environment": ConfigEnvironment.ALL,
    "category": ConfigCategory.SYSTEM,
    "validation_schema": {
        "type": "string",
        "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    }
}

config_service.create_configuration(config_data, created_by="admin")
```

### Updating a Configuration
```python
from modules.config_management.services.configuration_service import ConfigurationService
from backend_core.database import get_db

# Get the database session
db = next(get_db())

# Create the configuration service
config_service = ConfigurationService(db)

# Update a configuration
config_service.update_configuration(
    "system.log_level",
    {"value": "DEBUG"},
    updated_by="admin"
)
```

## Security Considerations
- Sensitive configuration values are encrypted at rest
- API endpoints enforce role-based access control
- Configuration history provides an audit trail for compliance
- Validation schemas ensure data integrity

## Integration with Other Modules
The Configuration Management Module can be integrated with other modules to provide centralized configuration management:

```python
from modules.config_management.services.configuration_service import ConfigurationService
from backend_core.database import get_db

class SomeOtherService:
    def __init__(self, db):
        self.db = db
        self.config_service = ConfigurationService(db)
    
    def some_method(self):
        # Get configuration values
        timeout = self.config_service.get_configuration_value("network.timeout", default=30)
        
        # Use the configuration value
        # ...
