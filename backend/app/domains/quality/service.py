from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content.models import ContentFragmentRevision
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase

from .models import QAIssue
from .programmatic import collect_programmatic_issues


def _now() -> datetime:
    return datetime.utcnow()


async def run_programmatic_qa(
    db: AsyncSession, report_case: ReportCase, *, actor_id: int
) -> tuple[list[QAIssue], str, dict[str, Any]]:
    issues, fingerprint, snapshot = await collect_programmatic_issues(db, report_case)
    prior = await db.scalars(
        select(QAIssue).where(
            QAIssue.report_case_id == report_case.id,
            QAIssue.source_type == "PROGRAMMATIC",
            QAIssue.status == "OPEN",
        )
    )
    for row in prior:
        row.status = "RESOLVED"
        row.resolution = "已由后续程序化 QA 结果替代。"
        row.resolved_by = actor_id
        row.resolved_at = _now()
    saved = []
    for issue in issues:
        row = QAIssue(
            report_case_id=report_case.id,
            source_type="PROGRAMMATIC",
            source_ref_id=None,
            issue_type=issue["issue_type"],
            severity=issue["severity"],
            status="OPEN",
            target_fragment_key=issue["target_fragment_key"],
            target_fragment_revision_id=issue["target_fragment_revision_id"],
            message=issue["message"],
            evidence_json={**issue["evidence_json"], "qa_fingerprint": fingerprint},
            suggestion=issue["suggestion"],
            created_at=_now(),
        )
        db.add(row)
        saved.append(row)
    await db.flush()
    return saved, fingerprint, snapshot


async def replace_validator_issues(db: AsyncSession, run: SkillRun) -> list[QAIssue]:
    if run.report_case_id is None:
        raise ValueError("validator_case_required")
    latest = await latest_validator_run(db, run.report_case_id)
    if latest is not None and latest.id != run.id:
        return []
    prior = await db.scalars(
        select(QAIssue).where(
            QAIssue.report_case_id == run.report_case_id,
            QAIssue.source_type == "VALIDATOR",
            QAIssue.status == "OPEN",
        )
    )
    for row in prior:
        row.status = "RESOLVED"
        row.resolution = f"已由 Validator 运行 #{run.id} 替代。"
        row.resolved_by = None
        row.resolved_at = _now()

    current_fragments = {
        row.fragment_key: row
        for row in await db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == run.report_case_id,
                ContentFragmentRevision.is_current.is_(True),
            )
        )
    }
    saved = []
    for issue in (run.output_parsed or {}).get("issues", []):
        if not isinstance(issue, dict):
            continue
        severity = issue.get("severity")
        if severity == "WARN":
            severity = "MAJOR"
        elif severity == "SUGGESTION":
            severity = "MINOR"
        if severity not in {"BLOCK", "MAJOR", "MINOR"}:
            continue
        fragment_key = issue.get("target_fragment_key")
        fragment = current_fragments.get(fragment_key)
        row = QAIssue(
            report_case_id=run.report_case_id,
            source_type="VALIDATOR",
            source_ref_id=run.id,
            issue_type=str(issue.get("issue_type") or "SEMANTIC_REVIEW"),
            severity=severity,
            status="OPEN",
            target_fragment_key=fragment_key if fragment else None,
            target_fragment_revision_id=fragment.id if fragment else None,
            message=str(issue.get("message") or "语义审核发现需要复核的问题。"),
            evidence_json={
                "evidence": issue.get("evidence"),
                "qa_fingerprint": (run.context_snapshot or {}).get("qa_fingerprint"),
            },
            suggestion=str(issue.get("suggestion") or "请咨询师复核该问题。"),
            created_at=_now(),
        )
        db.add(row)
        saved.append(row)
    await db.flush()
    return saved


async def resolve_qa_issue(
    db: AsyncSession,
    *,
    report_case_id: int,
    issue_id: int,
    status: str,
    resolution: str,
    actor_id: int,
) -> QAIssue:
    issue = await db.scalar(
        select(QAIssue)
        .where(QAIssue.id == issue_id, QAIssue.report_case_id == report_case_id)
        .with_for_update()
    )
    if issue is None:
        raise ValueError("qa_issue_not_found")
    if issue.status != "OPEN":
        raise ValueError("qa_issue_already_closed")
    if status not in {"RESOLVED", "ACCEPTED", "DISMISSED"}:
        raise ValueError("qa_issue_resolution_invalid")
    if issue.severity == "BLOCK" and status != "RESOLVED":
        raise ValueError("qa_block_cannot_be_accepted")
    issue.status = status
    issue.resolution = resolution.strip()
    issue.resolved_by = actor_id
    issue.resolved_at = _now()
    await db.flush()
    return issue


async def get_case_qa_issues(db: AsyncSession, report_case_id: int) -> list[QAIssue]:
    return list(
        await db.scalars(
            select(QAIssue)
            .where(QAIssue.report_case_id == report_case_id)
            .order_by(QAIssue.created_at.desc(), QAIssue.id.desc())
        )
    )


async def latest_validator_run(db: AsyncSession, report_case_id: int) -> SkillRun | None:
    return await db.scalar(
        select(SkillRun)
        .where(
            SkillRun.report_case_id == report_case_id,
            SkillRun.target_type == "REPORT_QA",
        )
        .order_by(SkillRun.created_at.desc(), SkillRun.id.desc())
        .limit(1)
    )
