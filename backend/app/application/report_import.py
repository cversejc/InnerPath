"""Consultant fast path: import a finished report and jump to final review.

The six-node flow stays intact; this orchestration marks the authoring steps as
completed, activates S6, and materializes the imported text as the confirmed
narrative plan and report fragments the quality gate and assembler already
read. The full-report check still runs and its findings are shown, but on this
path they are advice: the consultant's single final-gate attestation decides
delivery, and the override plus the advisories it covered are recorded on the
S6 row.

Reports already written in the three required sections are parsed locally. Any
other wording is normalized by the model layer in
`application/report_import_normalization.py`, and the model answer must pass the
same strict parser before a single workflow row is touched.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.report_import_normalization import (
    RECOVERABLE_PARSE_CODES,
    NormalizationGateway,
    normalize_report_content,
    prepare_local_report,
)
from app.core.time import utc_now_naive
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.content.models import ContentFragmentRevision, NarrativePlan
from app.domains.content.report_import import (
    ReportImportError,
    parse_report_content,
    verify_content_hash,
)
from app.domains.skills.bindings import resolve_case_skill
from app.domains.skills.models import SkillRun
from app.domains.skills.service import create_skill_run
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.authorization import (
    SPECIALTY_FIELDS,
    consultant_capabilities,
    validate_step_actor,
)
from app.domains.workflow.models import ReportCase, StepTask, WorkflowInstance


IMPORT_REVIEW_POLICY_VERSION = "import-review-v1"
IMPORT_TARGET_TYPE = "REPORT_IMPORT"
IMPORT_CANDIDATE_KEY = "imported-report-v1"
IMPORT_AUTHORING_STEP_KEYS = ("S1", "S2", "S3", "S4", "S5")
IMPORTABLE_STEP_STATUSES = {"PENDING", "READY"}


def claim_final_step(final_step: StepTask, *, actor, request_row: Optional[ServiceRequest]) -> None:
    """Give the importer ownership of S6 the same way an assignment or a
    specialty claim would, without stealing another consultant's case.

    Admins orchestrate the fast path but never become the professional owner, so
    their imports keep whatever assignment is already on the case.
    """
    if actor.role != "consultant":
        return
    capability = getattr(final_step, "required_capability", None)
    if capability in SPECIALTY_FIELDS:
        if capability not in consultant_capabilities(actor):
            raise ReportImportError("report_case_forbidden")
        field = SPECIALTY_FIELDS[capability]
        owner_id = getattr(request_row, field, None) if request_row is not None else None
        if owner_id not in (None, actor.id):
            raise ReportImportError("report_case_forbidden")
        if request_row is not None:
            setattr(request_row, field, actor.id)
    elif final_step.assignee_id not in (None, actor.id):
        raise ReportImportError("report_case_forbidden")
    final_step.assignee_id = actor.id


async def import_report_case(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    actor,
    content: str,
    content_sha256: str,
    idempotency_key: str,
    title: Optional[str] = None,
    source_filename: Optional[str] = None,
    audit_context: Optional[AuditContext] = None,
    normalization_gateway: Optional[NormalizationGateway] = None,
) -> ReportCase:
    sections = None
    parse_error: Optional[ReportImportError] = None
    try:
        sections = parse_report_content(content)
    except ReportImportError as error:
        # Structure problems are what the model layer exists for; missing,
        # oversized and hash-checked bodies must fail before any provider call.
        if str(error) not in RECOVERABLE_PARSE_CODES:
            raise
        parse_error = error

    content_hash = verify_content_hash(content, content_sha256)
    normalized_key = str(idempotency_key or "").strip()
    if not normalized_key:
        raise ReportImportError("report_import_idempotency_key_required")

    locked_case = await db.scalar(
        select(ReportCase).where(ReportCase.id == report_case.id).with_for_update()
    )
    if locked_case is None:
        raise ReportImportError("report_case_not_found")
    report_case = locked_case

    steps = list(
        await db.scalars(
            select(StepTask)
            .where(StepTask.workflow_instance_id == report_case.workflow_instance_id)
            .order_by(StepTask.sequence_no)
            .with_for_update()
        )
    )
    by_key = {step.step_key: step for step in steps}
    final_step = by_key.get("S6")
    if final_step is None or any(key not in by_key for key in IMPORT_AUTHORING_STEP_KEYS):
        raise ReportImportError("report_import_case_not_importable")

    existing_import = await db.scalar(
        select(SkillRun)
        .where(
            SkillRun.report_case_id == report_case.id,
            SkillRun.target_type == IMPORT_TARGET_TYPE,
        )
        .order_by(SkillRun.id.desc())
        .limit(1)
    )
    replay = await _resolve_replay(
        db,
        report_case=report_case,
        existing_import=existing_import,
        content_hash=content_hash,
        idempotency_key=normalized_key,
    )
    if replay is not None:
        return replay

    if (
        report_case.status in {"DELIVERED", "CANCELLED"}
        or report_case.review_policy_version != "six-node-review-v1"
        or any(step.status not in IMPORTABLE_STEP_STATUSES for step in steps)
    ):
        raise ReportImportError("report_import_case_not_importable")

    request_row = None
    if report_case.service_request_id is not None:
        request_row = await db.scalar(
            select(ServiceRequest)
            .where(ServiceRequest.id == report_case.service_request_id)
            .with_for_update()
        )
        if request_row is None or request_row.status in {"withdrawn", "rejected"}:
            raise ReportImportError("report_import_case_not_importable")

    claim_final_step(final_step, actor=actor, request_row=request_row)
    try:
        validate_step_actor(final_step, actor)
    except ValueError as error:
        raise ReportImportError("report_case_forbidden") from error

    instance = await db.get(WorkflowInstance, report_case.workflow_instance_id)
    if instance is None or instance.status != "RUNNING":
        raise ReportImportError("report_import_case_not_importable")

    # Only now, with the case verified importable and the replay checks done,
    # is it safe to spend a provider call on structure normalization.
    prepared = (
        prepare_local_report(sections)
        if sections is not None
        else await normalize_report_content(
            content, parse_error=parse_error, gateway=normalization_gateway
        )
    )

    validator_skill = await resolve_case_skill(db, report_case, "report.final_validator")
    now = utc_now_naive()

    for step_key in IMPORT_AUTHORING_STEP_KEYS:
        step = by_key[step_key]
        step.status = "COMPLETED"
        step.activation_no = max(step.activation_no, 1)
        step.activated_at = step.activated_at or now
        step.started_at = step.started_at or now
        step.completed_at = step.completed_at or now
        step.updated_at = now
        step.result_json = {
            **(step.result_json or {}),
            "imported": True,
            "import_idempotency_key": normalized_key,
        }

    final_step.status = "IN_REVIEW"
    final_step.activation_no = max(final_step.activation_no, 1)
    final_step.activated_at = final_step.activated_at or now
    final_step.started_at = final_step.started_at or now
    final_step.completed_at = None
    final_step.updated_at = now

    report_case.review_policy_version = IMPORT_REVIEW_POLICY_VERSION
    report_case.status = "ACTIVE"
    report_case.updated_at = now
    if request_row is not None:
        request_row.status = "reviewing"
        request_row.reviewing_at = request_row.reviewing_at or now
        request_row.updated_by = actor.id
        # Mirrors assign_step: the primary owner mirrors whichever specialty
        # owner exists, and an admin import never rewrites existing ownership.
        request_row.assigned_consultant_id = (
            request_row.assigned_consultant_id
            or request_row.assigned_mingli_consultant_id
            or request_row.assigned_psychology_consultant_id
        )

    run, created = await create_skill_run(
        db,
        skill_version_id=validator_skill.id,
        idempotency_key=f"report-import:{report_case.id}:{normalized_key}",
        input_snapshot={
            "content_sha256": content_hash,
            "normalized_content_sha256": prepared.sha256,
            "section_keys": [section.fragment_key for section in prepared.sections],
            "used_model_normalization": prepared.used_model,
            "normalization_prompt_sha256": prepared.prompt_sha256,
        },
        context_snapshot={
            "report_import_key": normalized_key,
            "report_import_sha256": content_hash,
            "report_import_normalized_sha256": prepared.sha256,
            "used_model_normalization": prepared.used_model,
            "source_filename": source_filename,
            "imported_at": now.isoformat(),
        },
        run_type="INITIAL",
        target_type=IMPORT_TARGET_TYPE,
        target_key=content_hash,
        report_case_id=report_case.id,
        workflow_instance_id=report_case.workflow_instance_id,
        step_task_id=final_step.id,
    )
    if not created:
        raise ReportImportError("report_import_idempotency_conflict")
    run.status = "COMPLETED"
    run.started_at = now
    run.completed_at = now
    run.model_trace = prepared.trace
    run.output_raw = prepared.content if prepared.used_model else None
    run.output_parsed = {
        "sections": [
            {
                "section_key": section.section_key,
                "fragment_key": section.fragment_key,
                "title": section.title,
                "content": section.content,
            }
            for section in prepared.sections
        ]
    }

    plan = NarrativePlan(
        report_case_id=report_case.id,
        version_no=1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=run.id,
        selected_candidate_key=IMPORT_CANDIDATE_KEY,
        plan_json=build_import_plan_json(
            prepared.sections,
            title=title,
            content_sha256=content_hash,
            normalized_content_sha256=prepared.sha256,
            used_model_normalization=prepared.used_model,
        ),
        source_snapshot={
            "source": "consultant_import",
            "content_sha256": content_hash,
            "normalized_content_sha256": prepared.sha256,
            "used_model_normalization": prepared.used_model,
            "source_filename": source_filename,
            "imported_at": now.isoformat(),
        },
        created_by=actor.id,
        confirmed_by=actor.id,
        created_at=now,
        confirmed_at=now,
    )
    db.add(plan)
    await db.flush()

    for section in prepared.sections:
        db.add(
            ContentFragmentRevision(
                report_case_id=report_case.id,
                fragment_key=section.fragment_key,
                revision_no=1,
                semantic_revision=1,
                content_revision=1,
                fragment_type="REPORT",
                title=section.title,
                content=section.content,
                status="CONFIRMED",
                source_snapshot={
                    "source": "consultant_import",
                    "content_sha256": content_hash,
                    "normalized_content_sha256": prepared.sha256,
                    "used_model_normalization": prepared.used_model,
                    "source_filename": source_filename,
                    "imported_at": now.isoformat(),
                },
                edit_kind="SEMANTIC",
                is_current=True,
                owner_step_task_id=final_step.id,
                source_skill_run_id=run.id,
                source_narrative_plan_id=plan.id,
                created_by=actor.id,
                created_at=now,
            )
        )
    await db.flush()

    await record_audit(
        db,
        actor.id,
        "report_case.import",
        "report_case",
        str(report_case.id),
        target_user_id=report_case.user_id,
        details={
            "content_sha256": content_hash,
            "normalized_content_sha256": prepared.sha256,
            "used_model_normalization": prepared.used_model,
            "normalization_prompt_sha256": prepared.prompt_sha256,
            "source_filename": source_filename,
            "idempotency_key": normalized_key,
            "review_policy_version": IMPORT_REVIEW_POLICY_VERSION,
        },
        audit_context=audit_context,
    )
    return report_case


def build_import_plan_json(
    sections,
    *,
    title,
    content_sha256,
    normalized_content_sha256: Optional[str] = None,
    used_model_normalization: bool = False,
) -> dict:
    chapters = {
        "report.identity": "identity",
        "report.challenge": "challenge",
        "report.direction": "direction",
    }
    by_key = {section.fragment_key: section for section in sections}
    core_theme = (title or "").strip() or _core_theme_from(by_key["report.identity"].content)
    fragments = []
    for sequence_no, section in enumerate(sections, start=1):
        fragments.append(
            {
                "fragment_key": section.fragment_key,
                "chapter": chapters[section.fragment_key],
                "sequence_no": sequence_no,
                "title": section.title,
                "purpose": f"已由咨询师导入并确认的“{section.title}”正文。",
                "required": True,
            }
        )
    return {
        "core_theme": core_theme,
        "revision_no": 1,
        "content_plan": {
            "status": "READY",
            "fragments": fragments,
            "semantic_priorities": {"must_include": []},
        },
        "source": {
            "kind": "consultant_import",
            "content_sha256": content_sha256,
            "normalized_content_sha256": normalized_content_sha256 or content_sha256,
            "used_model_normalization": used_model_normalization,
        },
    }


def _core_theme_from(identity_content: str) -> str:
    for line in identity_content.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            return cleaned[:200]
    return "咨询师导入报告"


async def _resolve_replay(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    existing_import: Optional[SkillRun],
    content_hash: str,
    idempotency_key: str,
) -> Optional[ReportCase]:
    if existing_import is not None:
        existing_context = existing_import.context_snapshot or {}
        if existing_context.get("report_import_key") != idempotency_key:
            raise ReportImportError("report_import_idempotency_conflict")
        if existing_context.get("report_import_sha256") != content_hash:
            raise ReportImportError("report_import_idempotency_conflict")
        return report_case
    duplicate = await db.scalar(
        select(SkillRun.id).where(
            SkillRun.target_type == IMPORT_TARGET_TYPE,
            SkillRun.target_key == content_hash,
        )
    )
    if duplicate is not None:
        raise ReportImportError("report_import_duplicate_content")
    return None
