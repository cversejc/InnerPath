from app.domains.workflow.authorization import validate_step_actor
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from app.core.time import api_datetime, utc_now_iso
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.application.skill_runtime import (
    authorize_report_case,
    queue_allocated_fragment_skill_run,
    queue_case_report_coherence_skill_run,
)
from app.domains.content.models import ContentFragmentRevision, NarrativePlan
from app.domains.content.narrative import (
    get_current_narrative_plan,
)
from app.domains.content.narrative_lineage import narrative_semantic_sources_match
from app.domains.content.queries import load_case_semantic_model
from app.domains.content.report_content_plan import validate_report_content_plan
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase, StepTask
from app.models.user import User


_REPORT_ANALYSIS_STEP_KEYS = ("S1", "S2", "S3", "S4")


def _generation_state(plan: NarrativePlan) -> dict[str, Any]:
    return deepcopy((plan.plan_json or {}).get("generation") or {})


def _content_plan(plan: NarrativePlan) -> dict[str, Any]:
    value = (plan.plan_json or {}).get("content_plan")
    return value if isinstance(value, dict) else {}


def _plan_fragment(content_plan: dict[str, Any], sequence_no: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in content_plan.get("fragments", [])
            if isinstance(item, dict) and item.get("sequence_no") == sequence_no
        ),
        None,
    )


def _fragment_snapshot(
    plan: NarrativePlan, rows: list[ContentFragmentRevision]
) -> list[dict[str, Any]]:
    content_plan = _content_plan(plan)
    order = {
        item.get("fragment_key"): item.get("sequence_no")
        for item in content_plan.get("fragments", [])
        if isinstance(item, dict) and isinstance(item.get("sequence_no"), int)
    }
    selected = [row for row in rows if row.status != "STALE"]
    selected.sort(key=lambda row: (order.get(row.fragment_key, 10_000), row.fragment_key))
    return [
        {
            "fragment_key": row.fragment_key,
            "revision_no": row.revision_no,
            "semantic_revision": row.semantic_revision,
            "content_revision": row.content_revision,
            "title": row.title,
            "content": row.content,
            "source_snapshot": row.source_snapshot or {},
        }
        for row in selected
    ]


def _chapter_snapshot(
    content_plan: dict[str, Any],
    snapshot: list[dict[str, Any]],
    chapter_key: str,
) -> list[dict[str, Any]]:
    chapter_fragment_keys = {
        item.get("fragment_key")
        for item in content_plan.get("fragments", [])
        if isinstance(item, dict) and item.get("chapter") == chapter_key
    }
    return [item for item in snapshot if item.get("fragment_key") in chapter_fragment_keys]


def _coherence_fingerprint(
    plan: NarrativePlan, fragment_snapshot: list[dict[str, Any]]
) -> str:
    payload = {
        "narrative_plan_id": plan.id,
        "source_snapshot": plan.source_snapshot,
        "content_plan": _content_plan(plan),
        "fragments": fragment_snapshot,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def current_report_coherence_context(
    db: AsyncSession, case_id: int
) -> dict[str, Any] | None:
    plan = await get_current_narrative_plan(db, case_id)
    if plan is None:
        return None

    generation = _generation_state(plan)
    fragments = _fragment_snapshot(
        plan, await _load_authored_fragments(db, case_id, plan)
    )
    content_plan = _content_plan(plan)
    chapter_checks = {}
    for chapter_key, check in (generation.get("chapter_checks") or {}).items():
        if not isinstance(check, dict):
            continue
        current_fingerprint = _coherence_fingerprint(
            plan,
            _chapter_snapshot(content_plan, fragments, chapter_key),
        )
        if check.get("fingerprint") == current_fingerprint:
            chapter_checks[chapter_key] = deepcopy(check)

    coherence = deepcopy(generation.get("coherence") or {})
    coherence_is_current = (
        coherence.get("status") in {"PASSED", "BLOCKED"}
        and coherence.get("fingerprint")
        == _coherence_fingerprint(plan, fragments)
    )
    if coherence.get("status") in {"PASSED", "BLOCKED"} and not coherence_is_current:
        coherence["status"] = "STALE"
        coherence["issues"] = []

    current_issues = []
    for issue in generation.get("issues") or []:
        scope = issue.get("scope")
        if scope == "CHAPTER" and issue.get("chapter_key") not in chapter_checks:
            continue
        if scope == "REPORT" and not coherence_is_current:
            continue
        current_issues.append(deepcopy(issue))

    return {
        "chapter_checks": chapter_checks,
        "coherence": coherence,
        "issues": current_issues,
    }


async def _load_authored_fragments(
    db: AsyncSession, case_id: int, plan: NarrativePlan
) -> list[ContentFragmentRevision]:
    rows = list(
        await db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == case_id,
                ContentFragmentRevision.fragment_type == "REPORT",
                ContentFragmentRevision.is_current.is_(True),
            )
        )
    )
    return [row for row in rows if row.status != "STALE"]


