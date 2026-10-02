import hashlib
import json
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.content.narrative import semantic_source_snapshot
from app.domains.content.queries import load_case_semantic_model
from app.domains.workflow.models import ReportCase, WorkflowInstance, WorkflowVersion


REQUIRED_SECTIONS = {
    "identity": ("report.identity", "你是谁"),
    "challenge": ("report.challenge", "卡在哪"),
    "direction": ("report.direction", "往哪去"),
}
BLOCKED_PHRASES = (
    "注定发财",
    "必然离婚",
    "保证治愈",
    "一定会",
    "必定会",
    "永远不会",
    "百分之百",
    "诊断为",
    "患有抑郁症",
    "患有焦虑症",
    "人格障碍",
    "精神分裂",
    "精神疾病",
)


def _issue(
    issue_type: str,
    severity: str,
    message: str,
    *,
    fragment: ContentFragmentRevision | None = None,
    evidence: dict[str, Any] | None = None,
    suggestion: str | None = None,
) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "target_fragment_key": fragment.fragment_key if fragment else None,
        "target_fragment_revision_id": fragment.id if fragment else None,
        "message": message,
        "evidence_json": evidence or {},
        "suggestion": suggestion,
    }


async def collect_programmatic_issues(
    db: AsyncSession, report_case: ReportCase
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    current_fragments = list(
        await db.scalars(
            select(ContentFragmentRevision)
            .where(
                ContentFragmentRevision.report_case_id == report_case.id,
                ContentFragmentRevision.is_current.is_(True),
                ContentFragmentRevision.fragment_type == "REPORT",
            )
            .order_by(ContentFragmentRevision.fragment_key)
        )
    )
    current_findings = list(
        await db.scalars(
            select(FindingRevision).where(
                FindingRevision.report_case_id == report_case.id,
                FindingRevision.is_current.is_(True),
            )
        )
    )
    current_analysis = list(
        await db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == report_case.id,
                ContentFragmentRevision.is_current.is_(True),
                ContentFragmentRevision.fragment_type == "ANALYSIS",
            )
        )
    )
    active_evidence = list(
        await db.scalars(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case.id,
                CaseEvidenceItem.status == "ACTIVE",
            )
        )
    )
    current_plan = await db.scalar(
        select(NarrativePlan).where(
            NarrativePlan.report_case_id == report_case.id,
            NarrativePlan.is_current.is_(True),
        )
    )
    issues: list[dict[str, Any]] = []
    by_finding = {row.finding_key: row for row in current_findings}
    by_analysis = {row.fragment_key: row for row in current_analysis}
    by_evidence = {row.evidence_key: row for row in active_evidence}
    referenced_findings: Counter[str] = Counter()

    if current_plan is None or current_plan.status != "CONFIRMED":
        issues.append(
            _issue(
                "NARRATIVE_PLAN_UNCONFIRMED",
                "BLOCK",
                "当前报告没有已确认的 NarrativePlan。",
                suggestion="回到叙事方案步骤，重新生成并确认方案。",
            )
        )
    try:
        semantic_model = await load_case_semantic_model(db, report_case.id)
    except ValueError:
        semantic_model = None
        issues.append(
            _issue(
                "CONFIRMED_SEMANTICS_MISSING",
                "BLOCK",
                "Case 没有可用于报告的已确认 Finding。",
                suggestion="补充并确认有 Evidence 来源的专业判断。",
            )
        )
    if current_plan is not None and current_plan.status == "CONFIRMED" and semantic_model:
        if current_plan.source_snapshot != semantic_source_snapshot(semantic_model):
            issues.append(
                _issue(
                    "NARRATIVE_PLAN_STALE",
                    "BLOCK",
                    "NarrativePlan 的语义来源已变化。",
                    suggestion="基于当前已确认语义重新生成并确认 NarrativePlan。",
                )
            )

    for section, (prefix, label) in REQUIRED_SECTIONS.items():
        section_fragments = [
            row for row in current_fragments if row.fragment_key == prefix or row.fragment_key.startswith(prefix + ".")
        ]
        if not any(row.status == "CONFIRMED" and row.content.strip() for row in section_fragments):
            issues.append(
                _issue(
                    "MISSING_REQUIRED_SECTION",
                    "BLOCK",
                    f"报告缺少已确认的“{label}”章节片段。",
                    evidence={"required_section": section, "fragment_prefix": prefix},
                    suggestion="补齐该章节的报告片段并确认。",
                )
            )

    if not current_fragments:
        issues.append(
            _issue(
                "REPORT_FRAGMENTS_MISSING",
                "BLOCK",
                "当前 Case 没有报告片段。",
                suggestion="基于确认后的 NarrativePlan 编写报告片段。",
            )
        )

    for fragment in current_fragments:
        if fragment.status == "STALE":
            issues.append(
                _issue(
                    "STALE_FRAGMENT",
                    "BLOCK",
                    f"片段 {fragment.fragment_key} 的语义来源已变化。",
                    fragment=fragment,
                    evidence={"stale_reason": fragment.stale_reason},
                    suggestion="重新生成或修订该片段并确认。",
                )
            )
            continue
        if fragment.status != "CONFIRMED":
            issues.append(
                _issue(
                    "UNCONFIRMED_FRAGMENT",
                    "BLOCK",
                    f"片段 {fragment.fragment_key} 尚未确认。",
                    fragment=fragment,
                    suggestion="完成人工审阅并确认片段。",
                )
            )
        if not fragment.title or not fragment.content.strip() or len(fragment.content) > 30000:
            issues.append(
                _issue(
                    "FRAGMENT_SCHEMA_INVALID",
                    "BLOCK",
                    f"片段 {fragment.fragment_key} 的标题或正文不符合报告结构要求。",
                    fragment=fragment,
                    suggestion="补全标题和正文，正文不超过 30000 个字符。",
                )
            )

        source = fragment.source_snapshot or {}
        finding_refs = source.get("findings") or []
        analysis_refs = source.get("fragments") or []
        evidence_refs = source.get("evidence") or []
        if not finding_refs and not analysis_refs:
            issues.append(
                _issue(
                    "SOURCE_MAP_MISSING",
                    "BLOCK",
                    f"片段 {fragment.fragment_key} 没有 Finding 或分析片段来源。",
                    fragment=fragment,
                    suggestion="为片段关联已确认的 Finding 或 Analysis Fragment。",
                )
            )
        for ref in finding_refs:
            key = ref.get("finding_key") if isinstance(ref, dict) else None
            finding = by_finding.get(key)
            if finding is None or finding.status != "CONFIRMED":
                issues.append(
                    _issue(
                        "FINDING_SOURCE_UNAVAILABLE",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 引用了不存在或未确认的 Finding。",
                        fragment=fragment,
                        evidence={"finding_key": key},
                        suggestion="移除无效来源，或先完成 Finding 审核。",
                    )
                )
                continue
            if (
                ref.get("revision_no") != finding.revision_no
                or ref.get("semantic_revision") != finding.semantic_revision
            ):
                issues.append(
                    _issue(
                        "FINDING_SOURCE_STALE",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 使用的 Finding 版本已过期。",
                        fragment=fragment,
                        evidence={"finding_key": key, "source_revision": ref.get("revision_no"), "current_revision": finding.revision_no},
                        suggestion="依据最新 Finding 重新审核该片段。",
                    )
                )
            referenced_findings[key] += 1
        for ref in analysis_refs:
            key = ref.get("fragment_key") if isinstance(ref, dict) else None
            analysis = by_analysis.get(key)
            if analysis is None or analysis.status != "CONFIRMED":
                issues.append(
                    _issue(
                        "ANALYSIS_SOURCE_UNAVAILABLE",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 引用了不存在或未确认的 Analysis Fragment。",
                        fragment=fragment,
                        evidence={"fragment_key": key},
                        suggestion="先确认分析片段，或移除该来源。",
                    )
                )
                continue
            if ref.get("revision_no") != analysis.revision_no or ref.get("semantic_revision") != analysis.semantic_revision:
                issues.append(
                    _issue(
                        "ANALYSIS_SOURCE_STALE",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 使用的分析片段版本已过期。",
                        fragment=fragment,
                        evidence={"fragment_key": key},
                        suggestion="依据最新分析片段重新审核该片段。",
                    )
                )
        for ref in evidence_refs:
            key = ref.get("evidence_key") if isinstance(ref, dict) else None
            if key not in by_evidence:
                issues.append(
                    _issue(
                        "EVIDENCE_SOURCE_UNAVAILABLE",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 引用了无效或已撤回的 Evidence。",
                        fragment=fragment,
                        evidence={"evidence_key": key},
                        suggestion="更新来源映射，移除已撤回的 Evidence。",
                    )
                )
        text = f"{fragment.title or ''}\n{fragment.content}".casefold()
        for phrase in BLOCKED_PHRASES:
            if phrase.casefold() in text:
                issues.append(
                    _issue(
                        "BLOCKED_EXPRESSION",
                        "BLOCK",
                        f"片段 {fragment.fragment_key} 包含需要人工修订的高风险表达。",
                        fragment=fragment,
                        evidence={"matched_phrase": phrase},
                        suggestion="改为有边界、非诊断且不作确定性预测的表达。",
                    )
                )

    for finding in current_findings:
        if (
            finding.status == "CONFIRMED"
            and finding.importance == "CRITICAL"
            and finding.reportability != "INTERNAL_ONLY"
            and finding.finding_key not in referenced_findings
        ):
            issues.append(
                _issue(
                    "CRITICAL_FINDING_UNCOVERED",
                    "BLOCK",
                    f"关键判断 {finding.finding_key} 尚未被报告片段覆盖。",
                    evidence={"finding_key": finding.finding_key, "revision_no": finding.revision_no},
                    suggestion="纳入有来源映射的报告片段，或修正该 Finding 的重要度/可报告性。",
                )
            )
    for finding_key, count in referenced_findings.items():
        if count > 3:
            issues.append(
                _issue(
                    "FINDING_OVER_REPEATED",
                    "MINOR",
                    f"Finding {finding_key} 在 {count} 个报告片段中重复出现。",
                    evidence={"finding_key": finding_key, "fragment_count": count},
                    suggestion="检查是否存在重复表达，保留必要的跨章节呼应。",
                )
            )

    semantic_model = semantic_model or {"findings": [], "analysis_fragments": [], "evidence": []}
    snapshot = {
        "application_snapshot": report_case.application_snapshot or {},
        "semantic_model": semantic_model,
        "narrative_plan": (
            {
                "id": current_plan.id,
                "version_no": current_plan.version_no,
                "plan_json": current_plan.plan_json,
                "source_snapshot": current_plan.source_snapshot,
                "status": current_plan.status,
            }
            if current_plan
            else None
        ),
        "fragments": [
            {
                "id": row.id,
                "fragment_key": row.fragment_key,
                "revision_no": row.revision_no,
                "semantic_revision": row.semantic_revision,
                "content_revision": row.content_revision,
                "status": row.status,
                "title": row.title,
                "content": row.content,
                "source_snapshot": row.source_snapshot,
            }
            for row in current_fragments
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return issues, fingerprint, snapshot
