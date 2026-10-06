from celery import Celery
from celery.schedules import schedule
from app.config import settings

celery_app = Celery(
    "innerpath",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.report_tasks",
        "app.tasks.service_request_tasks",
        "app.tasks.workflow_tasks",
        "app.tasks.calendar_generation_tasks",
    ]
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=[settings.CELERY_ACCEPT_CONTENT],
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    beat_schedule={
        "dispatch-workflow-outbox": {
            "task": "dispatch_workflow_outbox",
            "schedule": schedule(run_every=15.0),
        }
    },
)