def _require_allocated_fragments(
    plan: NarrativePlan,
    rows: list[ContentFragmentRevision],
    *,
    chapter_key: str | None = None,
) -> None:
    by_key = {row.fragment_key: row for row in rows}
    missing = [
        allocation.get("fragment_key")
        for allocation in _content_plan(plan).get("fragments", [])
        if allocation.get("required")
        and (chapter_key is None or allocation.get("chapter") == chapter_key)
        and (
            (row := by_key.get(allocation.get("fragment_key"))) is None
            or not row.content.strip()
            or row.source_narrative_plan_id != plan.id
        )
    ]
    if missing:
        raise ValueError("report_authoring_not_ready")


async def _queue_report_coherence_run(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    step: StepTask,
    plan: NarrativePlan,
    semantic_model: dict[str, Any],
    content_plan: dict[str, Any],
    generation: dict[str, Any],
    request_key: str,
    scope: str = "REPORT",
    chapter_key: str | None = None,
    next_sequence_no: int | None = None,
) -> SkillRun:
    rows = await _load_authored_fragments(db, report_case.id, plan)
    _require_allocated_fragments(
        plan, rows, chapter_key=chapter_key if scope == "CHAPTER" else None
    )
    snapshot = _fragment_snapshot(plan, rows)
    if scope == "CHAPTER":
        if not chapter_key:
            raise ValueError("report_coherence_chapter_required")
        snapshot = _chapter_snapshot(content_plan, snapshot, chapter_key)
        if not snapshot:
            raise ValueError("report_coherence_chapter_empty")
    fingerprint = _coherence_fingerprint(plan, snapshot)
    coherence_attempt = int(generation.get("coherence_attempt") or 0) + 1
    chapter_checks = generation.setdefault("chapter_checks", {})
    chapter_attempt = (
        int((chapter_checks.get(chapter_key) or {}).get("attempt") or 0) + 1
        if scope == "CHAPTER" and chapter_key
        else None
    )
    run, _created = await queue_case_report_coherence_skill_run(
        db,
        report_case=report_case,
        step=step,
        plan=plan,
        semantic_model=semantic_model,
        content_plan=content_plan,
        fragment_snapshot=snapshot,
        coherence_fingerprint=fingerprint,
        idempotency_key=(
            f"report-{scope.lower()}-coherence:{report_case.id}:{plan.id}:"
            f"{chapter_key or 'full'}:{generation.get('attempt', 0)}:{coherence_attempt}"
        ),
        generation_metadata={
            "kind": f"{scope}_COHERENCE",
            "plan_id": plan.id,
            "attempt": generation.get("attempt", 0),
            "coherence_attempt": coherence_attempt,
            "chapter_attempt": chapter_attempt,
            "chapter_key": chapter_key,
            "next_sequence_no": next_sequence_no,
            "request_key": request_key,
        },
        scope=scope,
        chapter_key=chapter_key,
    )
    generation.update(
        {
            "status": (
                "CHAPTER_COHERENCE_CHECK" if scope == "CHAPTER" else "COHERENCE_CHECK"
            ),
            "active_run_id": run.id,
            "coherence_run_id": run.id,
            "coherence_attempt": coherence_attempt,
            "coherence_request_key": request_key,
            "coherence_fingerprint": fingerprint,
            "completed_at": None,
            "error": None,
        }
    )
    if scope == "CHAPTER" and chapter_key:
        chapter_checks[chapter_key] = {
            "status": "PENDING",
            "attempt": chapter_attempt,
            "skill_run_id": run.id,
            "fingerprint": fingerprint,
            "issues": [],
        }
        generation["current_chapter_key"] = chapter_key
        generation["resume_sequence_no"] = next_sequence_no
        generation["current_sequence_no"] = None
        generation["current_fragment_key"] = None
        generation["issues"] = [
            issue
            for issue in generation.get("issues", [])
            if issue.get("chapter_key") != chapter_key
        ]
    else:
        generation["coherence"] = {
            "status": "PENDING",
            "skill_run_id": run.id,
            "fingerprint": fingerprint,
        }
        generation["current_sequence_no"] = None
        generation["current_fragment_key"] = None
        generation["issues"] = [
            issue for issue in generation.get("issues", []) if issue.get("scope") == "CHAPTER"
        ]
    plan.plan_json["generation"] = generation
    flag_modified(plan, "plan_json")
    await db.commit()
    await db.refresh(run)
    await db.refresh(plan)
    return run


