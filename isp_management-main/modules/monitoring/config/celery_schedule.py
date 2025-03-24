"""
Celery Schedule Configuration for the ISP Management Platform Monitoring Module

This module defines the Celery beat schedule for monitoring tasks.
"""

import os
from datetime import timedelta

# Default schedule intervals (can be overridden by environment variables)
DEFAULT_NETWORK_METRICS_INTERVAL = 5 * 60  # 5 minutes in seconds
DEFAULT_SYNC_LOGS_INTERVAL = 15 * 60  # 15 minutes in seconds
DEFAULT_SYNC_METRICS_INTERVAL = 15 * 60  # 15 minutes in seconds
DEFAULT_HEALTH_CHECK_INTERVAL = 60  # 1 minute in seconds

# Get schedule intervals from environment variables or use defaults
NETWORK_METRICS_INTERVAL = int(os.getenv('NETWORK_METRICS_INTERVAL', DEFAULT_NETWORK_METRICS_INTERVAL))
SYNC_LOGS_INTERVAL = int(os.getenv('SYNC_LOGS_INTERVAL', DEFAULT_SYNC_LOGS_INTERVAL))
SYNC_METRICS_INTERVAL = int(os.getenv('SYNC_METRICS_INTERVAL', DEFAULT_SYNC_METRICS_INTERVAL))
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', DEFAULT_HEALTH_CHECK_INTERVAL))

# Celery beat schedule configuration
CELERY_BEAT_SCHEDULE = {
    'collect-network-performance-metrics': {
        'task': 'modules.monitoring.tasks.collect_network_performance_metrics_task',
        'schedule': timedelta(seconds=NETWORK_METRICS_INTERVAL),
        'options': {
            'expires': NETWORK_METRICS_INTERVAL * 0.9,  # Expire if not executed within 90% of interval
        },
    },
    'sync-logs-to-elasticsearch': {
        'task': 'modules.monitoring.tasks.sync_logs_to_elasticsearch_task',
        'schedule': timedelta(seconds=SYNC_LOGS_INTERVAL),
        'options': {
            'expires': SYNC_LOGS_INTERVAL * 0.9,
        },
    },
    'sync-metrics-to-elasticsearch': {
        'task': 'modules.monitoring.tasks.sync_metrics_to_elasticsearch_task',
        'schedule': timedelta(seconds=SYNC_METRICS_INTERVAL),
        'options': {
            'expires': SYNC_METRICS_INTERVAL * 0.9,
        },
    },
    'health-check': {
        'task': 'modules.monitoring.tasks.health_check_task',
        'schedule': timedelta(seconds=HEALTH_CHECK_INTERVAL),
        'options': {
            'expires': HEALTH_CHECK_INTERVAL * 0.9,
        },
    },
}
