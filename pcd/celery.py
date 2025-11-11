"""
Celery configuration for PCD System.

This module sets up Celery for asynchronous task processing.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pcd.settings')

app = Celery('pcd')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Limpar notificações antigas a cada dia às 3h da manhã
    'limpar-notificacoes-antigas-pcd': {
        'task': 'userpcd.tasks.limpar_notificacoes_antigas_task',
        'schedule': crontab(hour=3, minute=0),
    },
    'limpar-notificacoes-antigas-empresa': {
        'task': 'usercompany.tasks.limpar_notificacoes_antigas_empresa_task',
        'schedule': crontab(hour=3, minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