async def validate_report_analysis_steps(db: AsyncSession, case_id: int) -> None:
    report_case = await db.get(ReportCase, case_id)
    if report_case is None:
        raise ValueError("report_case_not_found")
    if report_case.workflow_instance_id is None:
        raise ValueError("workflow_instance_not_found")
    rows = list(
        await db.scalars(
            select(StepTask).where(
                StepTask.workflow_instance_id == report_case.workflow_instance_id,
                StepTask.step_key.in_(_REPORT_ANALYSIS_STEP_KEYS),
            )
        )
    )
    completed = {
        row.step_key for row in rows if row.status == "COMPLETED"
    }
    if completed != set(_REPORT_ANALYSIS_STEP_KEYS):
        raise ValueError("report_analysis_steps_incomplete")
    analysis_fragments = await db.scalars(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.fragment_type == "ANALYSIS",
            ContentFragmentRevision.is_current.is_(True),
        )
    )
    if any(row.status != "CONFIRMED" for row in analysis_fragments):
        raise ValueError("report_analysis_fragments_incomplete")

    task_ids = [row.id for row in rows]
    skill_runs = await db.scalars(
        select(SkillRun)
        .where(SkillRun.step_task_id.in_(task_ids))
        .order_by(SkillRun.created_at, SkillRun.id)
    )
    latest_runs = {}
    for run in skill_runs:
        latest_runs[(run.step_task_id, run.target_type, run.target_key)] = run
    if any(
        run.status == "FAILED" and run.error == "skill_guardrail_blocked"
        for run in latest_runs.values()
    ):
        raise ValueError("report_analysis_guardrail_blocked")


async def _require_authoring_step(
    db: AsyncSession, report_case: ReportCase, actor: User
) -> StepTask:
    if report_case.workflow_instance_id is None:
        raise ValueError("workflow_instance_not_found")
    step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S5",
        )
        .with_for_update()
    )
    if step is None:
        raise ValueError("step_task_not_found")
    if step.status != "IN_REVIEW":
        raise ValueError("narrative_step_not_in_review")
    validate_step_actor(step, actor)
    return step


async def _validate_current_plan(
    db: AsyncSession, report_case: ReportCase, plan: NarrativePlan
) -> tuple[dict[str, Any], dict[str, Any]]:
    if plan.status != "CONFIRMED" or not plan.is_current:
        raise ValueError("narrative_plan_confirmation_required")
    semantic_model = await load_case_semantic_model(db, report_case.id)
    if not narrative_semantic_sources_match(plan, semantic_model):
        raise ValueError("narrative_semantics_changed")
    content_plan = _content_plan(plan)
    if not content_plan:
        raise ValueError("report_content_plan_required")
    issues = validate_report_content_plan(
        content_plan,
        semantic_model,
        plan.plan_json or {},
    )
    if content_plan.get("status") != "READY" or issues:
        raise ValueError("report_content_plan_blocked")
    return semantic_model, content_plan


async def _queue_generation_fragment(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    step: StepTask,
    plan: NarrativePlan,
    semantic_model: dict[str, Any],
    allocation: dict[str, Any],
    generation: dict[str, Any],
) -> SkillRun:
    attempt = generation["attempt"]
    sequence_no = allocation["sequence_no"]
    fragment_digest = hashlib.sha256(
        allocation["fragment_key"].encode("utf-8")
    ).hexdigest()[:32]
    run, _created = await queue_allocated_fragment_skill_run(
        db,
        report_case=report_case,
        step=step,
        plan=plan,
        semantic_model=semantic_model,
        allocation=allocation,
        idempotency_key=(
            f"report-generation:{report_case.id}:{plan.id}:{attempt}:{fragment_digest}"
        ),
        continuity=generation.get("continuity") or {},
        generation_metadata={
            "plan_id": plan.id,
            "attempt": attempt,
            "sequence_no": sequence_no,
            "fragment_key": allocation["fragment_key"],
            "request_key": generation.get("request_key"),
        },
        run_type="REGENERATE" if attempt > 1 else "INITIAL",
        commit=False,
    )
    generation["active_run_id"] = run.id
    generation["current_sequence_no"] = sequence_no
    generation["current_fragment_key"] = allocation["fragment_key"]
    plan.plan_json["generation"] = generation
    flag_modified(plan, "plan_json")
    await db.commit()
    await db.refresh(run)
    await db.refresh(plan)
    return run


