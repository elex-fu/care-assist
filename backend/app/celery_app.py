import os

from celery import Celery
from celery.schedules import crontab

from app.config import settings

broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL
scan_interval = int(os.getenv("CELERY_SCAN_INTERVAL_SEC", settings.CELERY_SCAN_INTERVAL_SEC))

celery_app = Celery("care_assist", broker=broker, backend=backend)
celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "generate-medication-logs": {
            "task": "care_assist.generate_medication_logs",
            "schedule": crontab(hour=0, minute=5),
        },
        "scan-missed-medications": {
            "task": "care_assist.scan_missed_medications",
            "schedule": scan_interval,
        },
        "scan-overdue-vaccines": {
            "task": "care_assist.scan_overdue_vaccines",
            "schedule": scan_interval,
        },
        "scan-overdue-reminders": {
            "task": "care_assist.scan_overdue_reminders",
            "schedule": scan_interval,
        },
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

# Import task modules so Celery can discover them
celery_app.autodiscover_tasks(["app.tasks"])
