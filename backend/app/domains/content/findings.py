from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .common import now, require_case, require_key, same_json, validate_owner_refs
from .dependencies import mark_dependents_stale
from .evidence import normalize_evidence_refs
from .models import FindingRevision


FINDING_STATUSES = {"PROPOSED", "CONFIRMED", "REJECTED"}


async def _normalize_relations(
    db: AsyncSession,
    *,
    report_case_id: int,
    finding_key: str,
    relations: list[Any],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in relations:
        if isinstance(item, str):
            target, relation = item, "RELATED"
        elif isinstance(item, dict):
            target, relation = item.get("finding_key"), item.get("relation", "RELATED")
        else:
            raise ValueError("finding_relation_invalid")
        target = require_key(target, "finding_relation_invalid")
        relation = require_key(relation, "finding_relation_invalid", 48).upper()
        if target == finding_key:
            raise ValueError("finding_relation_self_reference")
        row = await db.scalar(
            select(FindingRevision).where(
                FindingRevision.report_case_id == report_case_id,
                FindingRevision.finding_key == target,
                FindingRevision.is_current.is_(True),
            )
        )
        if row is None:
            raise ValueError("finding_relation_target_not_found")
        if row.status == "REJECTED":
            raise ValueError("finding_relation_target_unavailable")
        pair = (target, relation)
        if pair not in seen:
            normalized.append({"finding_key": target, "relation": relation})
            seen.add(pair)
    return normalized


async def current_finding(
    db: AsyncSession, report_case_id: int, finding_key: str
) -> Optional[FindingRevision]:
    return await db.scalar(
        select(FindingRevision)
        .where(
            FindingRevision.report_case_id == report_case_id,
            FindingRevision.finding_key == finding_key,
            FindingRevision.is_current.is_(True),
        )
        .with_for_update()
    )


async def create_finding_revision(
    db: AsyncSession,
    *,
    report_case_id: int,
    finding_key: str,
    claim: str,
    kind: Optional[str] = None,
    semantic_role: Optional[str] = None,
    confidence: Optional[str] = None,
    importance: Optional[str] = None,
    reportability: Optional[str] = None,
    status: Optional[str] = None,
    evidence_refs: Optional[list[str]] = None,
    relation_refs: Optional[list[Any]] = None,
    structured_data: Optional[dict[str, Any]] = None,
    edit_kind: str = "SEMANTIC",
    owner_step_task_id: Optional[int] = None,
    source_skill_run_id: Optional[int] = None,
    created_by: Optional[int] = None,
) -> FindingRevision:
    report_case = await require_case(db, report_case_id)
    key = require_key(finding_key, "finding_key_invalid")
    claim_value = claim.strip() if isinstance(claim, str) else ""
    if not claim_value or len(claim_value) > 5000:
        raise ValueError("finding_claim_invalid")
    if edit_kind not in {"SEMANTIC", "STYLE"}:
        raise ValueError("finding_edit_kind_invalid")

    current = await current_finding(db, report_case_id, key)
    if edit_kind == "STYLE" and current is None:
        raise ValueError("finding_style_edit_requires_current")

    values = {
        "kind": kind or (current.kind if current else "FINDING"),
        "semantic_role": semantic_role or (current.semantic_role if current else None),
        "confidence": confidence or (current.confidence if current else "MEDIUM"),
        "importance": importance or (current.importance if current else "MEDIUM"),
        "reportability": reportability or (current.reportability if current else "OPTIONAL"),
        "status": status or (current.status if current else "PROPOSED"),
        "evidence_refs": evidence_refs if evidence_refs is not None else (current.evidence_refs if current else []),
        "relation_refs": relation_refs if relation_refs is not None else (current.relation_refs if current else []),
        "structured_data_json": structured_data if structured_data is not None else (current.structured_data_json if current else {}),
    }
    if values["semantic_role"] is None:
        raise ValueError("finding_semantic_role_required")
    if len(values["semantic_role"]) > 48:
        raise ValueError("finding_semantic_role_invalid")
    if values["kind"] not in {"FINDING", "SIGNAL"}:
        raise ValueError("finding_kind_invalid")
    if values["confidence"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("finding_confidence_invalid")
    if values["importance"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ValueError("finding_importance_invalid")
    if values["reportability"] not in {
        "INTERNAL_ONLY",
        "OPTIONAL",
        "RECOMMENDED",
        "MUST_INCLUDE",
    }:
        raise ValueError("finding_reportability_invalid")
    if values["status"] not in FINDING_STATUSES:
        raise ValueError("finding_status_invalid")

    if edit_kind == "STYLE" and current:
        for field in (
            "kind",
            "semantic_role",
            "confidence",
            "importance",
            "reportability",
            "status",
        ):
            if values[field] != getattr(current, field):
                raise ValueError("finding_style_edit_changed_semantics")
        for field in ("evidence_refs", "relation_refs", "structured_data_json"):
            if not same_json(values[field], getattr(current, field)):
                raise ValueError("finding_style_edit_changed_semantics")

    normalized_evidence = await normalize_evidence_refs(
        db, report_case_id, values["evidence_refs"]
    )
    normalized_relations = await _normalize_relations(
        db,
        report_case_id=report_case_id,
        finding_key=key,
        relations=values["relation_refs"],
    )
    owner_step = owner_step_task_id if owner_step_task_id is not None else (current.owner_step_task_id if current else None)
    source_run = source_skill_run_id if source_skill_run_id is not None else (current.source_skill_run_id if current else None)
    await validate_owner_refs(
        db,
        report_case=report_case,
        owner_step_task_id=owner_step,
        source_skill_run_id=source_run,
    )

    if current:
        current.is_current = False
        current.status = "SUPERSEDED"
        revision_no = current.revision_no + 1
        semantic_revision = current.semantic_revision + (1 if edit_kind == "SEMANTIC" else 0)
        content_revision = current.content_revision + 1
    else:
        revision_no = semantic_revision = content_revision = 1
    revision = FindingRevision(
        report_case_id=report_case_id,
        finding_key=key,
        revision_no=revision_no,
        semantic_revision=semantic_revision,
        content_revision=content_revision,
        kind=values["kind"],
        semantic_role=values["semantic_role"],
        claim=claim_value,
        confidence=values["confidence"],
        importance=values["importance"],
        reportability=values["reportability"],
        status=values["status"],
        evidence_refs=normalized_evidence,
        relation_refs=normalized_relations,
        structured_data_json=values["structured_data_json"],
        edit_kind=edit_kind,
        is_current=True,
        owner_step_task_id=owner_step,
        source_skill_run_id=source_run,
        created_by=created_by,
        created_at=now(),
    )
    db.add(revision)
    await db.flush()
    if current and edit_kind == "SEMANTIC":
        await mark_dependents_stale(
            db,
            report_case_id=report_case_id,
            origin_kind="finding",
            origin_key=key,
            reason=f"semantic_dependency_changed:finding:{key}",
        )
    return revision


async def set_finding_status(
    db: AsyncSession,
    *,
    report_case_id: int,
    finding_key: str,
    status: str,
    created_by: Optional[int] = None,
) -> FindingRevision:
    if status not in FINDING_STATUSES:
        raise ValueError("finding_status_invalid")
    current = await current_finding(db, report_case_id, finding_key)
    if current is None:
        raise ValueError("finding_not_found")
    if current.status == status:
        return current
    return await create_finding_revision(
        db,
        report_case_id=report_case_id,
        finding_key=finding_key,
        claim=current.claim,
        kind=current.kind,
        semantic_role=current.semantic_role,
        confidence=current.confidence,
        importance=current.importance,
        reportability=current.reportability,
        status=status,
        evidence_refs=current.evidence_refs,
        relation_refs=current.relation_refs,
        structured_data=current.structured_data_json,
        edit_kind="SEMANTIC",
        owner_step_task_id=current.owner_step_task_id,
        source_skill_run_id=current.source_skill_run_id,
        created_by=created_by,
    )
