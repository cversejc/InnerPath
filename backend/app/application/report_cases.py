from datetime import datetime
from app.core.time import utc_now_naive
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.schemas import ServiceRequestCreate
from app.domains.service_requests.users import create_service_request
from app.domains.content.service import sync_application_evidence
from app.domains.workflow.definitions import (
    DEFAULT_WORKFLOW_KEY,
    SIMPLE_WORKFLOW_KEY,
    case_workflow_key,
    default_workflow_definition,
    normalize_workflow_key,
)
from app.domains.workflow.simple_definitions import (
    SIMPLE_PROTOCOL_LEGACY,
    ai_assisted_simple_workflow_definition,
    normalize_simple_protocol,
    simple_protocol_from_definition,
    simple_workflow_definition,
)
from app.domains.workflow.models import ReportCase, WorkflowVersion
from app.domains.workflow.service import cancel_case, create_report_case
from app.domains.workflow.service import latest_published_version, create_workflow_draft, publish_workflow_version
from copy import deepcopy
from app.models.user import User
from app.domains.workflow.authorization import STEP_SPECIALTIES

COLLABORATION_CONTRACT_VERSION = "professional-handoff-v2"


def _has_current_collaboration_contract(version: Optional[WorkflowVersion]) -> bool:
    if version is None:
        return False
    definition = version.definition_json or {}
    contract = definition.get("collaboration_contract") or {}
    if (
        contract.get("version") != COLLABORATION_CONTRACT_VERSION
        or contract.get("step_specialties") != STEP_SPECIALTIES
    ):
        return False
    steps = {step.get("step_key"): step for step in definition.get("steps", [])}
    return all(
        steps.get(step_key, {}).get("required_capability") == specialty
        for step_key, specialty in STEP_SPECIALTIES.items()
    )


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
        created_at=utc_now_naive(),
        published_at=utc_now_naive(),
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


async def _latest_simple_version_for_protocol(
    db: AsyncSession, protocol: str
) -> Optional[WorkflowVersion]:
    """Return the newest published ``report.simple`` version of one protocol.

    The workflow key is shared by both protocols, so the frozen definition
    marker, not the version number alone, decides which version a case wants.
    """
    versions = list(
        (
            await db.scalars(
                select(WorkflowVersion)
                .where(
                    WorkflowVersion.workflow_key == SIMPLE_WORKFLOW_KEY,
                    WorkflowVersion.status == "PUBLISHED",
                )
                .order_by(WorkflowVersion.version.desc())
            )
        ).all()
    )
    for version in versions:
        if simple_protocol_from_definition(version.definition_json) == protocol:
            return version
    return None


async def _next_simple_version_number(db: AsyncSession) -> int:
    """Return the next globally unique version number for ``report.simple``.

    The unique constraint covers ``(workflow_key, version)`` across both
    protocols, so numbering must not restart per protocol.
    """
    latest_number = await db.scalar(
        select(func.max(WorkflowVersion.version)).where(
            WorkflowVersion.workflow_key == SIMPLE_WORKFLOW_KEY
        )
    )
    return int(latest_number or 0) + 1


async def ensure_simple_workflow_version(
    db: AsyncSession, protocol: str = SIMPLE_PROTOCOL_LEGACY
) -> WorkflowVersion:
    """Return the published built-in version matching protocol and code.

    The simplified workflow follows the shared report node catalog. It has no
    authoring screen, so its code definition is published on first use.
    Existing cases keep their frozen workflow version; when a protocol's code
    definition changes, new cases receive a new version instead of reusing the
    stale one. The legacy protocol stays the default so existing callers and
    cases are untouched until the AI protocol is explicitly enabled.
    """
    protocol = normalize_simple_protocol(protocol)
    if protocol == SIMPLE_PROTOCOL_LEGACY:
        definition = simple_workflow_definition()
        name = "简化报告流程"
    else:
        definition = ai_assisted_simple_workflow_definition()
        name = "简化报告流程（AI 辅助）"
    latest = await _latest_simple_version_for_protocol(db, protocol)
    if latest is not None and latest.definition_json == definition:
        return latest

    now = utc_now_naive()
    version = WorkflowVersion(
        workflow_key=SIMPLE_WORKFLOW_KEY,
        name=name,
        version=await _next_simple_version_number(db),
        status="PUBLISHED",
        definition_json=definition,
        created_by=None,
        published_by=None,
        created_at=now,
        published_at=now,
    )
    try:
        async with db.begin_nested():
            db.add(version)
            await db.flush()
        return version
    except IntegrityError:
        latest = await _latest_simple_version_for_protocol(db, protocol)
        if latest is not None and latest.definition_json == definition:
            return latest
        raise


async def ensure_collaborative_workflow_version(db: AsyncSession) -> WorkflowVersion:
    from app.application.skill_runtime import ensure_analysis_workflow_version
    await ensure_default_workflow_version(db)
    await ensure_analysis_workflow_version(db)
    latest = await latest_published_version(db)
    if _has_current_collaboration_contract(latest):
        return latest
    if latest is None:
        raise ValueError("workflow_version_not_published")
    definition = deepcopy(latest.definition_json)
    definition["collaboration_contract"] = {
        "version": COLLABORATION_CONTRACT_VERSION,
        "step_specialties": STEP_SPECIALTIES,
    }
    for step in definition["steps"]:
        step["required_capability"] = STEP_SPECIALTIES[step["step_key"]]
    # Published workflow versions and existing cases stay immutable.
    try:
        async with db.begin_nested():
            version = await create_workflow_draft(db, DEFAULT_WORKFLOW_KEY, "命理与心理协作报告流程", definition, created_by=None)
            return await publish_workflow_version(db, version.id, published_by=None)
    except IntegrityError:
        latest = await latest_published_version(db)
        if _has_current_collaboration_contract(latest):
            return latest
        raise


async def get_report_case_for_service_request(
    db: AsyncSession, service_request_id: int
) -> Optional[ReportCase]:
    return await db.scalar(
        select(ReportCase).where(ReportCase.service_request_id == service_request_id)
    )


def ensure_legacy_service_request_allowed(request: ServiceRequest) -> None:
    """Keep the legacy AI-draft endpoints available for calendars only."""
    if request.service_type == "report":
        raise ValueError("report_case_workflow_required")


async def create_user_service_request(
    db: AsyncSession,
    user: User,
    data: ServiceRequestCreate,
    *,
    audit_context=None,
) -> tuple[ServiceRequest, Optional[ReportCase]]:
    if data.service_type == "calendar":
        raise ValueError("calendar_requires_delivered_report")
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
        request_payload = request.request_payload or {}
        workflow_key = normalize_workflow_key(case_workflow_key(request_payload))
        if workflow_key == SIMPLE_WORKFLOW_KEY:
            # The request payload freezes which Simple protocol was requested;
            # only an explicit AI-assisted request leaves the legacy default.
            workflow_version = await ensure_simple_workflow_version(
                db,
                simple_protocol_from_definition(request_payload),
            )
        else:
            workflow_version = await ensure_collaborative_workflow_version(db)
        report_case = await create_report_case(
            db,
            user_id=user.id,
            service_request_id=request.id,
            source_report_task_id=None,
            application_snapshot=request.request_payload,
            workflow_version=workflow_version,
        )
    if report_case is not None and case_workflow_key(report_case) != SIMPLE_WORKFLOW_KEY:
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
