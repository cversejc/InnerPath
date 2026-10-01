from app.tasks.celery_app import celery_app


def dispatch_service_request_draft(request_id: int, task_id: str) -> None:
    celery_app.send_task(
        "generate_service_request_draft",
        args=[request_id],
        task_id=task_id,
    )
