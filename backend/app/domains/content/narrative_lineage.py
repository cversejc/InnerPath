import json
from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ContentFragmentRevision, NarrativePlan


def _plan_source_refs(
    plan_json: dict[str, Any], semantic_model: dict[str, Any]
) -> tuple[set[str], set[str], set[str]]:
    finding_refs: set[str] = set()
    analysis_refs: set[str] = set()
    evidence_refs: set[str] = set()
    content_plan = plan_json.get("content_plan") or {}
    allocations = content_plan.get("fragments") or []
    if isinstance(allocations, list):
        for allocation in allocations:
            if not isinstance(allocation, dict):
                continue
            for field in ("finding_refs", "required_finding_refs", "action_refs"):
                values = allocation.get(field) or []
                if isinstance(values, list):
                    finding_refs.update(value for value in values if isinstance(value, str))
            values = allocation.get("analysis_refs") or []
            if isinstance(values, list):
                analysis_refs.update(value for value in values if isinstance(value, str))
            values = allocation.get("evidence_refs") or []
            if isinstance(values, list):
                evidence_refs.update(value for value in values if isinstance(value, str))

    narrative_refs = plan_json.get("narrative_source_refs") or {}
    values = narrative_refs.get("finding_refs") or []
    if isinstance(values, list):
        finding_refs.update(value for value in values if isinstance(value, str))
    values = narrative_refs.get("analysis_refs") or []
    if isinstance(values, list):
        analysis_refs.update(value for value in values if isinstance(value, str))
    finding_refs.update(
        value
        for value in (plan_json.get("must_include_findings") or [])
        if isinstance(value, str)
    )
    if isinstance(plan_json.get("self_direction"), str):
        finding_refs.add(plan_json["self_direction"])
    for block in plan_json.get("priority_blocks") or []:
        if isinstance(block, dict):
            finding_refs.update(
                value
                for value in (block.get("finding_refs") or [])
                if isinstance(value, str)
            )

    analysis_by_key = {
        item.get("fragment_key"): item
        for item in semantic_model.get("analysis_fragments", [])
        if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
    }
    pending = list(analysis_refs)
    visited: set[str] = set()
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key)
        source = analysis_by_key.get(key, {}).get("source_snapshot") or {}
        finding_refs.update(
            item.get("finding_key")
            for item in source.get("findings", [])
            if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
        )
        evidence_refs.update(
            item.get("evidence_key")
            for item in source.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("evidence_key"), str)
        )
        children = [
            item.get("fragment_key")
            for item in source.get("fragments", [])
            if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
        ]
        pending.extend(children)
        analysis_refs.update(children)

    for finding in semantic_model.get("findings", []):
        if isinstance(finding, dict) and finding.get("finding_key") in finding_refs:
            evidence_refs.update(
                value
                for value in (finding.get("evidence_refs") or [])
                if isinstance(value, str)
            )
    return finding_refs, analysis_refs, evidence_refs


def _filter_semantic_snapshot(
    snapshot: dict[str, Any], refs: tuple[set[str], set[str], set[str]]
) -> dict[str, list[dict[str, Any]]]:
    finding_refs, analysis_refs, evidence_refs = refs
    return {
        "findings": [
            item
            for item in (snapshot or {}).get("findings", [])
            if isinstance(item, dict) and item.get("finding_key") in finding_refs
        ],
        "analysis_fragments": [
            item
            for item in (snapshot or {}).get("analysis_fragments", [])
            if isinstance(item, dict) and item.get("fragment_key") in analysis_refs
        ],
        "evidence": [
            item
            for item in (snapshot or {}).get("evidence", [])
            if isinstance(item, dict) and item.get("evidence_key") in evidence_refs
        ],
    }


def narrative_semantic_sources_match(
    plan: NarrativePlan, semantic_model: dict[str, Any]
) -> bool:
    plan_json = plan.plan_json or {}
    refs = _plan_source_refs(
        {
            key: plan_json.get(key)
            for key in (
                "narrative_source_refs",
                "must_include_findings",
                "self_direction",
                "priority_blocks",
            )
        },
        semantic_model,
    )
    return _filter_semantic_snapshot(plan.source_snapshot or {}, refs) == _filter_semantic_snapshot(
        semantic_source_snapshot(semantic_model), refs
    )


