from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.skills.models import SkillRun

from .models import ContentFragmentRevision, NarrativePlan


def references(snapshot: dict, kind: str, key: str) -> bool:
    key_field = {
        "finding": "finding_key",
        "fragment": "fragment_key",
        "evidence": "evidence_key",
    }[kind]
    collection = {"finding": "findings", "fragment": "fragments", "evidence": "evidence"}[kind]
    return any(
        item.get(key_field) == key
        for item in (snapshot or {}).get(collection, [])
        if isinstance(item, dict)
    )


async def mark_dependents_stale(
    db: AsyncSession,
    *,
    report_case_id: int,
    origin_kind: str,
    origin_key: str,
    reason: str,
) -> int:
    rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == report_case_id,
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    current_fragments = list(rows.all())
    pending = [(origin_kind, origin_key, reason)]
    visited: set[tuple[str, str]] = set()
    stale_ids: set[int] = set()
    while pending:
        kind, key, cause = pending.pop(0)
        if (kind, key) in visited:
            continue
        visited.add((kind, key))
        for fragment in current_fragments:
            if fragment.id in stale_ids or fragment.status == "STALE":
                continue
            if not references(fragment.source_snapshot or {}, kind, key):
                continue
            fragment.status = "STALE"
            fragment.stale_reason = cause
            stale_ids.add(fragment.id)
            pending.append(
                (
                    "fragment",
                    fragment.fragment_key,
                    f"semantic_dependency_changed:fragment:{fragment.fragment_key}",
                )
            )
    await db.flush()
    should_invalidate_plan = origin_kind in {"finding", "evidence"} or (
        origin_kind == "fragment"
        and any(
            row.fragment_key == origin_key and row.fragment_type == "ANALYSIS"
            for row in current_fragments
        )
    )
    if should_invalidate_plan:
        await invalidate_narrative_for_source(
            db,
            report_case_id=report_case_id,
            source_kind=origin_kind,
            source_key=origin_key,
        )
    return len(stale_ids)


async def invalidate_narrative_for_source(
    db,
    *,
    report_case_id: int,
    source_kind: str,
    source_key: str,
) -> bool:
    plan = await db.scalar(
        select(NarrativePlan)
        .where(
            NarrativePlan.report_case_id == report_case_id,
            NarrativePlan.is_current.is_(True),
            NarrativePlan.status == "CONFIRMED",
        )
        .with_for_update()
    )
    if plan is None:
        return False

    plan_json = plan.plan_json or {}
    narrative_refs = plan_json.get("narrative_source_refs") or {}
    narrative_findings = set(
        value
        for value in (narrative_refs.get("finding_refs") or [])
        if isinstance(value, str)
    )
    narrative_findings.update(
        value
        for value in (plan_json.get("must_include_findings") or [])
        if isinstance(value, str)
    )
    if isinstance(plan_json.get("self_direction"), str):
        narrative_findings.add(plan_json["self_direction"])
    for block in plan_json.get("priority_blocks") or []:
        if isinstance(block, dict):
            narrative_findings.update(
                value
                for value in (block.get("finding_refs") or [])
                if isinstance(value, str)
            )
    if not narrative_findings:
        run = await db.get(SkillRun, plan.selected_skill_run_id)
        candidates = (run.output_parsed or {}).get("candidates", []) if run else []
        candidate = next(
            (
                item
                for item in candidates
                if isinstance(item, dict)
                and item.get("candidate_key") == plan.selected_candidate_key
            ),
            None,
        )
        narrative_findings = set(
            value
            for value in ((candidate or {}).get("supporting_findings") or [])
            if isinstance(value, str)
        )

    # A changed source only invalidates the mainline when it supported the
    # selected narrative. Direct and transitive report dependencies have
    # already been marked stale by mark_dependents_stale.
    if source_kind != "finding" or source_key not in narrative_findings:
        return False
    plan.status = "STALE"
    await db.flush()
    return True
