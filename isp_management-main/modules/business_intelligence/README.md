# Business Intelligence and Reporting Module

The Business Intelligence and Reporting module provides comprehensive reporting capabilities for the ISP Management Platform. It allows users to create, schedule, execute, and deliver reports based on data from various sources within the platform.

## Features

- **Report Templates**: Create and manage reusable report templates with customizable parameters
- **Scheduled Reports**: Schedule reports to run automatically at specified intervals
- **Multiple Output Formats**: Generate reports in various formats (PDF, CSV, Excel, HTML, JSON)
- **Data Sources**: Connect to multiple data sources including database, Elasticsearch, Redis, APIs, and files
- **Report Delivery**: Deliver reports via email, file storage, or API webhooks
- **Access Control**: Role-based access control for report operations
- **Audit Logging**: Track report access and usage

## Architecture

The module follows a modular architecture with the following components:

- **Models**: Database models for report templates, scheduled reports, report executions, etc.
- **Schemas**: Pydantic schemas for API request/response validation
- **Services**: Business logic for report management, scheduling, and execution
- **API Endpoints**: RESTful API endpoints for interacting with the module
- **Celery Tasks**: Background tasks for scheduled report generation and maintenance
- **Utilities**: Helper classes for report generation and data fetching

## Integration with Other Modules

The Business Intelligence module integrates with other modules in the ISP Management Platform:

- **Authentication**: Uses the platform's authentication system for user identification and authorization
- **Monitoring**: Provides data for monitoring dashboards and alerts
- **Billing**: Generates financial reports and billing summaries
- **Customer Management**: Creates customer-related reports and analytics
- **Elasticsearch**: Stores report execution data for analytics and visualization

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Redis server
- Elasticsearch (optional, for advanced analytics)

### Configuration

Ensure the following environment variables are set:

- `REPORT_OUTPUT_DIR`: Directory for storing report output files
- `REPORT_TEMPLATE_DIR`: Directory for storing report template files
- `ELASTICSEARCH_ENABLED`: Enable/disable Elasticsearch integration

### API Usage Examples

#### Creating a Report Template

```python
import requests

template_data = {
    "name": "Monthly Billing Summary",
    "description": "Summary of billing data for the month",
    "report_type": "financial",
    "output_formats": ["pdf", "csv"],
    "parameters_schema": {
        "type": "object",
        "properties": {
            "month": {"type": "string", "format": "month"},
            "year": {"type": "integer", "minimum": 2000}
        },
        "required": ["month", "year"]
    },
    "data_source_ids": [1, 2],
    "is_public": False
}

response = requests.post(
    "http://api.example.com/api/v1/business-intelligence/report-templates",
    json=template_data,
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

print(response.json())
```

#### Executing a Report

```python
import requests

execution_data = {
    "template_id": 1,
    "parameters": {
        "month": "03",
        "year": 2025
    }
}

response = requests.post(
    "http://api.example.com/api/v1/business-intelligence/report-executions",
    json=execution_data,
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

print(response.json())
```

## Celery Tasks

The module includes several Celery tasks for background processing:

- `business_intelligence.check_scheduled_reports`: Checks for scheduled reports that need to be executed
- `business_intelligence.process_report_execution`: Processes a report execution (generates outputs and delivers them)
- `business_intelligence.clean_old_report_outputs`: Cleans up old report outputs
- `business_intelligence.sync_report_data_to_elasticsearch`: Syncs report execution data to Elasticsearch
- `business_intelligence.generate_report_usage_metrics`: Generates metrics about report usage
- `business_intelligence.send_report_summary_notification`: Sends a summary notification about report executions

## License

This module is part of the ISP Management Platform and is subject to the same license terms.
