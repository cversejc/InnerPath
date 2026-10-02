from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.skills.models import SkillRun

from .common import now, require_case, require_key, validate_owner_refs
from .dependencies import invalidate_narrative_for_source, mark_dependents_stale
from .evidence import normalize_evidence_refs
from .models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)


async def _normalize_string_refs(
    db: AsyncSession,
    *,
    model,
    report_case_id: int,
    key_column,
    keys: list[str],
    missing_code: str,
    reject_statuses: set[str] | None = None,
) -> list[str]:
    normalized = []
    for item in keys:
        key = require_key(item, "content_reference_invalid")
        if key in normalized:
            continue
        row = await db.scalar(
            select(model).where(
                model.report_case_id == report_case_id,
                key_column == key,
                model.is_current.is_(True),
            )
        )
        if row is None:
            raise ValueError(missing_code)
        if reject_statuses and row.status in reject_statuses:
            raise ValueError("content_reference_unavailable")
        normalized.append(key)
    return normalized


async def _snapshot_references(
    db: AsyncSession,
    *,
    report_case_id: int,
    finding_keys: list[str],
    fragment_keys: list[str],
    evidence_keys: list[str],
    source_skill_run_id: Optional[int],
    fragment_type: str,
    require_confirmed: bool,
) -> dict[str, list[dict[str, Any]]]:
    normalized_findings = await _normalize_string_refs(
        db,
        model=FindingRevision,
        report_case_id=report_case_id,
        key_column=FindingRevision.finding_key,
        keys=finding_keys,
        missing_code="finding_reference_not_found",
        reject_statuses={"REJECTED", "SUPERSEDED"},
    )
    finding_rows = []
    for key in normalized_findings:
        row = await db.scalar(
            select(FindingRevision).where(
                FindingRevision.report_case_id == report_case_id,
                FindingRevision.finding_key == key,
                FindingRevision.is_current.is_(True),
            )
        )
        if require_confirmed and row.status != "CONFIRMED":
            raise ValueError("fragment_requires_confirmed_findings")
        finding_rows.append(
            {
                "finding_key": key,
                "revision_no": row.revision_no,
                "semantic_revision": row.semantic_revision,
            }
        )

    normalized_fragments = await _normalize_string_refs(
        db,
        model=ContentFragmentRevision,
        report_case_id=report_case_id,
        key_column=ContentFragmentRevision.fragment_key,
        keys=fragment_keys,
        missing_code="fragment_reference_not_found",
        reject_statuses={"STALE"},
    )
    fragment_rows = []
    for key in normalized_fragments:
        row = await db.scalar(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == report_case_id,
                ContentFragmentRevision.fragment_key == key,
                ContentFragmentRevision.is_current.is_(True),
            )
        )
        if require_confirmed and row.status != "CONFIRMED":
            raise ValueError("fragment_reference_not_confirmed")
        fragment_rows.append(
            {
                "fragment_key": key,
                "revision_no": row.revision_no,
                "semantic_revision": row.semantic_revision,
            }
        )

    normalized_evidence = await normalize_evidence_refs(
        db, report_case_id, evidence_keys
    )
    evidence_rows = []
    for key in normalized_evidence:
        row = await db.scalar(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case_id,
                CaseEvidenceItem.evidence_key == key,
            )
        )
        evidence_rows.append(
            {
                "evidence_key": key,
                "evidence_id": row.id,
                "source_type": row.source_type,
                "source_ref": row.source_ref,
            }
        )

    skill_rows: list[dict[str, Any]] = []
    if source_skill_run_id is not None:
        run = await db.get(SkillRun, source_skill_run_id)
        if run is None or run.report_case_id != report_case_id:
            raise ValueError("content_source_skill_run_invalid")
        skill_rows.append(
            {"skill_run_id": run.id, "skill_version_id": run.skill_version_id}
        )
    return {
        "findings": finding_rows,
        "fragments": fragment_rows,
        "evidence": evidence_rows,
        "skill_runs": skill_rows,
    }


