# Module Structure Guidelines

This document outlines the standardized structure for modules in the ISP Management Platform. Following these guidelines ensures consistency across the codebase and makes it easier for developers to navigate and maintain the system.

## Directory Structure

Each module should follow this standard directory structure:

```
modules/module_name/
├── __init__.py                # Module initialization
├── api/                       # API layer
│   ├── __init__.py            # API router initialization
│   └── endpoints.py           # API endpoints
├── models/                    # Database models
│   ├── __init__.py
│   └── module_models.py       # Module-specific models
├── schemas/                   # Pydantic schemas
│   ├── __init__.py
│   └── module_schemas.py      # Module-specific schemas
├── services/                  # Business logic
│   ├── __init__.py
│   └── module_service.py      # Module-specific services
├── utils/                     # Utility functions
│   ├── __init__.py
│   └── module_utils.py        # Module-specific utilities
└── config/                    # Module-specific configuration
    ├── __init__.py
    └── settings.py            # Module settings
```

## Layer Responsibilities

### API Layer (`api/`)
- Defines API endpoints and routes
- Handles request validation
- Manages authentication and authorization
- Delegates business logic to services
- Returns appropriate HTTP responses

### Models Layer (`models/`)
- Defines SQLAlchemy ORM models
- Specifies database relationships
- Implements model-specific methods
- Handles database constraints

### Schemas Layer (`schemas/`)
- Defines Pydantic schemas for request/response validation
- Implements schema validation logic
- Provides schema conversion methods
- Specifies OpenAPI documentation

### Services Layer (`services/`)
- Implements business logic
- Orchestrates data access and manipulation
- Manages transactions
- Handles error cases
- Interacts with external services

### Utilities Layer (`utils/`)
- Provides helper functions and classes
- Implements cross-cutting concerns
- Offers reusable functionality

### Configuration Layer (`config/`)
- Defines module-specific settings
- Manages environment-specific configuration
- Provides defaults and validation

## Naming Conventions

- **Files**: Use snake_case for all files (e.g., `user_service.py`)
- **Classes**: Use PascalCase for all classes (e.g., `UserService`)
- **Functions/Methods**: Use snake_case for functions and methods (e.g., `get_user_by_id`)
- **Variables**: Use snake_case for variables (e.g., `user_id`)
- **Constants**: Use UPPER_SNAKE_CASE for constants (e.g., `DEFAULT_PAGE_SIZE`)

## Import Guidelines

- Always use absolute imports
- Group imports in the following order:
  1. Standard library imports
  2. Third-party imports
  3. Application imports
- Sort imports alphabetically within each group
- Separate groups with a blank line

Example:
```python
# Standard library imports
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Application imports
from core.database import get_db
from core.security import get_current_user
```

## Testing

Each module should have corresponding tests in the `tests/modules/module_name/` directory, following this structure:

```
tests/modules/module_name/
├── conftest.py                # Test fixtures
├── test_api.py                # API tests
├── test_models.py             # Model tests
└── test_services.py           # Service tests
```

## Documentation

Each module should include:

1. Docstrings for all public classes and functions
2. Module-level docstrings explaining the purpose of the module
3. README.md file in the module root directory explaining its functionality

## Example

The AI Chatbot module follows this standardized structure and can be used as a reference implementation.
