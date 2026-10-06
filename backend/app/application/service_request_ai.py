from typing import Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.context import AuditContext
from app.domains.service_requests.models import ServiceRequest, ServiceRequestTask
from app.domains.service_requests.service import create_ai_draft_task
from app.application.report_cases import ensure_legacy_service_request_allowed
from app.models.user import User

TaskDispatcher = Callable[[int, str], None]


async def start_service_request_ai_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    audit_context: Optional[AuditContext] = None,
    *,
    dispatch_task: TaskDispatcher,
    force: bool = False,
    retry_of_task_id: Optional[str] = None,
) -> ServiceRequestTask:
    ensure_legacy_service_request_allowed(service_request)
    task, should_dispatch = await create_ai_draft_task(
        db,
        service_request,
        actor,
        audit_context=audit_context,
        force=force,
        retry_of_task_id=retry_of_task_id,
    )
    if should_dispatch:
        dispatch_task(task.request_id, task.task_id)
    return task
