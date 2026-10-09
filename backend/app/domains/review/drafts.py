"""Editing saves drafts even when coverage declarations need a later recheck."""
from copy import deepcopy
from difflib import SequenceMatcher
from sqlalchemy import select

from app.core.time import utc_now_naive
from app.domains.content.models import ContentFragmentRevision, FindingRevision, NarrativePlan, CaseEvidenceItem
from app.domains.content.evidence import normalize_evidence_refs
from app.domains.content.dependencies import mark_dependents_stale, invalidate_narrative_for_source
from app.domains.content.fragments import _snapshot_references


def rebind_coverage_quotes(snapshot, before, after):
    """Track existing quoted ranges through edits; never invent a coverage claim."""
    source = deepcopy(snapshot)
    records = [source.get("framework_coverage"), source.get("structured_analysis")] + list(source.get("requirement_coverage") or [])
    operations = SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
    def boundary(index, end=False):
        for kind, a, b, c, d in operations:
            if a <= index <= b:
                if kind == "equal":
                    return c + index - a
                if index == b:
                    return d
                return d if end else c
        return len(after)
    for record in records:
        if not isinstance(record, dict):
            continue
        quote = record.get("quote")
        if isinstance(quote, str) and quote not in after and quote in before:
            start = before.index(quote)
            record["quote"] = after[boundary(start):boundary(start + len(quote), True)]
    return source


async def rebind_coverage_quotes_from_history(db, row, snapshot, after):
    coverage = rebind_coverage_quotes(snapshot, row.content, after)
    records = [coverage.get("framework_coverage"), coverage.get("structured_analysis")] + list(coverage.get("requirement_coverage") or [])
    if not any(
        isinstance(record, dict)
        and isinstance(record.get("quote"), str)
        and record["quote"] not in after
        for record in records
    ):
        return coverage
    history = list(await db.scalars(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == row.report_case_id,
        ContentFragmentRevision.fragment_key == row.fragment_key,
        ContentFragmentRevision.revision_no < row.revision_no,
    ).order_by(ContentFragmentRevision.revision_no.desc())))
    for previous in history:
        coverage = rebind_coverage_quotes(coverage, previous.content, after)
    return coverage


