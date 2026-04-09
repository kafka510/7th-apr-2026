import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')

app = Celery('web_app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Use DB-backed periodic schedules (django-celery-beat).
# IMPORTANT: Ensure the DB has periodic tasks populated (see management command).
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()