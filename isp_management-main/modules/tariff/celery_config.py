"""
Celery configuration for the Tariff Enforcement Module.

This module defines the schedule for recurring tasks related to tariff enforcement,
such as processing scheduled plan changes, resetting billing cycles, and sending
usage notifications.
"""

from celery.schedules import crontab

# Define task schedules
CELERYBEAT_SCHEDULE = {
    # Process scheduled tariff plan changes daily at 1:00 AM
    'process-scheduled-plan-changes': {
        'task': 'tariff.process_scheduled_plan_changes',
        'schedule': crontab(hour=1, minute=0),
        'options': {'queue': 'tariff'}
    },
    
    # Reset billing cycles daily at 2:00 AM
    'reset-billing-cycles': {
        'task': 'tariff.reset_billing_cycles',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'tariff'}
    },
    
    # Send usage notifications daily at 8:00 AM
    'send-usage-notifications': {
        'task': 'tariff.send_usage_notifications',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'tariff'}
    },
    
    # Clean up expired plans daily at 3:00 AM
    'cleanup-expired-plans': {
        'task': 'tariff.cleanup_expired_plans',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'tariff'}
    },
    
    # Sync RADIUS policies weekly on Sunday at 4:00 AM
    'sync-radius-policies': {
        'task': 'tariff.sync_radius_policies',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        'options': {'queue': 'tariff'}
    }
}

# Task routing
CELERY_ROUTES = {
    'tariff.*': {'queue': 'tariff'}
}

# Task serialization format
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Task result backend
CELERY_RESULT_BACKEND = 'redis'

# Task result expiration time (in seconds)
CELERY_TASK_RESULT_EXPIRES = 86400  # 24 hours

# Maximum number of tasks a worker can execute before it's replaced
CELERYD_MAX_TASKS_PER_CHILD = 1000

# Concurrency settings
CELERYD_CONCURRENCY = 4

# Retry settings
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Logging
CELERYD_LOG_COLOR = False
