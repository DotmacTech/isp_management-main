# Database Migration Strategy

This document outlines the standardized approach to database migrations in the ISP Management Platform, ensuring consistency and reliability in schema evolution.

## Migration Framework

The ISP Management Platform uses **Alembic** for database migrations, which provides:

- Version control for database schema
- Auto-generation of migration scripts
- Dependency tracking between migrations
- Support for upgrading and downgrading

## Directory Structure

All migrations should be managed through the `/alembic` directory structure:

```
alembic/
├── versions/                  # Migration script files
│   ├── 20250315_initial.py
│   ├── 20250315_user_tables.py
│   └── ai_chatbot_integration.py
├── env.py                     # Alembic environment configuration
├── README                     # Documentation
└── script.py.mako             # Migration script template
```

The `/migrations` directory is deprecated and should not be used for new migrations.

## Migration Workflow

### 1. Creating New Migrations

When making schema changes, follow these steps:

```bash
# Navigate to the project root
cd /path/to/isp_management

# Generate a migration script
alembic revision --autogenerate -m "description_of_changes"
```

This will create a new migration script in `alembic/versions/`.

### 2. Reviewing Migrations

Always review auto-generated migrations before applying them:

- Check that all intended changes are captured
- Verify that no unintended changes are included
- Add any custom migration logic if needed
- Ensure proper dependencies between migrations

### 3. Applying Migrations

To apply migrations to the database:

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision>

# Apply relative migrations
alembic upgrade +2  # Apply next 2 migrations
```

### 4. Rolling Back Migrations

If needed, migrations can be rolled back:

```bash
# Rollback to previous version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

## Naming Conventions

Migration files should follow these naming conventions:

- Use descriptive names that indicate the purpose of the migration
- Prefix with date in YYYYMMDD format for chronological ordering
- Use snake_case for readability

Example: `20250315_add_user_preferences.py`

## Best Practices

1. **One Change Per Migration**: Each migration should focus on a single logical change to make troubleshooting easier.

2. **Test Migrations**: Always test migrations in development/staging environments before applying to production.

3. **Data Migrations**: For complex data migrations, consider creating separate scripts that can be run after schema migrations.

4. **Idempotent Operations**: When possible, make migrations idempotent (can be run multiple times without side effects).

5. **Documentation**: Document any non-obvious migration logic within the migration file.

6. **Backup**: Always backup the database before applying migrations in production.

## Module-Specific Migrations

For module-specific migrations:

1. Create a migration file with a name that clearly indicates the module
2. Include the module name in the revision ID comment
3. Document any module-specific considerations

Example for the AI Chatbot module:
```python
"""
AI Chatbot Integration Module database migration.

Revision ID: ai_chatbot_integration
Revises: integration_management_metrics
Create Date: 2025-03-15 06:55:00.000000
"""
```

## Migration Coordination

When multiple developers are working on migrations:

1. Communicate planned schema changes to the team
2. Coordinate migration dependencies to avoid conflicts
3. Use feature branches for migration development
4. Review migrations as part of the PR process

## Troubleshooting

Common migration issues and solutions:

1. **Migration conflicts**: Rebase your branch and regenerate migrations
2. **Failed migrations**: Check the error message and fix the underlying issue
3. **Inconsistent state**: Use `alembic current` to check the current state

## Monitoring and Maintenance

Regularly perform these maintenance tasks:

1. Clean up old migrations that are no longer needed
2. Verify that the migration history matches the actual database schema
3. Document any manual interventions in the migration process
