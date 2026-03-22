from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "sdn_controller",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.device_poll", "app.tasks.alarm_check"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        # Poll PENDING/ERROR devices every 5 minutes
        "poll-pending-devices": {
            "task": "app.tasks.device_poll.poll_pending_devices",
            "schedule": crontab(minute="*/5"),
        },
        # Poll MANAGED devices for port/vlan/endpoint every 1 minute
        "poll-managed-devices": {
            "task": "app.tasks.device_poll.poll_managed_devices",
            "schedule": crontab(minute="*"),
        },
        # Check alarms every 1 minute
        "check-alarms": {
            "task": "app.tasks.alarm_check.check_all_devices",
            "schedule": crontab(minute="*"),
        },
    },
)
