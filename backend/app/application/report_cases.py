from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.schemas import ServiceRequestCreate
from app.domains.service_requests.users import create_service_request
from app.domains.content.service import sync_application_evidence
from app.domains.workflow.definitions import (
    DEFAULT_WORKFLOW_KEY,
    default_workflow_definition,
)
from app.domains.workflow.models import ReportCase, WorkflowVersion
from app.domains.workflow.service import cancel_case, create_report_case
from app.models.user import User


async def ensure_default_workflow_version(db: AsyncSession) -> WorkflowVersion:
    existing = await db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_key == DEFAULT_WORKFLOW_KEY,
            WorkflowVersion.version == 1,
        )
    )
    if existing:
        return existing

    version = WorkflowVersion(
        workflow_key=DEFAULT_WORKFLOW_KEY,
        name="咨询师报告生产流程",
        version=1,
        status="PUBLISHED",
        definition_json=default_workflow_definition(),
        created_by=None,
        published_by=None,
        created_at=datetime.utcnow(),
        published_at=datetime.utcnow(),
    )
    try:
        async with db.begin_nested():
            db.add(version)
            await db.flush()
        return version
    except IntegrityError:
        existing = await db.scalar(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_key == DEFAULT_WORKFLOW_KEY,
                WorkflowVersion.version == 1,
            )
        )
        if existing:
            return existing
        raise


async def get_report_case_for_service_request(
    db: AsyncSession, service_request_id: int
) -> Optional[ReportCase]:
    return await db.scalar(
        select(ReportCase).where(ReportCase.service_request_id == service_request_id)
    )


async def ensure_legacy_report_request(db: AsyncSession, request: ServiceRequest) -> None:
    if request.service_type != "report":
        return
    if await get_report_case_for_service_request(db, request.id):
        raise ValueError("report_case_workflow_required")


async def create_user_service_request(
    db: AsyncSession,
    user: User,
    data: ServiceRequestCreate,
    *,
    audit_context=None,
) -> tuple[ServiceRequest, Optional[ReportCase]]:
    if data.service_type != "report":
        request = await create_service_request(
            db, user, data, audit_context=audit_context
        )
        return request, None

    request = await create_service_request(
        db, user, data, audit_context=audit_context, commit=False
    )
    report_case = await get_report_case_for_service_request(db, request.id)
    if report_case is None and request.status not in {"withdrawn", "rejected"}:
        await ensure_default_workflow_version(db)
        report_case = await create_report_case(
            db,
            user_id=user.id,
            service_request_id=request.id,
            source_report_task_id=None,
            application_snapshot=request.request_payload,
        )
    if report_case is not None:
        await sync_application_evidence(
            db,
            report_case_id=report_case.id,
            application_snapshot=report_case.application_snapshot or {},
        )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if data.idempotency_key:
            request = await db.scalar(
                select(ServiceRequest).where(
                    ServiceRequest.user_id == user.id,
                    ServiceRequest.idempotency_key == data.idempotency_key,
                )
            )
            if request:
                report_case = await db.scalar(
                    select(ReportCase).where(
                        ReportCase.service_request_id == request.id
                    )
                )
                if report_case:
                    return request, report_case
        raise
    await db.refresh(request)
    if report_case:
        await db.refresh(report_case)
    return request, report_case


async def cancel_report_case_for_service_request(
    db: AsyncSession, service_request_id: int, *, reason: str
) -> Optional[ReportCase]:
    report_case = await db.scalar(
        select(ReportCase)
        .where(ReportCase.service_request_id == service_request_id)
        .with_for_update()
    )
    if report_case is None:
        return None
    return await cancel_case(db, report_case.id, reason=reason)
