# ISP Management Platform

A comprehensive, modular, and scalable system designed to support Internet Service Providers in managing billing, network access, customer interactions, and analytics.

## Core Features

- Billing & Payment Processing
  - Subscription Management
  - Tax Management
  - Discount Management
  - Financial Reporting
- RADIUS Authentication (AAA)
- Tariff Management
- Customer Relationship Management
- Network Monitoring
- Reseller Management
- Service Activation

## Quick Start

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Unix/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
5. Initialize the database:
   ```bash
   alembic upgrade head
   ```
6. Start the development server:
   ```bash
   uvicorn backend_core.main:app --reload
   ```

## Docker Setup and Development

The ISP Management Platform uses Docker for containerization to ensure consistent environments across development and production.

### Prerequisites

- Docker and Docker Compose installed on your machine
- Git for version control

### Development Environment

The project includes a development helper script (`dev.sh`) to simplify common development tasks:

```bash
# Start all services in development mode
./dev.sh up

# Stop all services
./dev.sh down

# Rebuild all services
./dev.sh build

# View logs (optionally for a specific service)
./dev.sh logs [service]

# Run tests
./dev.sh test

# Run database migrations
./dev.sh migrate

# Open a shell in the app container
./dev.sh shell

# Open PostgreSQL interactive terminal
./dev.sh psql

# Open Redis interactive terminal
./dev.sh redis-cli

# Check Elasticsearch health
./dev.sh es-health

# Open Kibana in browser (macOS only)
./dev.sh kibana
```

### Docker Services

The Docker Compose setup includes the following services:

1. **Application Service (`app`)**: The main FastAPI application
2. **PostgreSQL**: Database for storing application data
3. **Redis**: For caching and message queuing
4. **Elasticsearch**: For centralized logging and search
5. **Kibana**: For log visualization and dashboards
6. **Logstash**: For log processing and transformation
7. **Filebeat**: For log shipping from the application to Elasticsearch
8. **Celery Worker**: For background task processing
9. **Celery Beat**: For scheduled task execution

### Environment Variables

The Docker Compose file includes all necessary environment variables for development. For production, you should set up appropriate environment variables or secrets.

## CI/CD Pipeline

The project includes a GitHub Actions workflow for continuous integration and deployment.

### CI Process

The CI process includes:

1. **Linting**: Checking code quality with flake8
2. **Testing**: Running unit and integration tests with pytest
3. **Coverage**: Generating test coverage reports

### CD Process

The CD process includes:

1. **Building Docker Images**: Creating Docker images for the application
2. **Publishing to DockerHub**: Pushing images to DockerHub
3. **Deploying to Production**: Deploying the application to the production server

### Required Secrets

To use the CI/CD pipeline, you need to set up the following secrets in your GitHub repository:

- `DOCKERHUB_USERNAME`: Your DockerHub username
- `DOCKERHUB_TOKEN`: Your DockerHub access token
- `DEPLOY_HOST`: The hostname or IP address of your production server
- `DEPLOY_USERNAME`: The username for SSH access to your production server
- `DEPLOY_KEY`: The SSH private key for accessing your production server

### Deployment

The deployment process uses SSH to connect to the production server and update the application using Docker Compose.

## Monitoring and Logging

The ISP Management Platform includes a comprehensive monitoring module with Elasticsearch integration for centralized logging, metrics collection, and system health monitoring.

### Kibana Dashboards

Kibana dashboards are available for:

1. System Health Monitoring
2. Network Performance Metrics
3. Service Availability Tracking
4. Customer Usage Statistics
5. Alert History and Configuration

Access Kibana at http://localhost:5601 when running in development mode.

## Architecture

Built on a microservices architecture with a modular monolith core:
- FastAPI for REST APIs
- PostgreSQL for primary data storage
- Redis for caching
- Elasticsearch for logging
- Celery for async tasks

## Module Structure

```
isp_management/
├── backend_core/          # Core services (Auth, Config, etc.)
├── modules/               # Business modules
│   ├── billing/          # Billing & payments
│   │   ├── schemas/      # Data validation schemas
│   │   ├── services/     # Business logic services
│   │   ├── endpoints.py  # API endpoints
│   │   └── README.md     # Module documentation
│   ├── radius/           # AAA services
│   ├── tariff/           # Plan management
│   ├── monitoring/       # System monitoring
│   ├── reseller/         # Reseller operations
│   └── crm/             # Customer management
├── tests/                # Test suites
│   ├── modules/
│   │   ├── billing/      # Billing module tests
│   │   └── ...
├── docs/                 # Documentation
│   ├── modules/
│   │   ├── billing/      # Billing module documentation
│   │   └── ...
└── scripts/              # Utility scripts
```

## Expanded Billing Module

The billing module has been expanded to include comprehensive financial management capabilities:

### Subscription Management
- Create and manage subscription plans
- Support for different billing cycles (monthly, quarterly, annual)
- Subscription lifecycle management (create, pause, resume, cancel)
- Plan changes with prorated billing
- Usage-based billing for metered services

### Tax Management
- Configure tax rates for different countries and regions
- Manage tax exemptions for eligible customers
- Automatic tax calculation based on customer location
- Generate tax reports for compliance

### Discount Management
- Create and manage various types of discounts
- Support for promotional codes, referral discounts, and loyalty discounts
- Apply discounts to invoices or subscription plans
- Track discount usage and effectiveness

### Financial Reporting
- Generate revenue summaries and breakdowns
- Track subscription metrics and churn rates
- Analyze accounts receivable aging
- Calculate customer lifetime value
- Export financial data for external analysis

## Testing

Run tests for specific modules:

```bash
# Run expanded billing module tests
./scripts/test_billing_module.sh

# Run all tests
pytest
```

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Expanded Billing Module Documentation](docs/modules/billing/expanded_billing_module.md)

## Development

- Follow PEP 8 style guide
- Use Black for code formatting
- Write tests for new features
- Update documentation when needed

## Security

- OAuth2 with JWT for authentication
- Role-based access control
- PCI-DSS compliance for payments
- Regular security audits

## License

Copyright 2025. All rights reserved.


## Directory Structure

The ISP Management Platform follows a standardized directory structure:

```
isp_management/
├── .env.example
├── .gitignore
├── README.md
├── alembic.ini
├── conftest.py
├── main.py
├── pytest.ini
├── requirements-test.txt
├── requirements.txt
├── api/  # Central API gateway and routing
├── config/  # Application-wide configuration
├── core/  # Core functionality and shared components
├── docs/  # Documentation files
├── migrations/  # Database migration scripts
├── modules/  # Feature modules
├── scripts/  # Utility and automation scripts
├── static/  # Static assets
├── templates/  # Template files
├── tests/  # Test files and fixtures
├── utils/  # Utility functions and helpers
