from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ContentFragmentRevision


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
    return len(stale_ids)
