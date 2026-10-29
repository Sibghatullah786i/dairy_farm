import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecomm.settings')

app = Celery('ecomm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
