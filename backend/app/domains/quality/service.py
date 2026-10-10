from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content.models import ContentFragmentRevision
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase

from .models import QAIssue
from .programmatic import collect_programmatic_issues
from app.core.time import utc_now_naive


_MIN_RECOVERED_EVIDENCE_LENGTH = 4


def _now() -> datetime:
    return utc_now_naive()


def _longest_contiguous_source_quote(evidence: str, source: str) -> str | None:
    """Return the longest exact quote from evidence that appears in source."""
    if not evidence or not source:
        return None
    previous = [0] * (len(source) + 1)
    best_start = 0
    best_length = 0
    for character in evidence:
        current = [0] * (len(source) + 1)
        for source_index, source_character in enumerate(source, start=1):
            if character != source_character:
                continue
            length = previous[source_index - 1] + 1
            current[source_index] = length
            if length > best_length:
                best_start = source_index - length
                best_length = length
        previous = current
    if best_length < _MIN_RECOVERED_EVIDENCE_LENGTH:
        return None
    return source[best_start : best_start + best_length]


def _programmatic_issue_identity(row: QAIssue) -> tuple:
    """Identify a programmatic finding across re-checks of the same content."""
    return (
        row.issue_type,
        row.target_fragment_key,
        row.message,
        row.target_fragment_revision_id,
    )


