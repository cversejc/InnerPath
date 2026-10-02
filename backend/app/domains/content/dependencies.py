from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            reason=f"SOURCE_CHANGED:{origin_kind}:{origin_key}",
        )
    return len(stale_ids)


async def invalidate_narrative_for_source(
    db,
    *,
    report_case_id: int,
    source_kind: str,
    source_key: str,
    reason: str,
    force: bool = False,
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
    collection, key_field = {
        "finding": ("findings", "finding_key"),
        "fragment": ("analysis_fragments", "fragment_key"),
        "evidence": ("evidence", "evidence_key"),
    }[source_kind]
    is_source = any(
        isinstance(item, dict) and item.get(key_field) == source_key
        for item in (plan.source_snapshot or {}).get(collection, [])
    )
    if not is_source and not force:
        return False
    plan.status = "STALE"
    await mark_report_fragments_stale_for_plan(
        db, plan.id, reason=f"SOURCE_CHANGED:{source_kind}:{source_key}"
    )
    return True


async def mark_report_fragments_stale_for_plan(
    db, narrative_plan_id: int, *, reason: str
) -> int:
    rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.source_narrative_plan_id == narrative_plan_id,
            ContentFragmentRevision.fragment_type == "REPORT",
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    count = 0
    for row in rows:
        if row.status != "STALE":
            row.status = "STALE"
            count += 1
        row.stale_reason = reason
    await db.flush()
    return count
