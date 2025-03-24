# Tariff Enforcement Module

The Tariff Enforcement Module is a core component of the ISP Management Platform, responsible for managing tariff plans, user assignments, usage tracking, and policy enforcement.

## Features

- **Tariff Plan Management**: Create, update, and manage tariff plans with various pricing tiers, data caps, and speed limits.
- **User Assignment**: Assign tariff plans to users with effective dates and billing cycles.
- **Usage Tracking**: Record and monitor user bandwidth usage against plan limits.
- **Policy Enforcement**: Automatically enforce policies such as throttling when data caps are exceeded.
- **Billing Integration**: Handle plan changes, prorated billing, and overage charges.
- **RADIUS Integration**: Apply network-level policies based on tariff plans.

## Architecture

The Tariff Enforcement Module follows a modular design with the following components:

- **Core Services**: Business logic for tariff management and enforcement.
- **API Endpoints**: RESTful API for interacting with the module.
- **Database Models**: SQLAlchemy models for persistent storage.
- **Scheduled Tasks**: Celery tasks for recurring operations.
- **Integrations**: Connectors to RADIUS and Billing modules.
- **Monitoring**: Prometheus metrics and alerting.

## Integration Components

### RADIUS Integration

The RADIUS integration (`radius_integration.py`) provides the following capabilities:

- Apply tariff policies to RADIUS for network-level enforcement
- Update user bandwidth limits based on tariff plans
- Throttle users who exceed data caps
- Synchronize policy changes across multiple users
- Retrieve usage data from RADIUS for reconciliation

### Billing Integration

The Billing integration (`billing_integration.py`) handles:

- Plan changes with prorated billing
- Overage fees for exceeding data caps
- Billing cycle synchronization with tariff plans
- Invoice item creation for tariff-related charges
- User billing information retrieval

## Installation and Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- RADIUS server (FreeRADIUS recommended)
- Billing module

### Environment Variables

The module requires the following environment variables:

```
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/isp_management

# RADIUS Integration
RADIUS_API_URL=http://radius-server:8000/api
RADIUS_API_KEY=your_api_key
RADIUS_API_TIMEOUT=10.0

# Billing Integration
BILLING_API_URL=http://billing-service:8000/api
BILLING_API_KEY=your_api_key
BILLING_API_TIMEOUT=10.0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Monitoring
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=password
```

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/isp-management.git
   cd isp-management
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the service:
   ```bash
   uvicorn isp_management.main:app --host 0.0.0.0 --port 8000
   ```

5. Start Celery worker:
   ```bash
   celery -A modules.tariff.tasks worker -l info
   ```

6. Start Celery beat for scheduled tasks:
   ```bash
   celery -A modules.tariff.tasks beat -l info
   ```

## API Documentation

Detailed API documentation is available in the [api_documentation.md](../../docs/modules/tariff/api_documentation.md) file.

## Development

### Branching Strategy

The project follows a modified GitFlow branching strategy:

- `main`: Production-ready code
- `develop`: Main development branch
- `feature/*`: For new features
- `bugfix/*`: For bug fixes
- `hotfix/*`: For critical production fixes
- `release/*`: For preparing releases

### Testing

Run the test suite with:

```bash
pytest tests/modules/tariff/
```

For integration tests:

```bash
pytest tests/integration/tariff/
```

### CI/CD

The module includes a GitHub Actions workflow for continuous integration and deployment:

- Automated testing on pushes and pull requests
- Docker image building and publishing
- Deployment to staging and production environments

## Deployment

### Docker

A Dockerfile is provided for containerization:

```bash
docker build -t isp-management/tariff-module:latest -f modules/tariff/Dockerfile .
docker run -p 8000:8000 isp-management/tariff-module:latest
```

### Kubernetes

Kubernetes deployment manifests are available in the `deployment/kubernetes/` directory:

```bash
kubectl apply -f deployment/kubernetes/tariff-module.yaml
```

## Monitoring

The module exposes Prometheus metrics at the `/metrics` endpoint for monitoring:

- Usage tracking metrics
- Policy enforcement actions
- API request rates and latencies
- Error rates

## Troubleshooting

Common issues and their solutions:

1. **RADIUS Integration Failures**:
   - Check RADIUS API URL and credentials
   - Verify network connectivity between services
   - Check RADIUS server logs for errors

2. **Billing Integration Issues**:
   - Verify Billing API URL and credentials
   - Check for consistent user IDs across systems
   - Review billing service logs

3. **Scheduled Tasks Not Running**:
   - Ensure Celery worker and beat are running
   - Check Redis connectivity
   - Verify task registration in `celery_config.py`

## Contributing

1. Create a feature branch from `develop`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