async def start_case_report_generation(
    db: AsyncSession,
    *,
    case_id: int,
    actor: User,
    idempotency_key: str,
) -> NarrativePlan:
    report_case = await authorize_report_case(db, case_id, actor)
    await validate_report_analysis_steps(db, case_id)
    step = await _require_authoring_step(db, report_case, actor)
    plan = await get_current_narrative_plan(db, case_id)
    if plan is None:
        raise ValueError("narrative_plan_confirmation_required")
    semantic_model, content_plan = await _validate_current_plan(db, report_case, plan)
    generation = _generation_state(plan)
    state = generation.get("status", "NOT_STARTED")

    if state == "IN_PROGRESS":
        active_run = await db.get(SkillRun, generation.get("active_run_id"))
        if active_run is not None and active_run.status in {"PENDING", "RUNNING"}:
            return plan
        if active_run is not None:
            await advance_case_report_generation(db, active_run.id)
            refreshed = await get_current_narrative_plan(db, case_id)
            if refreshed is not None:
                return refreshed
        raise ValueError("report_generation_state_invalid")
    if state == "READY_FOR_REVIEW":
        return plan
    if state == "NEEDS_INPUT":
        raise ValueError("report_generation_semantic_gap")
    if state == "BLOCKED":
        raise ValueError("report_content_plan_blocked")
    if state in {
        "CHAPTER_COHERENCE_CHECK",
        "CHAPTER_COHERENCE_BLOCKED",
        "CHAPTER_COHERENCE_FAILED",
        "CHAPTER_COHERENCE_STALE",
        "COHERENCE_CHECK",
        "COHERENCE_BLOCKED",
        "COHERENCE_FAILED",
        "COHERENCE_STALE",
    }:
        raise ValueError("report_generation_state_invalid")
    if state == "FAILED" and generation.get("request_key") == idempotency_key:
        return plan

    generation["status"] = "IN_PROGRESS"
    generation["attempt"] = int(generation.get("attempt") or 0) + 1
    generation["request_key"] = idempotency_key
    generation["started_at"] = utc_now_iso()
    generation["completed_at"] = None
    generation["error"] = None
    generation["issues"] = []
    generation.setdefault("completed_fragment_keys", [])
    generation.setdefault(
        "continuity",
        {"established_points": [], "used_metaphors": [], "unresolved_threads": []},
    )
    sequence_no = generation.get("current_sequence_no") or 1
    allocation = _plan_fragment(content_plan, sequence_no)
    if allocation is None:
        raise ValueError("report_content_plan_sequence_invalid")
    plan.plan_json["generation"] = generation
    flag_modified(plan, "plan_json")
    await _queue_generation_fragment(
        db,
        report_case=report_case,
        step=step,
        plan=plan,
        semantic_model=semantic_model,
        allocation=allocation,
        generation=generation,
    )
    return plan


async def start_case_report_coherence_check(
    db: AsyncSession,
    *,
    case_id: int,
    actor: User,
    idempotency_key: str,
) -> SkillRun:
    report_case = await authorize_report_case(db, case_id, actor)
    await validate_report_analysis_steps(db, case_id)
    step = await _require_authoring_step(db, report_case, actor)
    plan = await get_current_narrative_plan(db, case_id)
    if plan is None:
        raise ValueError("narrative_plan_confirmation_required")
    semantic_model, content_plan = await _validate_current_plan(db, report_case, plan)
    generation = _generation_state(plan)
    state = generation.get("status", "NOT_STARTED")

    if state in {"CHAPTER_COHERENCE_CHECK", "COHERENCE_CHECK"}:
        active_run = await db.get(SkillRun, generation.get("active_run_id"))
        if active_run is not None:
            return active_run
        raise ValueError("report_coherence_state_invalid")
    chapter_retry = state in {
        "CHAPTER_COHERENCE_BLOCKED",
        "CHAPTER_COHERENCE_FAILED",
        "CHAPTER_COHERENCE_STALE",
    }
    if not chapter_retry and state not in {
        "READY_FOR_REVIEW",
        "COHERENCE_BLOCKED",
        "COHERENCE_FAILED",
        "COHERENCE_STALE",
    }:
        raise ValueError("report_coherence_not_ready")
    if generation.get("coherence_request_key") == idempotency_key:
        existing = await db.get(SkillRun, generation.get("coherence_run_id"))
        if existing is not None:
            return existing

    return await _queue_report_coherence_run(
        db,
        report_case=report_case,
        step=step,
        plan=plan,
        semantic_model=semantic_model,
        content_plan=content_plan,
        generation=generation,
        request_key=idempotency_key,
        scope="CHAPTER" if chapter_retry else "REPORT",
        chapter_key=(generation.get("current_chapter_key") if chapter_retry else None),
        next_sequence_no=(generation.get("resume_sequence_no") if chapter_retry else None),
    )


def _bounded_strings(values: Any, *, limit: int, length: int = 240) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(
        dict.fromkeys(
            value.strip()[:length]
            for value in values
            if isinstance(value, str) and value.strip()
        )
    )[:limit]


