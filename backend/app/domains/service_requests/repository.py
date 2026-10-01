"""Persistence helpers shared by service request workflows."""

from copy import deepcopy
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest, ServiceRequestDraft, ServiceRequestRevision, ServiceRequestTask


async def _get_request_for_update(db: AsyncSession, request_id: int) -> Optional[ServiceRequest]:
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
    )
    return result.scalar_one_or_none()

async def _get_draft(db: AsyncSession, request_id: int) -> Optional[ServiceRequestDraft]:
    result = await db.execute(
        select(ServiceRequestDraft).where(ServiceRequestDraft.request_id == request_id)
    )
    return result.scalar_one_or_none()

async def _get_draft_for_update(db: AsyncSession, request_id: int) -> Optional[ServiceRequestDraft]:
    result = await db.execute(
        select(ServiceRequestDraft)
        .where(ServiceRequestDraft.request_id == request_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()

async def _get_latest_task(db: AsyncSession, request_id: int) -> Optional[ServiceRequestTask]:
    result = await db.execute(
        select(ServiceRequestTask)
        .where(ServiceRequestTask.request_id == request_id)
        .order_by(ServiceRequestTask.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def _append_revision(
    db: AsyncSession,
    request_id: int,
    stage: str,
    payload: dict[str, Any],
    created_by: Optional[int],
) -> ServiceRequestRevision:
    version = int(
        await db.scalar(
            select(func.max(ServiceRequestRevision.version_number)).where(
                ServiceRequestRevision.request_id == request_id
            )
        )
        or 0
    ) + 1
    revision = ServiceRequestRevision(
        request_id=request_id,
        version_number=version,
        stage=stage,
        payload=deepcopy(payload),
        created_by=created_by,
    )
    db.add(revision)
    await db.flush()
    return revision