async def edit_draft(db, case_id, step, change, actor_id, *, evidence_remap=None):
    key = change.get("key")
    model, key_column = (ContentFragmentRevision, ContentFragmentRevision.fragment_key) if change.get("kind", "fragment") == "fragment" else (FindingRevision, FindingRevision.finding_key)
    row = await db.scalar(select(model).where(model.report_case_id == case_id, key_column == key, model.is_current.is_(True)).with_for_update())
    if not row or (row.owner_step_task_id != step.id and not (isinstance(row, ContentFragmentRevision) and row.fragment_type == "REPORT" and step.step_key == "S6")):
        raise ValueError("node_edit_target_invalid")
    text = change.get("content")
    title = change.get("title") if model == ContentFragmentRevision else None
    maximum = 30000 if model == ContentFragmentRevision else 5000
    if not isinstance(text, str) or not text.strip() or len(text) > maximum:
        raise ValueError("node_edit_content_invalid")
    if title is not None and (not isinstance(title, str) or len(title) > 240):
        raise ValueError("node_edit_title_invalid")
    field = "content" if model == ContentFragmentRevision else "claim"
    structured = change.get("structured_data") if model == FindingRevision else None
    source_snapshot = None
    if model == ContentFragmentRevision:
        source_snapshot = await rebind_coverage_quotes_from_history(db, row, row.source_snapshot or {}, text)
    snapshot_changed = source_snapshot is not None and source_snapshot != (row.source_snapshot or {})
    if (getattr(row, field) == text and (title is None or title == getattr(row, "title", None))
            and structured is None and not change.get("reject") and not change.get("refresh_sources")
            and change.get("evidence_refs") is None and not snapshot_changed):
        return row
    values = {c.name: deepcopy(getattr(row, c.name)) for c in model.__table__.columns if c.name != "id"}
    values.update({field: text, "revision_no": row.revision_no + 1, "semantic_revision": row.semantic_revision + 1,
                   "content_revision": row.content_revision + 1, "status": "PROPOSED", "created_by": actor_id if actor_id is not None else row.created_by,
                   "created_at": utc_now_naive(), "is_current": True, "edit_kind": "SEMANTIC"})
    if model == ContentFragmentRevision:
        if title is not None:
            values["title"] = title
        values["source_snapshot"] = source_snapshot
        values["stale_reason"] = None
        if change.get("refresh_sources"):
            old = deepcopy(values["source_snapshot"])
            for ref in old.get("evidence", []):
                ref["evidence_key"] = (evidence_remap or {}).get(ref["evidence_key"], ref["evidence_key"])
            refs = await _snapshot_references(db, report_case_id=case_id, finding_keys=[r["finding_key"] for r in old.get("findings", [])], fragment_keys=[r["fragment_key"] for r in old.get("fragments", [])], evidence_keys=[r["evidence_key"] for r in old.get("evidence", [])], source_skill_run_id=row.source_skill_run_id, fragment_type=row.fragment_type, require_confirmed=False)
            values["source_snapshot"] = {**deepcopy(old), **refs}
        if change.get("coverage_snapshot") is not None:
            values["source_snapshot"] = {**values["source_snapshot"], **change["coverage_snapshot"]}
    else:
        if change.get("evidence_refs") is not None:
            values["evidence_refs"] = await normalize_evidence_refs(db, report_case_id=case_id, keys=change["evidence_refs"])
        if structured is not None:
            if not isinstance(structured, dict):
                raise ValueError("node_structured_data_invalid")
            values["structured_data_json"] = structured
        if change.get("reject"):
            values["status"] = "REJECTED"
    row.is_current = False
    await db.flush()
    edited = model(**values)
    db.add(edited)
    await db.flush()
    origin = "fragment" if model == ContentFragmentRevision else "finding"
    await mark_dependents_stale(db, report_case_id=case_id, origin_kind=origin, origin_key=key, reason=f"semantic_dependency_changed:{origin}:{key}")
    if step.step_key not in {"S5", "S6"}:
        await invalidate_narrative_for_source(db, report_case_id=case_id, source_kind=origin, source_key=key)
    return edited


async def refresh_review_sources(db, case_id, step):
    evidence = list(await db.scalars(select(CaseEvidenceItem).where(CaseEvidenceItem.report_case_id == case_id)))
    active = [e for e in evidence if e.status == "ACTIVE" and isinstance(e.value_json, dict) and e.value_json.get("birth_time") and e.value_json.get("calculation_version") == "mingli-v2"]
    foundation = max(active, key=lambda e: (e.created_at, e.id), default=None)
    remap = {e.evidence_key: foundation.evidence_key for e in evidence if foundation and e.status == "RETRACTED" and isinstance(e.value_json, dict) and e.value_json.get("calculation_version") == "mingli-v2"}
    findings = list(await db.scalars(select(FindingRevision).where(FindingRevision.report_case_id == case_id, FindingRevision.is_current.is_(True), FindingRevision.owner_step_task_id == step.id, FindingRevision.status.not_in(["REJECTED", "SUPERSEDED"]))))
    for finding in findings:
        if set(finding.evidence_refs or []).intersection(remap):
            await edit_draft(db, case_id, step, {"kind":"finding", "key":finding.finding_key, "content":finding.claim, "evidence_refs":[remap.get(k, k) for k in finding.evidence_refs]}, None)
    owner = ContentFragmentRevision.fragment_type == "REPORT" if step.step_key == "S6" else ContentFragmentRevision.owner_step_task_id == step.id
    rows = list(await db.scalars(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case_id, ContentFragmentRevision.is_current.is_(True), owner)))
    # Explicit collective recheck rebinds available changed inputs into a pending
    # version which still requires independent consistency review and a signature.
    pending = list(rows)
    while pending:
        progressed = False
        for row in list(pending):
            try:
                async with db.begin_nested():
                    old = row.source_snapshot or {}
                    refs = await _snapshot_references(db, report_case_id=case_id, finding_keys=[r["finding_key"] for r in old.get("findings", [])], fragment_keys=[r["fragment_key"] for r in old.get("fragments", [])], evidence_keys=[remap.get(r["evidence_key"], r["evidence_key"]) for r in old.get("evidence", [])], source_skill_run_id=row.source_skill_run_id, fragment_type=row.fragment_type, require_confirmed=False)
                    coverage = await rebind_coverage_quotes_from_history(db, row, old, row.content)
                    coverage_fields = {k:coverage[k] for k in ("framework_coverage", "structured_analysis", "requirement_coverage") if k in coverage}
                    if row.status == "STALE" or any(old.get(k) != v for k, v in refs.items()) or coverage != old:
                        await edit_draft(db, case_id, step, {"key":row.fragment_key, "content":row.content, "refresh_sources":True, "coverage_snapshot":coverage_fields}, None, evidence_remap=remap)
                pending.remove(row)
                progressed = True
            except ValueError:
                pass  # Missing/retracted inputs stay blocking until repaired.
        if not progressed:
            break


