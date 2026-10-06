import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .common import now, require_case, require_key, same_json
from .dependencies import mark_dependents_stale
from .models import CaseEvidenceItem, FindingRevision


EVIDENCE_SOURCE_TYPES = {
    "USER_PROVIDED",
    "SYSTEM_CALCULATED",
    "CONSULTANT_CORRECTED",
    "EXTERNAL_REFERENCE",
}


def _application_source_values(snapshot: dict[str, Any]) -> list[tuple[str, Any]]:
    source = snapshot
    request_payload = source.get("request_payload")
    if isinstance(request_payload, dict):
        source = request_payload
    nested = source.get("application_snapshot")
    if isinstance(nested, dict):
        source = {**nested, **source}

    allowed_roots = {
        "profile",
        "context",
        "selected_topics",
        "additional_info",
        "calendar_goal",
        "start_date",
    }
    values: list[tuple[str, Any]] = []

    def walk(value: Any, path: str) -> None:
        if value is None or value == "" or value == [] or value == {}:
            return
        if isinstance(value, dict):
            for child_key, child_value in sorted(value.items(), key=lambda item: str(item[0])):
                walk(child_value, f"{path}.{child_key}" if path else str(child_key))
            return
        normalized_path = re.sub(r"[^A-Za-z0-9_.-]+", "_", path).strip("._")
        if normalized_path:
            values.append((normalized_path, value))

    for root in sorted(allowed_roots):
        if root in source:
            walk(source[root], root)
    return values


async def create_evidence_item(
    db: AsyncSession,
    *,
    report_case_id: int,
    evidence_key: str,
    source_type: str,
    source_ref: str,
    value: Any,
    source_skill_run_id: Optional[int] = None,
    created_by: Optional[int] = None,
) -> CaseEvidenceItem:
    await require_case(db, report_case_id)
    key = require_key(evidence_key, "evidence_key_invalid", 240)
    if source_type not in EVIDENCE_SOURCE_TYPES:
        raise ValueError("evidence_source_type_invalid")
    if not source_ref or len(source_ref) > 500:
        raise ValueError("evidence_source_ref_invalid")
    if source_skill_run_id is not None:
        from app.domains.skills.models import SkillRun

        source_run = await db.get(SkillRun, source_skill_run_id)
        if source_run is None or source_run.report_case_id != report_case_id:
            raise ValueError("content_source_skill_run_invalid")

    existing = await db.scalar(
        select(CaseEvidenceItem).where(
            CaseEvidenceItem.report_case_id == report_case_id,
            CaseEvidenceItem.evidence_key == key,
        )
    )
    if existing:
        same_source = (
            existing.source_type == source_type
            and existing.source_ref == source_ref
            and existing.source_skill_run_id == source_skill_run_id
        )
        if not same_source or not same_json(existing.value_json, value):
            raise ValueError("evidence_key_immutable")
        if existing.status != "ACTIVE":
            raise ValueError("evidence_key_retracted")
        return existing

    evidence = CaseEvidenceItem(
        report_case_id=report_case_id,
        evidence_key=key,
        source_type=source_type,
        source_ref=source_ref,
        value_json=value,
        status="ACTIVE",
        source_skill_run_id=source_skill_run_id,
        created_by=created_by,
        created_at=now(),
    )
    db.add(evidence)
    await db.flush()
    return evidence


async def sync_application_evidence(
    db: AsyncSession,
    *,
    report_case_id: int,
    application_snapshot: dict[str, Any],
) -> list[CaseEvidenceItem]:
    """Project only explicit user input; calculated and AI output are never inferred here."""
    result = []
    for source_path, value in _application_source_values(application_snapshot):
        result.append(
            await create_evidence_item(
                db,
                report_case_id=report_case_id,
                evidence_key=f"input.{source_path}",
                source_type="USER_PROVIDED",
                source_ref=f"application_snapshot.{source_path}",
                value=value,
            )
        )
    return result


async def normalize_evidence_refs(
    db: AsyncSession, report_case_id: int, keys: list[str]
) -> list[str]:
    normalized = []
    for item in keys:
        key = require_key(item, "content_reference_invalid", 240)
        if key in normalized:
            continue
        evidence = await db.scalar(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case_id,
                CaseEvidenceItem.evidence_key == key,
            )
        )
        if evidence is None:
            raise ValueError("case_evidence_not_found")
        if evidence.status != "ACTIVE":
            raise ValueError("case_evidence_unavailable")
        normalized.append(key)
    return normalized


async def retract_case_evidence(
    db: AsyncSession,
    *,
    report_case_id: int,
    evidence_key: str,
    reason: str,
) -> CaseEvidenceItem:
    evidence = await db.scalar(
        select(CaseEvidenceItem)
        .where(
            CaseEvidenceItem.report_case_id == report_case_id,
            CaseEvidenceItem.evidence_key == evidence_key,
        )
        .with_for_update()
    )
    if evidence is None:
        raise ValueError("case_evidence_not_found")
    if evidence.status == "RETRACTED":
        return evidence
    evidence.status = "RETRACTED"
    evidence.status_reason = reason[:1000] if reason else "source_retracted"
    finding_rows = await db.scalars(
        select(FindingRevision).where(
            FindingRevision.report_case_id == report_case_id,
            FindingRevision.is_current.is_(True),
        )
    )
    affected_findings = [
        row.finding_key for row in finding_rows if evidence_key in (row.evidence_refs or [])
    ]
    await mark_dependents_stale(
        db,
        report_case_id=report_case_id,
        origin_kind="evidence",
        origin_key=evidence_key,
        reason=f"evidence_retracted:{evidence_key}",
    )
    for finding_key in affected_findings:
        await mark_dependents_stale(
            db,
            report_case_id=report_case_id,
            origin_kind="finding",
            origin_key=finding_key,
            reason=f"evidence_retracted:{evidence_key}",
        )
    await db.flush()
    return evidence
