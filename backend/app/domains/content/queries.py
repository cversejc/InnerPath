from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .common import require_case
from .models import CaseEvidenceItem, ContentFragmentRevision, FindingRevision


async def load_confirmed_case_semantics(
    db: AsyncSession, report_case_id: int
) -> dict[str, list[dict[str, Any]]]:
    await require_case(db, report_case_id)
    finding_rows = await db.scalars(
        select(FindingRevision)
        .where(
            FindingRevision.report_case_id == report_case_id,
            FindingRevision.is_current.is_(True),
            FindingRevision.status == "CONFIRMED",
        )
        .order_by(FindingRevision.finding_key)
    )
    fragment_rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == report_case_id,
            ContentFragmentRevision.is_current.is_(True),
            ContentFragmentRevision.status == "CONFIRMED",
        )
        .order_by(ContentFragmentRevision.fragment_key)
    )
    evidence_rows = await db.scalars(
        select(CaseEvidenceItem)
        .where(
            CaseEvidenceItem.report_case_id == report_case_id,
            CaseEvidenceItem.status == "ACTIVE",
        )
        .order_by(CaseEvidenceItem.evidence_key)
    )
    active_evidence = list(evidence_rows)
    active_evidence_keys = {row.evidence_key for row in active_evidence}
    confirmed_findings = [
        row
        for row in finding_rows
        if set(row.evidence_refs or []).issubset(active_evidence_keys)
    ]
    return {
        "findings": [
            {
                "finding_key": row.finding_key,
                "revision_no": row.revision_no,
                "semantic_revision": row.semantic_revision,
                "kind": row.kind,
                "semantic_role": row.semantic_role,
                "claim": row.claim,
                "confidence": row.confidence,
                "importance": row.importance,
                "reportability": row.reportability,
                "evidence_refs": row.evidence_refs,
                "structured_data": row.structured_data_json,
                "relation_refs": row.relation_refs or [],
            }
            for row in confirmed_findings
        ],
        "fragments": [
            {
                "fragment_key": row.fragment_key,
                "revision_no": row.revision_no,
                "semantic_revision": row.semantic_revision,
                "fragment_type": row.fragment_type,
                "title": row.title,
                "content": row.content,
                "source_snapshot": row.source_snapshot,
            }
            for row in fragment_rows
        ],
        "evidence": [
            {
                "evidence_key": row.evidence_key,
                "source_type": row.source_type,
                "source_ref": row.source_ref,
                "source_skill_run_id": row.source_skill_run_id,
                "value": row.value_json,
            }
            for row in active_evidence
        ],
    }


async def load_case_semantic_model(
    db: AsyncSession, report_case_id: int
) -> dict[str, Any]:
    """Build the writer's input from current, confirmed analysis assets only."""
    semantics = await load_confirmed_case_semantics(db, report_case_id)
    report_case = await require_case(db, report_case_id)
    reasoning = (report_case.application_snapshot or {}).get("reasoning_contract")
    findings = [
        item
        for item in semantics["findings"]
        if item["reportability"] != "INTERNAL_ONLY" or reasoning
    ]
    analysis_fragments = [
        item
        for item in semantics["fragments"]
        if item["fragment_type"] == "ANALYSIS"
    ]
    evidence_refs = {
        key
        for item in findings
        for key in item.get("evidence_refs", [])
    }
    if reasoning:
        for finding in findings:
            path = (finding.get("structured_data") or {}).get("reasoning_path") or {}
            if isinstance(path, dict):
                evidence_refs.update(path.get("evidence_refs") or [])
    for item in analysis_fragments:
        evidence_refs.update(
            row.get("evidence_key")
            for row in (item.get("source_snapshot") or {}).get("evidence", [])
            if isinstance(row, dict) and row.get("evidence_key")
        )
    evidence = [
        item for item in semantics["evidence"] if item["evidence_key"] in evidence_refs
    ]
    if not findings:
        raise ValueError("narrative_confirmed_findings_required")
    model = {
        "findings": findings,
        "analysis_fragments": analysis_fragments,
        "evidence": evidence,
    }
    contract = (report_case.application_snapshot or {}).get("framework_contract")
    if contract is not None:
        from .product_framework import validate_framework
        model["framework_contract"] = validate_framework(contract)
    if reasoning:
        from .reasoning_contract import validate_reasoning_contract
        validate_reasoning_contract(reasoning)
        model["reasoning_contract"] = reasoning
    return model