def _advance_continuity(
    current: dict[str, Any], allocation: dict[str, Any], output: dict[str, Any]
) -> dict[str, Any]:
    meta = output.get("presentation_meta") or {}
    points = list(current.get("established_points") or [])
    points.append(
        {
            "fragment_key": allocation["fragment_key"],
            "title": (output.get("title") or "")[:160],
            "finding_refs": list(output.get("used_findings") or []),
            "key_points": _bounded_strings(meta.get("key_points"), limit=4),
        }
    )
    metaphors = list(current.get("used_metaphors") or [])
    metaphors.extend(_bounded_strings(meta.get("used_metaphors"), limit=4))
    unresolved = list(current.get("unresolved_threads") or [])
    unresolved.extend(_bounded_strings(meta.get("unresolved_threads"), limit=4))
    transition = output.get("transition_hint")
    if isinstance(transition, str) and transition.strip():
        unresolved.append(transition.strip()[:300])
    return {
        "established_points": points[-6:],
        "used_metaphors": list(dict.fromkeys(metaphors))[-8:],
        "unresolved_threads": list(dict.fromkeys(unresolved))[-8:],
        "previous_fragment_key": allocation["fragment_key"],
        "previous_transition_hint": (
            transition.strip()[:300]
            if isinstance(transition, str) and transition.strip()
            else ""
        ),
    }