def semantic_source_snapshot_for_allocation(
    allocation: dict[str, Any], semantic_model: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    refs = _plan_source_refs({"content_plan": {"fragments": [allocation]}}, semantic_model)
    return _filter_semantic_snapshot(semantic_source_snapshot(semantic_model), refs)


def allocation_semantic_sources_match(
    snapshot: dict[str, Any], allocation: dict[str, Any], semantic_model: dict[str, Any]
) -> bool:
    refs = _plan_source_refs({"content_plan": {"fragments": [allocation]}}, semantic_model)
    return _filter_semantic_snapshot(snapshot or {}, refs) == _filter_semantic_snapshot(
        semantic_source_snapshot(semantic_model), refs
    )


def semantic_source_snapshot(
    semantic_model: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    return {
        "findings": [
            {
                "finding_key": item["finding_key"],
                "revision_no": item["revision_no"],
                "semantic_revision": item["semantic_revision"],
            }
            for item in semantic_model["findings"]
        ],
        "analysis_fragments": [
            {
                "fragment_key": item["fragment_key"],
                "revision_no": item["revision_no"],
                "semantic_revision": item["semantic_revision"],
            }
            for item in semantic_model["analysis_fragments"]
        ],
        "evidence": [
            {"evidence_key": item["evidence_key"]}
            for item in semantic_model["evidence"]
        ],
    }


def _allocation_signature(allocation: dict[str, Any] | None) -> str | None:
    if allocation is None:
        return None
    return json.dumps(allocation, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _narrative_signature(plan_json: dict[str, Any]) -> str:
    fields = (
        "selected_candidate",
        "core_theme",
        "reader_profile",
        "narrative_arc",
        "chapter_strategy",
        "rationale",
        "deemphasized_findings",
    )
    return json.dumps(
        {key: plan_json.get(key) for key in fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


async def carry_forward_unchanged_report_fragments(
    db: AsyncSession,
    *,
    previous: NarrativePlan,
    current: NarrativePlan,
    actor_id: int,
) -> None:
    old_json = previous.plan_json or {}
    new_json = current.plan_json or {}
    old_allocations = {
        item.get("fragment_key"): item
        for item in ((old_json.get("content_plan") or {}).get("fragments") or [])
        if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
    }
    new_allocations = {
        item.get("fragment_key"): item
        for item in ((new_json.get("content_plan") or {}).get("fragments") or [])
        if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
    }
    narrative_changed = _narrative_signature(old_json) != _narrative_signature(new_json)
    changed_keys = {
        key
        for key in set(old_allocations) | set(new_allocations)
        if _allocation_signature(old_allocations.get(key))
        != _allocation_signature(new_allocations.get(key))
    }
    changed_sequences = [
        allocation.get("sequence_no")
        for key in changed_keys
        for allocation in (old_allocations.get(key), new_allocations.get(key))
        if isinstance(allocation, dict)
        and isinstance(allocation.get("sequence_no"), int)
    ]
    earliest_changed_sequence = min(changed_sequences, default=None)
    rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == previous.report_case_id,
            ContentFragmentRevision.source_narrative_plan_id == previous.id,
            ContentFragmentRevision.fragment_type == "REPORT",
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    for row in rows:
        can_carry = (
            not narrative_changed
            and row.status != "STALE"
            and _allocation_signature(old_allocations.get(row.fragment_key))
            == _allocation_signature(new_allocations.get(row.fragment_key))
            and row.fragment_key in new_allocations
            and (
                earliest_changed_sequence is None
                or (old_allocations[row.fragment_key].get("sequence_no") or 0)
                < earliest_changed_sequence
            )
        )
        if not can_carry:
            if row.status != "STALE":
                row.status = "STALE"
            row.stale_reason = "NARRATIVE_CHANGED"
            continue

        row.is_current = False
        snapshot = deepcopy(row.source_snapshot or {})
        snapshot["narrative_plan"] = {
            "id": current.id,
            "version_no": current.version_no,
            "selected_candidate_key": current.selected_candidate_key,
        }
        db.add(
            ContentFragmentRevision(
                report_case_id=row.report_case_id,
                fragment_key=row.fragment_key,
                revision_no=row.revision_no + 1,
                semantic_revision=row.semantic_revision,
                content_revision=row.content_revision + 1,
                fragment_type=row.fragment_type,
                title=row.title,
                content=row.content,
                status=row.status,
                source_snapshot=snapshot,
                edit_kind="STYLE",
                is_current=True,
                owner_step_task_id=row.owner_step_task_id,
                source_skill_run_id=row.source_skill_run_id,
                source_narrative_plan_id=current.id,
                stale_reason=None,
                created_by=actor_id,
                created_at=datetime.utcnow(),
            )
        )
    await db.flush()
