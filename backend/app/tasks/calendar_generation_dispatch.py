from app.tasks.celery_app import celery_app


def dispatch_calendar_generation(request_id: int, task_id: str) -> None:
    celery_app.send_task(
        "generate_calendar_from_report",
        args=[request_id],
        task_id=task_id,
    )
