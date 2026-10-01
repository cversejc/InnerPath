from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reports.models import ReportTask


async def create_report_task(
    db: AsyncSession,
    task_id: str,
    user_id: int,
    input_snapshot: Optional[Dict[str, Any]] = None,
    retry_count: int = 0,
    retry_of_task_id: Optional[str] = None,
) -> ReportTask:
    task = ReportTask(
        task_id=task_id,
        user_id=user_id,
        status="processing",
        progress=0,
        input_snapshot=input_snapshot,
        retry_count=retry_count,
        retry_of_task_id=retry_of_task_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_report_task(
    db: AsyncSession, task_id: str, user_id: int
) -> Optional[ReportTask]:
    result = await db.execute(
        select(ReportTask).where(
            ReportTask.task_id == task_id, ReportTask.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_report_task_by_id(db: AsyncSession, task_id: str) -> Optional[ReportTask]:
    result = await db.execute(select(ReportTask).where(ReportTask.task_id == task_id))
    return result.scalar_one_or_none()
