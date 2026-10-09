"""Node completion and delivery for the simplified report workflow.

Each node of ``report.simple`` consumes the user application plus the current
full report text and returns the next immutable full text version.  The
simplified workflow never touches the production analysis, narrative, quality
or skill-run assets; only the final node creates the legacy ``Report`` row the
existing reader consumes.
"""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now_naive
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.delivery.simple_models import SimpleReportVersion
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest
from app.domains.users.lunar_calendar import solar_date_for_birth
from app.domains.workflow.authorization import validate_step_actor
from app.domains.workflow.definitions import SIMPLE_WORKFLOW_KEY, case_workflow_key
from app.domains.workflow.service import complete_step, lock_case_and_tasks
from app.models.user import User

SUMMARY_LIMIT = 300


def _summary_from_text(report_text: str) -> str:
    flattened = " ".join(
        line.strip() for line in report_text.splitlines() if line.strip()
    )
    if len(flattened) <= SUMMARY_LIMIT:
        return flattened
    return flattened[:SUMMARY_LIMIT].rstrip()


def _final_content_payload(report_text: str) -> dict:
    summary = _summary_from_text(report_text)
    return {
        "structured_sections": [
            {
                "section_key": "report_body",
                "section_title": "报告正文",
                "content": report_text,
            }
        ],
        "summary": summary,
        "energy_profile": {
            "type": "简化流程报告",
            "core_traits": summary,
            "description": report_text,
        },
        "career_guidance": {
            "suitable_paths": [],
            "work_style": "",
            "development_suggestions": [],
        },
        "relationship_pattern": {
            "style": "",
            "strengths": [],
            "challenges": [],
            "growth_direction": "",
        },
        "personal_growth": {"action_plan": []},
    }


def _birth_date_for_snapshot(snapshot: dict) -> date:
    profile = snapshot.get("profile") or {}
    try:
        return solar_date_for_birth(
            int(profile["birth_year"]),
            int(profile["birth_month"]),
            int(profile["birth_day"]),
            calendar_type=profile.get("calendar_type", "solar"),
            is_leap_month=bool(profile.get("birth_is_leap_month", False)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("report_profile_snapshot_invalid") from error


async def complete_simple_report_step(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
    report_text: str,
    review_note: Optional[str] = None,
    final_gate_confirmed: bool = False,
    audit_context: Optional[AuditContext] = None,
) -> tuple[SimpleReportVersion, Optional[Report]]:
    """Complete one simplified node and persist the resulting full-text version.

    Round numbers, version numbers and the final flag are derived from the
    frozen ``config_snapshot`` of the step task, so clients cannot forge them.
    """
    report_case, instance, tasks = await lock_case_and_tasks(db, case_id)
    if case_workflow_key(report_case) != SIMPLE_WORKFLOW_KEY:
        raise ValueError("workflow_key_mismatch")
    if instance.status != "RUNNING" or report_case.status in {"CANCELLED", "DELIVERED"}:
        raise ValueError("workflow_not_active")
    task = next((item for item in tasks if item.step_key == step_key), None)
    if task is None:
        raise ValueError("step_task_not_found")
    if task.status != "IN_REVIEW":
        raise ValueError("step_not_in_review")
    if any(
        previous.sequence_no < task.sequence_no and previous.status != "COMPLETED"
        for previous in tasks
    ):
        raise ValueError("workflow_step_order_invalid")
    if any(
        other.id != task.id and other.status in {"IN_REVIEW", "EXECUTING"}
        for other in tasks
    ):
        raise ValueError("step_not_current")
    validate_step_actor(task, actor)

    text = (report_text or "").strip()
    if not text:
        raise ValueError("simple_report_text_required")
    note = (review_note or "").strip() or None
    config = task.config_snapshot or {}
    version_no = int(config.get("output_version") or task.sequence_no)
    is_final = bool(config.get("final_gate"))
    if is_final and not final_gate_confirmed:
        raise ValueError("final_gate_approval_required")

    now = utc_now_naive()
    version = SimpleReportVersion(
        report_case_id=report_case.id,
        step_task_id=task.id,
        round_no=version_no,
        version_no=version_no,
        version_label=f"v{version_no}.0",
        source_step_key=step_key,
        report_text=text,
        review_note=note,
        is_final=is_final,
        created_by=actor.id,
        created_at=now,
    )
    db.add(version)
    await db.flush()

    await complete_step(
        db,
        case_id,
        step_key,
        result_json={
            "simple_report_version_id": version.id,
            "version_no": version_no,
            "round_no": version_no,
            "is_final": is_final,
        },
        final_gate_verified=is_final,
    )
    await record_audit(
        db,
        actor.id,
        "workflow.step.complete",
        "report_case",
        str(report_case.id),
        details={
            "step_key": step_key,
            "simple_report_version_id": version.id,
            "version_no": version_no,
        },
        audit_context=audit_context,
    )

    report = None
    if is_final:
        report = await _deliver_simple_report(
            db, report_case=report_case, actor=actor, report_text=text, audit_context=audit_context
        )
    await db.commit()
    await db.refresh(version)
    return version, report


async def _deliver_simple_report(
    db: AsyncSession,
    *,
    report_case,
    actor: User,
    report_text: str,
    audit_context: Optional[AuditContext],
) -> Report:
    snapshot = report_case.application_snapshot or {}
    profile = snapshot.get("profile") or {}
    content_payload = _final_content_payload(report_text)
    summary = content_payload["summary"]
    now = utc_now_naive()

    request = None
    if report_case.service_request_id is not None:
        request = await db.scalar(
            select(ServiceRequest)
            .where(ServiceRequest.id == report_case.service_request_id)
            .with_for_update()
        )

    report = Report(
        user_id=report_case.user_id,
        request_id=report_case.service_request_id,
        title="辰鉴·人生说明书",
        birth_date=_birth_date_for_snapshot(snapshot),
        birth_time=None,
        birth_calendar_type=profile.get("calendar_type", "solar"),
        birth_place=profile.get("birth_place"),
        input_snapshot={
            "service_type": "report",
            "name": profile.get("name") or "用户",
            **snapshot,
        },
        energy_profile=content_payload["energy_profile"],
        career_guidance=content_payload["career_guidance"],
        relationship_pattern=content_payload["relationship_pattern"],
        personal_growth=content_payload["personal_growth"],
        summary=summary,
        content_payload=content_payload,
        ai_raw_content=None,
        reviewed_by=actor.id,
        reviewed_at=now,
        additional_info=(snapshot.get("context") or {}).get("additional_info"),
        status="completed",
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    await db.flush()

    report_case.status = "DELIVERED"
    report_case.delivered_at = now
    report_case.updated_at = now
    if request is not None:
        request.status = "delivered"
        request.result_type = "report"
        request.result_id = report.id
        request.delivered_at = now
        request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "report_case.deliver",
        "report_case",
        str(report_case.id),
        target_user_id=report_case.user_id,
        details={"report_id": report.id, "workflow_key": SIMPLE_WORKFLOW_KEY},
        audit_context=audit_context,
    )
    return report
