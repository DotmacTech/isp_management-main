# ISP Management Platform Module Standardization Guide

## Overview

This document provides guidelines for standardizing all modules in the ISP Management Platform codebase. The standardization aims to improve code organization, maintainability, and developer experience by establishing a consistent structure across all modules.

## Target Module Structure

Each module should follow this standardized structure:

```
module_name/
├── api/                       # API layer
│   ├── __init__.py            # API router initialization
│   └── endpoints.py           # API endpoints
├── config/                    # Configuration
│   ├── __init__.py
│   └── settings.py            # Module settings
├── models/                    # Database models
│   ├── __init__.py
│   └── model_files.py         # Domain-specific models
├── schemas/                   # Pydantic schemas
│   ├── __init__.py
│   └── schema_files.py        # Domain-specific schemas
├── services/                  # Business logic
│   ├── __init__.py
│   └── service_files.py       # Domain-specific services
├── utils/                     # Utilities
│   ├── __init__.py
│   └── utility_files.py       # Domain-specific utilities
└── __init__.py                # Module initialization
```

## Implementation Steps

Follow these steps when standardizing a module:

### 1. Create Directory Structure

Create the standard directories if they don't exist:

```bash
mkdir -p module_name/{api,config,models,schemas,services,utils}
touch module_name/{api,config,models,schemas,services,utils}/__init__.py
```

### 2. Move Files to Appropriate Directories

- Move API endpoints to `api/endpoints.py`
- Move configuration settings to `config/settings.py`
- Move database models to `models/`
- Move Pydantic schemas to `schemas/`
- Move service implementations to `services/`
- Move utility functions to `utils/`

### 3. Update Imports

- Use relative imports within the module
- Update cross-module imports to reflect the new structure
- Example:
  ```python
  # Before
  from modules.monitoring.schemas import AlertResponse
  
  # After
  from .schemas import AlertResponse
  ```

### 4. Update Module __init__.py

Update the module's main `__init__.py` to expose the API router:

```python
"""
Module initialization for [Module Name].

This module provides [brief description of module functionality].
"""

from .api import router

__all__ = ["router"]
```

### 5. Create API Router

In `api/__init__.py`, initialize the API router:

```python
"""
API router initialization for [Module Name].

This module provides the FastAPI router for [Module Name] endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
```

## Testing and Validation

After standardizing a module:

1. Run the application to ensure it starts without errors
2. Test the module's API endpoints to verify functionality
3. Run unit tests to ensure all tests pass
4. Check for any import errors or circular dependencies

## Git Workflow

Follow this Git workflow when standardizing modules:

1. Create a feature branch for each module: `git checkout -b standardize-[module-name]`
2. Implement the standardization changes
3. Commit changes with descriptive messages
4. Create a pull request for review
5. Merge the changes after approval and successful testing

## Module-Specific Considerations

### Monitoring Module
- Organize collectors into a dedicated directory
- Ensure alert management services are properly separated

### Billing Module
- Separate invoice generation from payment processing
- Organize subscription management services

### CRM Module
- Separate ticket handling from customer management
- Organize notification services

### Network Module
- Separate configuration from monitoring components
- Organize device management services

## Best Practices

1. **Maintain Backward Compatibility**: Ensure existing functionality continues to work
2. **Update Documentation**: Update any documentation that references the old structure
3. **Consistent Naming**: Use consistent naming conventions across all modules
4. **Clean Imports**: Avoid circular dependencies and use relative imports where appropriate
5. **Incremental Changes**: Make changes incrementally to minimize disruption

## Timeline and Prioritization

1. Start with the Monitoring module as a proof of concept
2. Proceed with core modules (Auth, Billing, CRM)
3. Continue with secondary modules
4. Complete with utility modules

## Conclusion

Following this standardization guide will result in a more maintainable, organized, and developer-friendly codebase. The consistent structure across all modules will make it easier for developers to navigate and understand the codebase, leading to increased productivity and code quality.
