from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.skills.models import SkillRun

from .common import require_case
from .dependencies import mark_report_fragments_stale_for_plan
from .models import NarrativePlan
from .queries import load_case_semantic_model
from .report_content_plan import (
    build_report_content_plan,
    validate_report_content_plan,
)


def semantic_source_snapshot(semantic_model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
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


async def get_current_narrative_plan(
    db: AsyncSession, report_case_id: int
) -> NarrativePlan | None:
    return await db.scalar(
        select(NarrativePlan)
        .where(
            NarrativePlan.report_case_id == report_case_id,
            NarrativePlan.is_current.is_(True),
        )
        .with_for_update()
    )


async def confirm_narrative_plan(
    db: AsyncSession,
    *,
    report_case_id: int,
    skill_run_id: int,
    candidate_key: str,
    overrides: dict[str, Any],
    actor_id: int,
) -> NarrativePlan:
    await require_case(db, report_case_id)
    run = await db.get(SkillRun, skill_run_id)
    if (
        run is None
        or run.report_case_id != report_case_id
        or run.target_type != "NARRATIVE_CANDIDATES"
    ):
        raise ValueError("narrative_candidate_run_invalid")
    if run.status != "COMPLETED":
        raise ValueError("narrative_candidate_run_not_completed")

    semantic_model = await load_case_semantic_model(db, report_case_id)
    current_sources = semantic_source_snapshot(semantic_model)
    run_sources = (run.context_snapshot or {}).get("semantic_source_snapshot")
    if run_sources != current_sources:
        raise ValueError("narrative_semantics_changed")

    candidates = (run.output_parsed or {}).get("candidates") or []
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("candidate_key") == candidate_key
        ),
        None,
    )
    if candidate is None:
        raise ValueError("narrative_candidate_not_found")
    supported_ordered = list(dict.fromkeys(candidate.get("supporting_findings") or []))
    supported = set(supported_ordered)
    valid_finding_keys = {item["finding_key"] for item in semantic_model["findings"]}
    if not supported.issubset(valid_finding_keys):
        raise ValueError("narrative_candidate_unsupported_finding")

    allowed_overrides = {
        "core_theme",
        "priority_blocks",
        "must_include_findings",
        "self_direction",
        "reader_profile",
        "narrative_arc",
        "chapter_strategy",
    }
    if set(overrides) - allowed_overrides:
        raise ValueError("narrative_plan_override_invalid")
    core_theme = overrides.get("core_theme", candidate.get("theme"))
    if not isinstance(core_theme, str) or not core_theme.strip() or len(core_theme) > 1000:
        raise ValueError("narrative_plan_theme_invalid")
    must_include = overrides.get("must_include_findings", supported_ordered)
    if (
        not isinstance(must_include, list)
        or any(not isinstance(key, str) for key in must_include)
        or not set(must_include).issubset(supported)
    ):
        raise ValueError("narrative_plan_findings_invalid")
    self_direction = overrides.get("self_direction")
    if self_direction and self_direction not in valid_finding_keys:
        raise ValueError("narrative_plan_findings_invalid")
    priority_blocks = overrides.get("priority_blocks", candidate.get("priority_blocks") or [])
    narrative_arc = overrides.get("narrative_arc", candidate.get("narrative_arc") or [])
    if not isinstance(priority_blocks, list) or not isinstance(narrative_arc, list):
        raise ValueError("narrative_plan_structure_invalid")
    for block in priority_blocks:
        if isinstance(block, dict) and not set(block.get("finding_refs") or []).issubset(
            valid_finding_keys
        ):
            raise ValueError("narrative_plan_findings_invalid")

    plan_json = {
        "version": 1,
        "core_theme": core_theme.strip(),
        "selected_candidate": candidate_key,
        "priority_blocks": priority_blocks,
        "must_include_findings": must_include,
        "self_direction": self_direction,
        "reader_profile": overrides.get(
            "reader_profile",
            {
                "directness": "medium",
                "warmth": "medium",
                "theory_density": "low",
                "action_density": "high",
                "metaphor_density": "medium",
            },
        ),
        "narrative_arc": narrative_arc,
        "chapter_strategy": overrides.get("chapter_strategy", {}),
        "rationale": candidate.get("rationale", ""),
        "deemphasized_findings": candidate.get("deemphasized_findings") or [],
    }
    plan_json["priority_blocks"] = priority_blocks
    if not isinstance(plan_json["reader_profile"], dict) or not isinstance(
        plan_json["chapter_strategy"], dict
    ):
        raise ValueError("narrative_plan_structure_invalid")

    application_snapshot = (await require_case(db, report_case_id)).application_snapshot or {}
    content_plan = build_report_content_plan(
        semantic_model,
        plan_json,
        user_context=application_snapshot.get("context") or {},
    )
    content_issues = validate_report_content_plan(
        content_plan, semantic_model, plan_json
    )
    content_plan["status"] = "READY" if not content_issues else "BLOCKED"
    content_plan["validation_issues"] = content_issues
    plan_json["content_plan"] = content_plan
    plan_json["generation"] = {
        "status": "NOT_STARTED" if not content_issues else "BLOCKED",
        "attempt": 0,
        "request_key": None,
        "current_sequence_no": None,
        "active_run_id": None,
        "completed_fragment_keys": [],
        "continuity": {
            "established_points": [],
            "used_metaphors": [],
            "unresolved_threads": [],
        },
        "runs": [],
        "issues": content_issues,
    }

    current = await get_current_narrative_plan(db, report_case_id)
    latest_version = await db.scalar(
        select(func.max(NarrativePlan.version_no)).where(
            NarrativePlan.report_case_id == report_case_id
        )
    )
    if current is not None:
        current.is_current = False
        current.status = "SUPERSEDED"
        await mark_report_fragments_stale_for_plan(
            db, current.id, reason="NARRATIVE_CHANGED"
        )
    now = datetime.utcnow()
    plan = NarrativePlan(
        report_case_id=report_case_id,
        version_no=(latest_version or 0) + 1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=run.id,
        selected_candidate_key=candidate_key,
        plan_json=plan_json,
        source_snapshot=current_sources,
        created_by=actor_id,
        confirmed_by=actor_id,
        created_at=now,
        confirmed_at=now,
    )
    db.add(plan)
    await db.flush()
    return plan
