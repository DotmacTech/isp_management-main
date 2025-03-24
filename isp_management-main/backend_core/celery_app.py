"""
Celery configuration for the ISP Management Platform.
"""
from celery import Celery
from celery.schedules import crontab
import os

# Set the default Django settings module
os.environ.setdefault('ISP_MANAGEMENT_SETTINGS', 'isp_management.settings')

app = Celery('isp_management')

# Load configuration from environment variables prefixed with ISP_CELERY_
app.config_from_envvar('ISP_CELERY', silent=True)

# Load task modules from all registered apps
app.autodiscover_tasks(['isp_management.modules.billing', 'modules.config_management'])

# Configure the scheduled tasks
app.conf.beat_schedule = {
    'send-invoice-reminders-daily': {
        'task': 'isp_management.modules.billing.tasks.send_invoice_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9:00 AM
        'args': (),
    },
    'generate-monthly-billing-report': {
        'task': 'isp_management.modules.billing.tasks.generate_monthly_billing_report',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),  # Run on the 1st of each month at 1:00 AM
        'args': (),
    },
    'clear-template-cache-weekly': {
        'task': 'isp_management.modules.billing.tasks.clear_template_cache',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),  # Run every Sunday at 2:00 AM
        'args': (),
    },
    'sync-configurations-to-elasticsearch': {
        'task': 'sync_configurations_to_elasticsearch',
        'schedule': crontab(minute=0, hour='*/3'),  # Run every 3 hours
        'args': (),
    },
    'cleanup-configuration-history': {
        'task': 'cleanup_configuration_history',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),  # Run on the 1st of each month at 3:00 AM
        'args': (90,),  # Keep 90 days of history
    },
}

# Configure Celery to use Redis as the broker and result backend
app.conf.broker_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Configure task serialization
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'

# Configure task execution settings
app.conf.task_acks_late = True  # Tasks are acknowledged after the task is executed
app.conf.worker_prefetch_multiplier = 1  # Prefetch only one task at a time
app.conf.task_ignore_result = True  # Don't store task results

# Configure task routing
app.conf.task_routes = {
    'isp_management.modules.billing.*': {'queue': 'billing'},
}

if __name__ == '__main__':
    app.start()