async def run_programmatic_qa(
    db: AsyncSession, report_case: ReportCase, *, actor_id: int
) -> tuple[list[QAIssue], str, dict[str, Any]]:
    issues, fingerprint, snapshot = await collect_programmatic_issues(db, report_case)
    prior = list(
        await db.scalars(
            select(QAIssue).where(
                QAIssue.report_case_id == report_case.id,
                QAIssue.source_type == "PROGRAMMATIC",
                QAIssue.status == "OPEN",
            )
        )
    )
    # A re-check of unchanged fragments must not reopen a finding the reviewer
    # already retained or dismissed; carry that decision to the new row.
    decided = list(
        await db.scalars(
            select(QAIssue)
            .where(
                QAIssue.report_case_id == report_case.id,
                QAIssue.source_type == "PROGRAMMATIC",
                QAIssue.status.in_({"ACCEPTED", "DISMISSED"}),
            )
            .order_by(QAIssue.id.desc())
        )
    )
    carried = {}
    for row in decided:
        carried.setdefault(_programmatic_issue_identity(row), row)
    for row in prior:
        row.status = "RESOLVED"
        row.resolution = "已由后续程序化 QA 结果替代。"
        row.resolved_by = actor_id
        row.resolved_at = _now()
    saved = []
    for issue in issues:
        identity = (
            issue["issue_type"],
            issue["target_fragment_key"],
            issue["message"],
            issue["target_fragment_revision_id"],
        )
        decision = carried.get(identity)
        row = QAIssue(
            report_case_id=report_case.id,
            source_type="PROGRAMMATIC",
            source_ref_id=None,
            issue_type=issue["issue_type"],
            severity=issue["severity"],
            status=decision.status if decision is not None else "OPEN",
            target_fragment_key=issue["target_fragment_key"],
            target_fragment_revision_id=issue["target_fragment_revision_id"],
            message=issue["message"],
            evidence_json={
                **issue["evidence_json"],
                "qa_fingerprint": fingerprint,
                **(
                    {"carried_from_issue_id": decision.id}
                    if decision is not None
                    else {}
                ),
            },
            suggestion=issue["suggestion"],
            resolution=decision.resolution if decision is not None else None,
            resolved_by=decision.resolved_by if decision is not None else None,
            resolved_at=decision.resolved_at if decision is not None else None,
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
    prior = list(
        await db.scalars(
            select(QAIssue).where(
                QAIssue.report_case_id == run.report_case_id,
                QAIssue.source_type == "VALIDATOR",
                QAIssue.status == "OPEN",
            )
        )
    )
    # Re-runs of an unchanged fragment must not reopen a finding the reviewer
    # already retained or dismissed on that very revision.
    decided = list(
        await db.scalars(
            select(QAIssue)
            .where(
                QAIssue.report_case_id == run.report_case_id,
                QAIssue.source_type == "VALIDATOR",
                QAIssue.status.in_({"ACCEPTED", "DISMISSED"}),
            )
            .order_by(QAIssue.id.desc())
        )
    )
    carried = {}
    for row in decided:
        carried.setdefault(
            (
                row.target_fragment_key,
                row.issue_type,
                row.severity,
                row.target_fragment_revision_id,
            ),
            row,
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
    case = await db.get(ReportCase, run.report_case_id)
    seen = set()
    unverified_seen = set()
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
        evidence = issue.get("evidence")
        evidence_original = None
        if case and case.review_policy_version == "six-node-review-v1":
            issue_type = str(issue.get("issue_type") or "SEMANTIC_REVIEW")
            if issue_type != "quality_score_below_threshold":
                source_quote = (
                    evidence
                    if (
                        fragment
                        and isinstance(evidence, str)
                        and evidence in fragment.content
                    )
                    else None
                )
                if source_quote is None and fragment and isinstance(evidence, str):
                    source_quote = _longest_contiguous_source_quote(
                        evidence, fragment.content
                    )
                    if source_quote is not None:
                        evidence_original = evidence
                if source_quote is None:
                    identity = (fragment_key, issue_type, evidence)
                    if identity not in unverified_seen:
                        unverified_seen.add(identity)
                        row = QAIssue(
                            report_case_id=run.report_case_id,
                            source_type="PROGRAMMATIC",
                            source_ref_id=run.id,
                            issue_type="VALIDATOR_EVIDENCE_UNVERIFIED",
                            severity="MINOR",
                            status="OPEN",
                            target_fragment_key=(
                                fragment_key if fragment else None
                            ),
                            target_fragment_revision_id=(
                                fragment.id if fragment else None
                            ),
                            message=(
                                "检查意见的引用无法在目标正文中定位，"
                                "已省略原意见，请人工复核。"
                            ),
                            evidence_json={
                                "evidence": evidence,
                                "validator_issue_type": issue_type,
                                "validator_run_id": run.id,
                                "qa_fingerprint": (
                                    run.context_snapshot or {}
                                ).get("qa_fingerprint"),
                            },
                            suggestion="请重新运行检查或人工通读目标片段核对。",
                            created_at=_now(),
                        )
                        db.add(row)
                        saved.append(row)
                    continue
                evidence = source_quote
            identity = (fragment_key, issue.get("issue_type"), severity)
            if identity in seen:
                continue
            seen.add(identity)
        issue_type = str(issue.get("issue_type") or "SEMANTIC_REVIEW")
        decision = carried.get(
            (
                fragment_key,
                issue_type,
                severity,
                fragment.id if fragment else None,
            )
        )
        row = QAIssue(
            report_case_id=run.report_case_id,
            source_type="VALIDATOR",
            source_ref_id=run.id,
            issue_type=issue_type,
            severity=severity,
            status=decision.status if decision is not None else "OPEN",
            target_fragment_key=fragment_key if fragment else None,
            target_fragment_revision_id=fragment.id if fragment else None,
            message=str(issue.get("message") or "语义审核发现需要复核的问题。"),
            evidence_json={
                "evidence": evidence,
                "qa_fingerprint": (run.context_snapshot or {}).get("qa_fingerprint"),
                **(
                    {"evidence_original": evidence_original}
                    if evidence_original is not None
                    else {}
                ),
                **(
                    {"carried_from_issue_id": decision.id}
                    if decision is not None
                    else {}
                ),
            },
            suggestion=str(issue.get("suggestion") or "请咨询师复核该问题。"),
            resolution=decision.resolution if decision is not None else None,
            resolved_by=decision.resolved_by if decision is not None else None,
            resolved_at=decision.resolved_at if decision is not None else None,
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


def group_quality_issues(issues) -> list[dict]:
    """同类同严重度的检查问题分组：整体处理一次，逐条保留处理记录。"""
    groups = {}
    order = []
    for issue in issues or []:
        if issue.status != "OPEN" or issue.severity == "BLOCK":
            continue
        key = f"{issue.source_type}:{issue.issue_type}:{issue.severity}"
        group = groups.get(key)
        if group is None:
            group = {
                "group_key": key,
                "source_type": issue.source_type,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "issue_ids": [],
                "target_keys": [],
            }
            groups[key] = group
            order.append(key)
        group["issue_ids"].append(issue.id)
        if issue.target_fragment_key and issue.target_fragment_key not in group["target_keys"]:
            group["target_keys"].append(issue.target_fragment_key)
    return [
        {**groups[key], "count": len(groups[key]["issue_ids"])}
        for key in order
        if len(groups[key]["issue_ids"]) > 1
    ]


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
