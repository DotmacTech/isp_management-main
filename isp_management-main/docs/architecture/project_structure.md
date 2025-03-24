# ISP Management Platform Project Structure

This document provides an overview of the ISP Management Platform's project structure, explaining the purpose and organization of key directories and files.

## Root Directory Structure

```
isp_management/
├── alembic/                   # Database migration scripts and configuration
├── backend_core/              # Core backend functionality
├── core/                      # Cross-cutting concerns and utilities
├── docs/                      # Documentation
├── kubernetes/                # Kubernetes deployment configurations
├── modules/                   # Feature modules
├── scripts/                   # Utility scripts
├── static/                    # Static assets
├── templates/                 # Template files
├── tests/                     # Test suite
├── .github/                   # GitHub workflows and configurations
├── .gitignore                 # Git ignore file
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Docker build configuration
├── main.py                    # Application entry point
├── pyproject.toml             # Python project configuration
├── README.md                  # Project overview
└── requirements.txt           # Python dependencies
```

## Core Components

### Backend Core (`/backend_core`)

Contains the core functionality that supports the entire platform:

```
backend_core/
├── auth/                      # Authentication and authorization
│   ├── dependencies.py        # FastAPI dependencies for auth
│   ├── jwt.py                 # JWT token handling
│   ├── oauth2.py              # OAuth2 implementation
│   └── permissions.py         # Permission management
├── db/                        # Database configuration
│   ├── base.py                # Base model class
│   ├── session.py             # Database session management
│   └── utils.py               # Database utilities
├── exceptions/                # Custom exception handling
│   ├── handlers.py            # Exception handlers
│   └── types.py               # Custom exception types
├── logging/                   # Logging configuration
│   ├── config.py              # Logging setup
│   └── handlers.py            # Custom log handlers
└── middleware/                # Middleware components
    ├── correlation.py         # Request correlation
    ├── logging.py             # Request logging
    └── tenant.py              # Multi-tenancy support
```

### Core Utilities (`/core`)

Contains cross-cutting utilities and services:

```
core/
├── cache.py                   # Caching utilities
├── config.py                  # Configuration management
├── constants.py               # System-wide constants
├── metrics.py                 # Metrics collection and reporting
├── pagination.py              # Pagination utilities
├── security.py                # Security utilities
└── validators.py              # Common validators
```

### Feature Modules (`/modules`)

Contains the individual feature modules of the platform:

```
modules/
├── ai_chatbot/                # AI Chatbot integration
├── billing/                   # Billing and invoicing
├── business_intelligence/     # Reporting and analytics
├── config_management/         # System configuration management
├── crm/                       # Customer relationship management
├── crm_ticketing/             # Support ticketing system
├── file_manager/              # File storage and management
├── integration_management/    # Third-party integrations
├── monitoring/                # System monitoring
├── network_inventory/         # Network equipment inventory
├── notification/              # Notification system
├── radius/                    # RADIUS authentication
├── reseller/                  # Reseller management
└── tariff/                    # Tariff and plan management
```

Each module follows the standardized structure outlined in the [Module Structure Guidelines](./module_structure.md).

### Tests (`/tests`)

Contains the test suite for the platform:

```
tests/
├── conftest.py                # Shared test fixtures
├── unit/                      # Unit tests
│   ├── backend_core/          # Tests for backend core
│   └── modules/               # Tests for modules
├── integration/               # Integration tests
├── api/                       # API tests
└── e2e/                       # End-to-end tests
```

See the [Testing Guidelines](../testing/testing_guidelines.md) for more information.

### Documentation (`/docs`)

Contains project documentation:

```
docs/
├── architecture/              # Architecture documentation
│   ├── module_structure.md    # Module structure guidelines
│   ├── migration_strategy.md  # Database migration strategy
│   └── project_structure.md   # This document
├── api/                       # API documentation
│   └── openapi_standards.md   # OpenAPI documentation standards
├── security/                  # Security documentation
│   └── security_guidelines.md # Security guidelines
├── testing/                   # Testing documentation
│   └── testing_guidelines.md  # Testing guidelines
├── deployment/                # Deployment guides
├── development/               # Development guides
└── user/                      # User documentation
```

### Kubernetes (`/kubernetes`)

Contains Kubernetes deployment configurations:

```
kubernetes/
├── production/                # Production environment configurations
├── staging/                   # Staging environment configurations
└── development/               # Development environment configurations
```

### GitHub Workflows (`/.github/workflows`)

Contains CI/CD pipeline configurations:

```
.github/workflows/
├── customer-module-ci.yml     # CI/CD for customer module
├── tariff-module-ci.yml       # CI/CD for tariff module
└── main-ci.yml                # Main CI/CD pipeline
```

## Application Entry Point

The `main.py` file is the entry point for the application:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_core.middleware.correlation import CorrelationIdMiddleware
from backend_core.middleware.logging import RequestLoggingMiddleware
from backend_core.middleware.tenant import TenantMiddleware
from backend_core.exceptions.handlers import register_exception_handlers

# Import module routers
from modules.ai_chatbot.api import router as ai_chatbot_router
from modules.billing.api import router as billing_router
# ... other module routers

app = FastAPI(
    title="ISP Management Platform",
    description="API for ISP Management Platform",
    version="1.0.0",
)

# Register middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include module routers
app.include_router(ai_chatbot_router, prefix="/api/v1/chatbot", tags=["AI Chatbot"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])
# ... other module routers

@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Module Example: AI Chatbot

The AI Chatbot module follows the standardized module structure:

```
modules/ai_chatbot/
├── __init__.py                # Module initialization
├── api/                       # API layer
│   ├── __init__.py            # API router initialization
│   └── endpoints.py           # API endpoints
├── config/                    # Module configuration
│   ├── __init__.py
│   └── settings.py            # Module settings
├── models/                    # Database models
│   ├── __init__.py
│   └── chatbot.py             # Chatbot-related models
├── schemas/                   # Pydantic schemas
│   ├── __init__.py
│   └── chatbot.py             # Chatbot-related schemas
├── services/                  # Business logic
│   ├── __init__.py
│   ├── ai_service_client.py   # AI service communication
│   ├── business_logic_processor.py # Business logic processing
│   └── chatbot_service.py     # Main chatbot service
└── utils/                     # Utilities
    ├── __init__.py
    ├── context.py             # Conversation context management
    └── security.py            # Security utilities
```

## Dependency Management

The project uses the following dependency management files:

- `requirements.txt`: Main project dependencies
- `pyproject.toml`: Python project configuration
- `requirements-dev.txt`: Development dependencies

## Docker Configuration

The project includes Docker configuration for containerized deployment:

- `Dockerfile`: Container build configuration
- `docker-compose.yml`: Multi-container configuration for development

## Symlinks and Special Directories

The project contains some symbolic links for backward compatibility:

- `/isp_management/backend_core` → `/backend_core`
- `/isp_management/modules` → `/modules`

These symlinks ensure that imports continue to work with the legacy structure while the codebase transitions to the new structure.

## Empty Directories

The following empty directories are placeholders for future development:

- `/modules/business_intelligence/tasks`
- `/modules/business_intelligence/templates`
- `/modules/crm_ticketing/utils`
- `/modules/config_management/tests`
- `/modules/file_manager/endpoints`
- `/modules/file_manager/utils`
- `/modules/integration_management/tests`
- `/modules/monitoring/endpoints`
- `/modules/monitoring/tests`

## Conclusion

This project structure provides a modular, maintainable architecture for the ISP Management Platform. By following the standardized module structure and adhering to the documentation guidelines, developers can easily navigate and contribute to the codebase.