async def create_content_fragment_revision(
    db: AsyncSession,
    *,
    report_case_id: int,
    fragment_key: str,
    content: str,
    fragment_type: str = "ANALYSIS",
    title: Optional[str] = None,
    status: Optional[str] = None,
    finding_refs: Optional[list[str]] = None,
    fragment_refs: Optional[list[str]] = None,
    evidence_refs: Optional[list[str]] = None,
    edit_kind: str = "SEMANTIC",
    owner_step_task_id: Optional[int] = None,
    source_skill_run_id: Optional[int] = None,
    source_narrative_plan_id: Optional[int] = None,
    created_by: Optional[int] = None,
) -> ContentFragmentRevision:
    report_case = await require_case(db, report_case_id)
    key = require_key(fragment_key, "fragment_key_invalid")
    content_value = content.strip() if isinstance(content, str) else ""
    if not content_value or len(content_value) > 30000:
        raise ValueError("fragment_content_invalid")
    if title is not None and len(title) > 240:
        raise ValueError("fragment_title_invalid")
    if fragment_type not in {"ANALYSIS", "REPORT"}:
        raise ValueError("fragment_type_invalid")
    if edit_kind not in {"SEMANTIC", "STYLE"}:
        raise ValueError("fragment_edit_kind_invalid")

    current = await db.scalar(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == report_case_id,
            ContentFragmentRevision.fragment_key == key,
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    if edit_kind == "STYLE" and current is None:
        raise ValueError("fragment_style_edit_requires_current")
    if current and edit_kind == "STYLE":
        if fragment_type != current.fragment_type:
            raise ValueError("fragment_style_edit_changed_semantics")
        if status is not None and status != current.status:
            raise ValueError("fragment_style_edit_changed_semantics")
        if (
            owner_step_task_id is not None
            and owner_step_task_id != current.owner_step_task_id
        ):
            raise ValueError("fragment_style_edit_changed_semantics")
        if (
            source_skill_run_id is not None
            and source_skill_run_id != current.source_skill_run_id
        ):
            raise ValueError("fragment_style_edit_changed_semantics")
        old_snapshot = current.source_snapshot or {}
        prior_findings = [item["finding_key"] for item in old_snapshot.get("findings", [])]
        prior_fragments = [item["fragment_key"] for item in old_snapshot.get("fragments", [])]
        prior_evidence = [item["evidence_key"] for item in old_snapshot.get("evidence", [])]
        for requested, prior in (
            (finding_refs, prior_findings),
            (fragment_refs, prior_fragments),
            (evidence_refs, prior_evidence),
        ):
            if requested is not None and set(requested) != set(prior):
                raise ValueError("fragment_style_edit_changed_semantics")
        source_skill_run_id = (
            source_skill_run_id
            if source_skill_run_id is not None
            else current.source_skill_run_id
        )
        finding_refs, fragment_refs, evidence_refs = (
            prior_findings,
            prior_fragments,
            prior_evidence,
        )
    else:
        if current:
            old_snapshot = current.source_snapshot or {}
            finding_refs = (
                finding_refs
                if finding_refs is not None
                else [item["finding_key"] for item in old_snapshot.get("findings", [])]
            )
            fragment_refs = (
                fragment_refs
                if fragment_refs is not None
                else [item["fragment_key"] for item in old_snapshot.get("fragments", [])]
            )
            evidence_refs = (
                evidence_refs
                if evidence_refs is not None
                else [item["evidence_key"] for item in old_snapshot.get("evidence", [])]
            )
            source_skill_run_id = (
                source_skill_run_id
                if source_skill_run_id is not None
                else current.source_skill_run_id
            )
        else:
            finding_refs = finding_refs if finding_refs is not None else []
            fragment_refs = fragment_refs if fragment_refs is not None else []
            evidence_refs = evidence_refs if evidence_refs is not None else []

    owner_step = (
        owner_step_task_id
        if owner_step_task_id is not None
        else (current.owner_step_task_id if current else None)
    )
    await validate_owner_refs(
        db,
        report_case=report_case,
        owner_step_task_id=owner_step,
        source_skill_run_id=source_skill_run_id,
    )
    effective_narrative_plan_id = source_narrative_plan_id
    if effective_narrative_plan_id is None and current and fragment_type == "REPORT":
        effective_narrative_plan_id = current.source_narrative_plan_id
    narrative_plan = (
        await db.get(NarrativePlan, effective_narrative_plan_id)
        if effective_narrative_plan_id is not None
        else None
    )
    if fragment_type == "REPORT" and edit_kind != "STYLE":
        if (
            narrative_plan is None
            or narrative_plan.report_case_id != report_case_id
            or narrative_plan.status != "CONFIRMED"
        ):
            raise ValueError("fragment_narrative_plan_invalid")
    elif narrative_plan is not None and (
        narrative_plan.report_case_id != report_case_id or fragment_type != "REPORT"
    ):
        raise ValueError("fragment_narrative_plan_invalid")
    if current and edit_kind == "STYLE":
        source_snapshot = current.source_snapshot or {}
    else:
        require_confirmed = fragment_type == "REPORT" or status == "CONFIRMED"
        source_snapshot = await _snapshot_references(
            db,
            report_case_id=report_case_id,
            finding_keys=finding_refs,
            fragment_keys=fragment_refs,
            evidence_keys=evidence_refs,
            source_skill_run_id=source_skill_run_id,
            fragment_type=fragment_type,
            require_confirmed=require_confirmed,
        )
        if narrative_plan is not None:
            source_snapshot["narrative_plan"] = {
                "id": narrative_plan.id,
                "version_no": narrative_plan.version_no,
                "selected_candidate_key": narrative_plan.selected_candidate_key,
            }
        await _ensure_acyclic_fragment_refs(
            db,
            report_case_id=report_case_id,
            fragment_key=key,
            fragment_refs=[row["fragment_key"] for row in source_snapshot["fragments"]],
        )
    next_status = status or (
        current.status if current and edit_kind == "STYLE" else "PROPOSED"
    )
    allowed_statuses = {"PROPOSED", "CONFIRMED"}
    if current and current.status == "STALE" and edit_kind == "STYLE":
        next_status = "STALE"
        allowed_statuses.add("STALE")
    if next_status not in allowed_statuses:
        raise ValueError("fragment_status_invalid")

    if current:
        current.is_current = False
        revision_no = current.revision_no + 1
        semantic_revision = current.semantic_revision + (1 if edit_kind == "SEMANTIC" else 0)
        content_revision = current.content_revision + 1
    else:
        revision_no = semantic_revision = content_revision = 1
    revision = ContentFragmentRevision(
        report_case_id=report_case_id,
        fragment_key=key,
        revision_no=revision_no,
        semantic_revision=semantic_revision,
        content_revision=content_revision,
        fragment_type=fragment_type,
        title=title if title is not None else (current.title if current else None),
        content=content_value,
        status=next_status,
        source_snapshot=source_snapshot,
        edit_kind=edit_kind,
        is_current=True,
        owner_step_task_id=owner_step,
        source_skill_run_id=source_skill_run_id,
        source_narrative_plan_id=(
            effective_narrative_plan_id
            if effective_narrative_plan_id is not None
            else (current.source_narrative_plan_id if current else None)
        ),
        stale_reason=(
            current.stale_reason
            if current and current.status == "STALE" and edit_kind == "STYLE"
            else None
        ),
        created_by=created_by,
        created_at=now(),
    )
    db.add(revision)
    await db.flush()
    if current and edit_kind == "SEMANTIC":
        await mark_dependents_stale(
            db,
            report_case_id=report_case_id,
            origin_kind="fragment",
            origin_key=key,
            reason=f"semantic_dependency_changed:fragment:{key}",
        )
    if (
        fragment_type == "ANALYSIS"
        and next_status == "CONFIRMED"
        and edit_kind == "SEMANTIC"
    ):
        await invalidate_narrative_for_source(
            db,
            report_case_id=report_case_id,
            source_kind="fragment",
            source_key=key,
            reason=f"SOURCE_CHANGED:fragment:{key}",
            force=current is None or current.status != "CONFIRMED",
        )
    return revision


async def _ensure_acyclic_fragment_refs(
    db: AsyncSession,
    *,
    report_case_id: int,
    fragment_key: str,
    fragment_refs: list[str],
) -> None:
    if fragment_key in fragment_refs:
        raise ValueError("fragment_dependency_cycle")
    rows = await db.scalars(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == report_case_id,
            ContentFragmentRevision.is_current.is_(True),
        )
    )
    dependencies = {
        row.fragment_key: [
            item.get("fragment_key")
            for item in (row.source_snapshot or {}).get("fragments", [])
            if isinstance(item, dict) and item.get("fragment_key")
        ]
        for row in rows
    }

    def reaches_target(start: str) -> bool:
        pending = [start]
        seen: set[str] = set()
        while pending:
            current_key = pending.pop()
            if current_key == fragment_key:
                return True
            if current_key in seen:
                continue
            seen.add(current_key)
            pending.extend(dependencies.get(current_key, []))
        return False

    if any(reaches_target(reference) for reference in fragment_refs):
        raise ValueError("fragment_dependency_cycle")
