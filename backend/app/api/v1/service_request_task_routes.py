from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.service_request import ServiceRequestTaskResponse
from app.services.service_request_service import get_service_request, serialize_task, staff_can_access

task_router = APIRouter()
@task_router.get("/{task_id}", response_model=ServiceRequestTaskResponse)
async def get_staff_task(
    task_id: str,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.service_request import ServiceRequestTask

    task = await db.get(ServiceRequestTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    service_request = await get_service_request(db, task.request_id)
    if not service_request or not staff_can_access(service_request, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not assigned")
    return ServiceRequestTaskResponse.model_validate(serialize_task(task))