async def advance_case_report_generation(db: AsyncSession, run_id: int) -> NarrativePlan | None:
    run = await db.scalar(select(SkillRun).where(SkillRun.id == run_id).with_for_update())
    if run is None or run.target_type not in {
        "REPORT_FRAGMENT",
        "REPORT_CHAPTER_COHERENCE",
        "REPORT_COHERENCE",
    }:
        return None
    metadata = (run.context_snapshot or {}).get("report_generation")
    if not isinstance(metadata, dict) or not metadata.get("plan_id"):
        return None
    plan = await db.scalar(
        select(NarrativePlan)
        .where(NarrativePlan.id == metadata["plan_id"])
        .with_for_update()
    )
    if plan is None or not plan.is_current:
        return None
    generation = _generation_state(plan)
    expected_state = {
        "REPORT_CHAPTER_COHERENCE": "CHAPTER_COHERENCE_CHECK",
        "REPORT_COHERENCE": "COHERENCE_CHECK",
    }.get(run.target_type, "IN_PROGRESS")
    if (
        generation.get("status") != expected_state
        or generation.get("active_run_id") != run.id
    ):
        return plan
    if run.status in {"PENDING", "RUNNING"}:
        return plan

    if run.status == "FAILED":
        is_chapter = run.target_type == "REPORT_CHAPTER_COHERENCE"
        is_report_coherence = run.target_type == "REPORT_COHERENCE"
        is_coherence = is_chapter or is_report_coherence
        generation["status"] = (
            "CHAPTER_COHERENCE_FAILED"
            if is_chapter
            else "COHERENCE_FAILED" if is_report_coherence else "FAILED"
        )
        generation["error"] = run.error or (
            "report_coherence_check_failed"
            if is_coherence
            else "report_fragment_generation_failed"
        )
        generation["completed_at"] = utc_now_iso()
        generation["active_run_id"] = None
        generation.setdefault("issues", []).append(
            {
                "type": "REPORT_CHAPTER_COHERENCE_FAILED"
                if is_chapter
                else "REPORT_COHERENCE_CHECK_FAILED"
                if is_report_coherence
                else "FRAGMENT_GENERATION_FAILED",
                "target_fragment": run.target_key,
                "chapter_key": metadata.get("chapter_key") if is_chapter else None,
                "scope": "CHAPTER" if is_chapter else "REPORT" if is_report_coherence else None,
                "skill_run_id": run.id,
                "message": generation["error"],
            }
        )
        if is_chapter:
            chapter_key = metadata.get("chapter_key")
            generation.setdefault("chapter_checks", {})[chapter_key] = {
                "status": "FAILED",
                "attempt": metadata.get("chapter_attempt"),
                "skill_run_id": run.id,
                "fingerprint": metadata.get("coherence_fingerprint"),
                "issues": [],
                "error": generation["error"],
            }
        elif is_report_coherence:
            generation["coherence"] = {
                "status": "FAILED",
                "skill_run_id": run.id,
                "error": generation["error"],
                "completed_at": generation["completed_at"],
            }
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
        return plan

    output = run.output_parsed or {}
    if run.target_type in {"REPORT_CHAPTER_COHERENCE", "REPORT_COHERENCE"}:
        is_chapter = run.target_type == "REPORT_CHAPTER_COHERENCE"
        chapter_key = metadata.get("chapter_key") if is_chapter else None
        chapter_checks = generation.setdefault("chapter_checks", {})
        report_case = await db.get(ReportCase, run.report_case_id)
        if report_case is None:
            generation["status"] = "CHAPTER_COHERENCE_FAILED" if is_chapter else "COHERENCE_FAILED"
            generation["error"] = "report_case_not_found"
            generation["active_run_id"] = None
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan
        semantic_model = await load_case_semantic_model(db, report_case.id)
        if not narrative_semantic_sources_match(plan, semantic_model):
            plan.status = "STALE"
            generation["status"] = "CHAPTER_COHERENCE_STALE" if is_chapter else "COHERENCE_STALE"
            generation["error"] = "narrative_semantics_changed"
            generation["active_run_id"] = None
            if is_chapter:
                chapter_checks.setdefault(chapter_key, {}).update(
                    status="STALE", skill_run_id=run.id, error=generation["error"]
                )
            else:
                generation["coherence"] = {
                    "status": "STALE",
                    "skill_run_id": run.id,
                    "error": generation["error"],
                }
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan
        rows = await _load_authored_fragments(db, report_case.id, plan)
        snapshot = _fragment_snapshot(plan, rows)
        if is_chapter:
            snapshot = _chapter_snapshot(_content_plan(plan), snapshot, chapter_key)
        current_fingerprint = _coherence_fingerprint(plan, snapshot)
        if current_fingerprint != (run.context_snapshot or {}).get(
            "coherence_fingerprint"
        ):
            generation["status"] = "CHAPTER_COHERENCE_STALE" if is_chapter else "COHERENCE_STALE"
            generation["error"] = "report_content_changed_during_coherence_check"
            generation["active_run_id"] = None
            if is_chapter:
                chapter_checks.setdefault(chapter_key, {}).update(
                    status="STALE", skill_run_id=run.id, error=generation["error"]
                )
            else:
                generation["coherence"] = {
                    "status": "STALE",
                    "skill_run_id": run.id,
                    "error": generation["error"],
                }
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan

        source_keys = {item.get("fragment_key") for item in snapshot}
        planned_keys = {
            item.get("fragment_key")
            for item in _content_plan(plan).get("fragments", [])
            if isinstance(item, dict)
            and (not is_chapter or item.get("chapter") == chapter_key)
        }
        issues = output.get("issues") or []
        if any(
            issue.get("target_fragment_key") is not None
            and issue.get("target_fragment_key") not in source_keys.intersection(planned_keys)
            for issue in issues
        ):
            generation["status"] = "CHAPTER_COHERENCE_FAILED" if is_chapter else "COHERENCE_FAILED"
            generation["error"] = "report_coherence_target_invalid"
            generation["active_run_id"] = None
            if is_chapter:
                chapter_checks.setdefault(chapter_key, {}).update(
                    status="FAILED", skill_run_id=run.id, error=generation["error"]
                )
            else:
                generation["coherence"] = {
                    "status": "FAILED",
                    "skill_run_id": run.id,
                    "error": generation["error"],
                }
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan

        normalized_issues = [
            {
                "type": issue.get("issue_type") or "REPORT_COHERENCE_ISSUE",
                "severity": issue.get("severity"),
                "target_fragment": issue.get("target_fragment_key"),
                "message": issue.get("message") or "",
                "evidence": issue.get("evidence") or "",
                "suggestion": issue.get("suggestion") or "",
                "scope": "CHAPTER" if is_chapter else "REPORT",
                "chapter_key": chapter_key,
                "skill_run_id": run.id,
            }
            for issue in issues
        ]
        blocked = any(issue.get("severity") == "BLOCK" for issue in issues)
        completed_at = utc_now_iso()
        generation["active_run_id"] = None
        if is_chapter:
            chapter_checks[chapter_key] = {
                "status": "BLOCKED" if blocked else "PASSED",
                "attempt": metadata.get("chapter_attempt"),
                "skill_run_id": run.id,
                "fingerprint": current_fingerprint,
                "issues": normalized_issues,
                "completed_at": completed_at,
            }
            generation["issues"] = [
                issue
                for issue in generation.get("issues", [])
                if issue.get("chapter_key") != chapter_key
            ] + normalized_issues
            if blocked:
                generation["status"] = "CHAPTER_COHERENCE_BLOCKED"
                generation["completed_at"] = completed_at
                generation["error"] = "report_chapter_coherence_blocked"
                plan.plan_json["generation"] = generation
                flag_modified(plan, "plan_json")
                await db.commit()
                return plan

            generation["error"] = None
            next_sequence_no = metadata.get("next_sequence_no")
            if next_sequence_no is not None:
                next_allocation = _plan_fragment(_content_plan(plan), int(next_sequence_no))
                step = await db.scalar(
                    select(StepTask)
                    .where(
                        StepTask.workflow_instance_id == report_case.workflow_instance_id,
                        StepTask.step_key == "S5",
                    )
                    .with_for_update()
                )
                if next_allocation is None:
                    generation["status"] = "FAILED"
                    generation["error"] = "report_content_plan_sequence_invalid"
                    generation["completed_at"] = completed_at
                    plan.plan_json["generation"] = generation
                    flag_modified(plan, "plan_json")
                    await db.commit()
                    return plan
                if step is None or step.status != "IN_REVIEW":
                    generation["status"] = "PAUSED"
                    generation["error"] = "narrative_step_not_in_review"
                    generation["current_sequence_no"] = int(next_sequence_no)
                    plan.plan_json["generation"] = generation
                    flag_modified(plan, "plan_json")
                    await db.commit()
                    return plan
                generation["status"] = "IN_PROGRESS"
                generation["current_sequence_no"] = int(next_sequence_no)
                generation["current_fragment_key"] = next_allocation["fragment_key"]
                plan.plan_json["generation"] = generation
                flag_modified(plan, "plan_json")
                await _queue_generation_fragment(
                    db,
                    report_case=report_case,
                    step=step,
                    plan=plan,
                    semantic_model=semantic_model,
                    allocation=next_allocation,
                    generation=generation,
                )
                return plan

            step = await db.scalar(
                select(StepTask)
                .where(
                    StepTask.workflow_instance_id == report_case.workflow_instance_id,
                    StepTask.step_key == "S5",
                )
                .with_for_update()
            )
            if step is None or step.status != "IN_REVIEW":
                generation["status"] = "PAUSED"
                generation["error"] = "narrative_step_not_in_review"
                generation["current_sequence_no"] = None
                plan.plan_json["generation"] = generation
                flag_modified(plan, "plan_json")
                await db.commit()
                return plan
            await _queue_report_coherence_run(
                db,
                report_case=report_case,
                step=step,
                plan=plan,
                semantic_model=semantic_model,
                content_plan=_content_plan(plan),
                generation=generation,
                request_key=f"auto:report:{generation.get('request_key') or generation.get('attempt', 0)}",
                scope="REPORT",
            )
            return plan

        generation["status"] = "COHERENCE_BLOCKED" if blocked else "READY_FOR_REVIEW"
        generation["completed_at"] = completed_at
        chapter_issues = [
            issue for issue in generation.get("issues", []) if issue.get("scope") == "CHAPTER"
        ]
        generation["issues"] = chapter_issues + normalized_issues
        generation["coherence"] = {
            "status": "BLOCKED" if blocked else "PASSED",
            "skill_run_id": run.id,
            "fingerprint": current_fingerprint,
            "issues": issues,
            "completed_at": completed_at,
        }
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
        return plan

    if output.get("status") == "MISSING_SEMANTIC_SUPPORT":
        generation["status"] = "NEEDS_INPUT"
        generation["active_run_id"] = None
        generation["completed_at"] = utc_now_iso()
        generation.setdefault("issues", []).append(
            {
                "type": "MISSING_SEMANTIC_SUPPORT",
                "target_fragment": run.target_key,
                "skill_run_id": run.id,
                "message": output.get("message") or output.get("reason") or "请返回上游步骤补充已确认语义。",
                "related_sources": output.get("related_sources") or [],
            }
        )
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
        return plan

    content_plan = _content_plan(plan)
    sequence_no = metadata.get("sequence_no")
    allocation = _plan_fragment(content_plan, sequence_no)
    if allocation is None:
        generation["status"] = "FAILED"
        generation["error"] = "report_content_plan_sequence_invalid"
        generation["active_run_id"] = None
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
        return plan

    if not any(item.get("skill_run_id") == run.id for item in generation.get("runs", [])):
        generation.setdefault("runs", []).append(
            {
                "skill_run_id": run.id,
                "fragment_key": run.target_key,
                "sequence_no": sequence_no,
                "status": "COMPLETED",
                "completed_at": api_datetime(run.completed_at),
            }
        )
    if run.target_key not in generation.setdefault("completed_fragment_keys", []):
        generation["completed_fragment_keys"].append(run.target_key)
    generation["continuity"] = _advance_continuity(
        generation.get("continuity") or {}, allocation, output
    )
    generation["active_run_id"] = None

    next_sequence = int(sequence_no) + 1
    next_allocation = _plan_fragment(content_plan, next_sequence)
    chapter_finished = (
        next_allocation is None
        or next_allocation.get("chapter") != allocation.get("chapter")
    )
    if chapter_finished:
        report_case = await db.get(ReportCase, run.report_case_id)
        if report_case is None:
            generation["status"] = "FAILED"
            generation["error"] = "report_case_not_found"
            generation["active_run_id"] = None
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan
        try:
            semantic_model = await load_case_semantic_model(db, report_case.id)
            if not narrative_semantic_sources_match(plan, semantic_model):
                generation["status"] = "BLOCKED"
                generation["error"] = "narrative_semantics_changed"
                generation["active_run_id"] = None
                plan.status = "STALE"
                plan.plan_json["generation"] = generation
                flag_modified(plan, "plan_json")
                await db.commit()
                return plan
            step = await db.scalar(
                select(StepTask)
                .where(
                    StepTask.workflow_instance_id == report_case.workflow_instance_id,
                    StepTask.step_key == "S5",
                )
                .with_for_update()
            )
            if step is None or step.status != "IN_REVIEW":
                generation["status"] = "PAUSED"
                generation["error"] = "narrative_step_not_in_review"
                generation["current_sequence_no"] = None
                plan.plan_json["generation"] = generation
                flag_modified(plan, "plan_json")
                await db.commit()
                return plan
            await _queue_report_coherence_run(
                db,
                report_case=report_case,
                step=step,
                plan=plan,
                semantic_model=semantic_model,
                content_plan=content_plan,
                generation=generation,
                request_key=(
                    f"auto:chapter:{generation.get('request_key') or generation.get('attempt', 0)}:"
                    f"{allocation.get('chapter')}"
                ),
                scope="CHAPTER",
                chapter_key=allocation.get("chapter"),
                next_sequence_no=(next_sequence if next_allocation is not None else None),
            )
        except ValueError as error:
            generation["status"] = "FAILED"
            generation["error"] = str(error)
            generation["active_run_id"] = None
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
        return plan

    report_case = await db.get(ReportCase, run.report_case_id)
    if report_case is None:
        generation["status"] = "FAILED"
        generation["error"] = "report_case_not_found"
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
        return plan
    try:
        semantic_model = await load_case_semantic_model(db, report_case.id)
        if not narrative_semantic_sources_match(plan, semantic_model):
            generation["status"] = "BLOCKED"
            generation["error"] = "narrative_semantics_changed"
            generation["active_run_id"] = None
            plan.status = "STALE"
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan
        step = await db.scalar(
            select(StepTask)
            .where(
                StepTask.workflow_instance_id == report_case.workflow_instance_id,
                StepTask.step_key == "S5",
            )
            .with_for_update()
        )
        if step is None or step.status != "IN_REVIEW":
            generation["status"] = "PAUSED"
            generation["error"] = "narrative_step_not_in_review"
            generation["current_sequence_no"] = next_sequence
            plan.plan_json["generation"] = generation
            flag_modified(plan, "plan_json")
            await db.commit()
            return plan
        generation["current_sequence_no"] = next_sequence
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await _queue_generation_fragment(
            db,
            report_case=report_case,
            step=step,
            plan=plan,
            semantic_model=semantic_model,
            allocation=next_allocation,
            generation=generation,
        )
    except ValueError as error:
        generation["status"] = "FAILED"
        generation["error"] = str(error)
        generation["active_run_id"] = None
        plan.plan_json["generation"] = generation
        flag_modified(plan, "plan_json")
        await db.commit()
    return plan


