from typing import Callable, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest, ServiceRequestTask
from app.domains.service_requests.service import create_ai_draft_task
from app.models.user import User

TaskDispatcher = Callable[[int, str], None]


async def start_service_request_ai_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    request: Optional[Request] = None,
    *,
    dispatch_task: TaskDispatcher,
    force: bool = False,
    retry_of_task_id: Optional[str] = None,
) -> ServiceRequestTask:
    task, should_dispatch = await create_ai_draft_task(
        db,
        service_request,
        actor,
        request=request,
        force=force,
        retry_of_task_id=retry_of_task_id,
    )
    if should_dispatch:
        dispatch_task(task.request_id, task.task_id)
    return task
