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