async def validate_report_authoring_completion(
    db: AsyncSession, case_id: int
) -> None:
    report_case = await db.get(ReportCase, case_id)
    if report_case is None:
        raise ValueError("report_case_not_found")
    await validate_report_analysis_steps(db, case_id)
    plan = await get_current_narrative_plan(db, case_id)
    if plan is None:
        raise ValueError("narrative_plan_confirmation_required")
    if not _content_plan(plan):
        return
    semantic_model, content_plan = await _validate_current_plan(db, report_case, plan)
    generation = _generation_state(plan)
    if generation.get("status") != "READY_FOR_REVIEW":
        raise ValueError("report_authoring_not_ready")

    rows = list(
        await db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == case_id,
                ContentFragmentRevision.fragment_type == "REPORT",
                ContentFragmentRevision.is_current.is_(True),
            )
        )
    )
    by_key = {row.fragment_key: row for row in rows}
    missing = [
        allocation["fragment_key"]
        for allocation in content_plan.get("fragments", [])
        if allocation.get("required")
        and (
            (row := by_key.get(allocation["fragment_key"])) is None
            or row.status != "CONFIRMED"
            or not row.content.strip()
            or row.source_narrative_plan_id != plan.id
        )
    ]
    if missing:
        raise ValueError("report_authoring_not_ready")

    current_fingerprint = _coherence_fingerprint(
        plan, _fragment_snapshot(plan, [row for row in rows if row.status != "STALE"])
    )
    if (
        (generation.get("coherence") or {}).get("status") != "PASSED"
        or generation.get("coherence_fingerprint") != current_fingerprint
    ):
        raise ValueError("report_authoring_not_ready")

    must_include = set(
        (content_plan.get("semantic_priorities") or {}).get("must_include") or []
    )
    covered = {
        ref.get("finding_key")
        for row in rows
        if row.status == "CONFIRMED" and row.source_narrative_plan_id == plan.id
        for ref in (row.source_snapshot or {}).get("findings", [])
        if isinstance(ref, dict)
    }
    if not must_include.issubset(covered):
        raise ValueError("report_authoring_not_ready")