async def edit_narrative_draft(db, case_id, step, changes, actor_id):
    """Version the mainline with the complete body preserved for collective review."""
    if step.step_key != "S5" or set(changes) - {"core_theme", "narrative_arc", "fragment_order"}:
        raise ValueError("node_narrative_edit_invalid")
    plan = await db.scalar(select(NarrativePlan).where(NarrativePlan.report_case_id == case_id, NarrativePlan.is_current.is_(True)).with_for_update())
    if not plan:
        raise ValueError("narrative_plan_not_found")
    data = deepcopy(plan.plan_json)
    theme = changes.get("core_theme", data.get("core_theme"))
    arc = changes.get("narrative_arc", data.get("narrative_arc"))
    if not isinstance(theme, str) or not theme.strip() or len(theme) > 1000 or not isinstance(arc, list) or len(arc) > 30:
        raise ValueError("node_narrative_edit_invalid")
    data.update(core_theme=theme.strip(), narrative_arc=arc)
    allocations = data.get("content_plan", {}).get("fragments", [])
    if "fragment_order" in changes:
        order = changes["fragment_order"]
        if not isinstance(order, list) or len(order) != len(allocations) or set(order) != {a["fragment_key"] for a in allocations}:
            raise ValueError("node_narrative_order_invalid")
        allocations.sort(key=lambda a: order.index(a["fragment_key"]))
        for n, allocation in enumerate(allocations, 1):
            allocation["sequence_no"] = n
    if data == plan.plan_json:
        return plan
    values = {c.name: deepcopy(getattr(plan, c.name)) for c in NarrativePlan.__table__.columns if c.name != "id"}
    values.update(version_no=plan.version_no + 1, plan_json=data, status="PROPOSED", created_by=actor_id, created_at=utc_now_naive(), confirmed_by=None, confirmed_at=None)
    plan.is_current = False
    plan.status = "SUPERSEDED"
    await db.flush()
    edited = NarrativePlan(**values)
    db.add(edited)
    await db.flush()
    rows = list(await db.scalars(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case_id, ContentFragmentRevision.fragment_type == "REPORT", ContentFragmentRevision.is_current.is_(True))))
    for row in rows:
        row.is_current = False
        values = {c.name: deepcopy(getattr(row, c.name)) for c in ContentFragmentRevision.__table__.columns if c.name != "id"}
        source = deepcopy(row.source_snapshot or {})
        source["narrative_plan"] = {"id":edited.id, "version_no":edited.version_no, "selected_candidate_key":edited.selected_candidate_key}
        values.update(is_current=True, revision_no=row.revision_no + 1, content_revision=row.content_revision + 1, source_narrative_plan_id=edited.id, source_snapshot=source, status="PROPOSED" if row.status != "STALE" else "STALE", created_at=utc_now_naive(), edit_kind="STYLE")
        db.add(ContentFragmentRevision(**values))
    await db.flush()
    return edited
