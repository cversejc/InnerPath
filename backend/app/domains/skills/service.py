from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .definitions import (
    DEFAULT_SKILL_KEY,
    REASONING_GUIDANCE_SKILL_KEYS,
    default_analysis_skill_specifications,
    default_validator_skill_specification,
    default_narrative_skill_specifications,
    prepare_reasoning_guidance_specification,
    validate_skill_specification,
)
from .models import AISkillVersion, SkillRun
from .lifecycle import require_active_skill
from .builtin_examples import ensure_builtin_examples


def _now() -> datetime:
    return datetime.utcnow()


def _system_managed_projection(specification: dict[str, Any]) -> dict[str, Any]:
    projection = deepcopy(specification)
    projection.pop("reasoning_guidance", None)
    instructions = projection.get("instructions")
    if isinstance(instructions, dict):
        instructions.pop("objective", None)
        instructions.pop("methodology", None)
    return projection


def _is_reasoning_guidance_specification(specification: Any) -> bool:
    identity = specification.get("identity") if isinstance(specification, dict) else None
    return (
        isinstance(identity, dict)
        and identity.get("skill_key") in REASONING_GUIDANCE_SKILL_KEYS
    )


async def _ensure_published_builtin_version(
    db: AsyncSession,
    *,
    skill_key: str,
    category: str,
    specification: dict[str, Any],
) -> AISkillVersion:
    await ensure_builtin_examples(db, skill_key)
    latest_published = await db.scalar(
        select(AISkillVersion)
        .where(
            AISkillVersion.skill_key == skill_key,
            AISkillVersion.status == "PUBLISHED",
        )
        .order_by(AISkillVersion.version.desc())
        .limit(1)
    )
    if skill_key in REASONING_GUIDANCE_SKILL_KEYS and latest_published is not None:
        if latest_published.specification_json == specification:
            return latest_published
        if (
            latest_published.created_by is not None
            or latest_published.published_by is not None
        ):
            # Administrator-maintained reasoning remains authoritative. Code
            # defaults initialize new installations and never overwrite it.
            return latest_published

        latest_any = await db.scalar(
            select(AISkillVersion)
            .where(AISkillVersion.skill_key == skill_key)
            .order_by(AISkillVersion.version.desc())
            .limit(1)
        )
        if latest_any is not None and latest_any.version > latest_published.version:
            # Do not publish over an administrator's in-progress draft during
            # startup. Matching system-created drafts can be promoted directly.
            if latest_any.created_by is not None:
                return latest_published
            if (
                latest_any.status == "DRAFT"
                and prepare_reasoning_guidance_specification(
                    latest_any.specification_json
                ).get("reasoning_guidance")
                == prepare_reasoning_guidance_specification(specification).get(
                    "reasoning_guidance"
                )
            ):
                # Keep the administrator-owned guidance while refreshing
                # program-owned runtime fields from the current definition.
                latest_any.specification_json = specification
                latest_any.status = "PUBLISHED"
                latest_any.published_by = None
                latest_any.published_at = _now()
                await db.flush()
                return latest_any
    if (
        latest_published is not None
        and (latest_published.specification_json == specification
             or latest_published.created_by is not None
             or latest_published.published_by is not None)
    ):
        return latest_published

    latest_version = await db.scalar(
        select(func.max(AISkillVersion.version)).where(
            AISkillVersion.skill_key == skill_key
        )
    )

    now = _now()
    version = AISkillVersion(
        skill_key=skill_key,
        name=specification["identity"]["name"],
        category=category,
        version=(latest_version or 0) + 1,
        status="PUBLISHED",
        specification_json=specification,
        created_by=None,
        published_by=None,
        created_at=now,
        published_at=now,
    )
    try:
        async with db.begin_nested():
            db.add(version)
            await db.flush()
        return version
    except IntegrityError:
        existing = await db.scalar(
            select(AISkillVersion)
            .where(
                AISkillVersion.skill_key == skill_key,
                AISkillVersion.status == "PUBLISHED",
            )
            .order_by(AISkillVersion.version.desc())
            .limit(1)
        )
        if (
            existing is None
            or existing.specification_json != specification
        ):
            raise
        return existing


async def create_skill_draft(
    db: AsyncSession,
    *,
    skill_key: str,
    name: str,
    category: str,
    specification: dict[str, Any],
    created_by: int | None,
) -> AISkillVersion:
    require_active_skill(skill_key)
    if _is_reasoning_guidance_specification(specification):
        specification = prepare_reasoning_guidance_specification(specification)
    spec = validate_skill_specification(specification)
    if spec["identity"]["skill_key"] != skill_key or spec["identity"]["name"] != name:
        raise ValueError("skill_identity_mismatch")
    if category not in {"ANALYSIS", "ACTION", "AUTHORING", "VALIDATOR"}:
        raise ValueError("skill_category_invalid")
    latest = await db.scalar(
        select(AISkillVersion)
        .where(AISkillVersion.skill_key == skill_key)
        .order_by(AISkillVersion.version.desc())
        .limit(1)
    )
    if skill_key in REASONING_GUIDANCE_SKILL_KEYS and latest is not None:
        latest_spec = validate_skill_specification(
            prepare_reasoning_guidance_specification(latest.specification_json)
        )
        if (
            category != latest.category
            or _system_managed_projection(spec)
            != _system_managed_projection(latest_spec)
        ):
            raise ValueError("skill_system_managed_fields_immutable")
    version = AISkillVersion(
        skill_key=skill_key,
        name=name,
        category=category,
        version=(latest.version if latest else 0) + 1,
        status="DRAFT",
        specification_json=spec,
        created_by=created_by,
        created_at=_now(),
    )
    db.add(version)
    await db.flush()
    return version


async def update_skill_draft(
    db: AsyncSession,
    version_id: int,
    *,
    name: str,
    category: str,
    specification: dict[str, Any],
) -> AISkillVersion:
    version = await db.scalar(
        select(AISkillVersion).where(AISkillVersion.id == version_id).with_for_update()
    )
    if version is None:
        raise ValueError("skill_version_not_found")
    require_active_skill(version.skill_key)
    if version.status != "DRAFT":
        raise ValueError("skill_version_immutable")
    if _is_reasoning_guidance_specification(specification):
        specification = prepare_reasoning_guidance_specification(specification)
    spec = validate_skill_specification(specification)
    if (
        spec["identity"]["skill_key"] != version.skill_key
        or spec["identity"]["name"] != name
    ):
        raise ValueError("skill_identity_mismatch")
    if category not in {"ANALYSIS", "ACTION", "AUTHORING", "VALIDATOR"}:
        raise ValueError("skill_category_invalid")
    if version.skill_key in REASONING_GUIDANCE_SKILL_KEYS:
        current_spec = validate_skill_specification(
            prepare_reasoning_guidance_specification(version.specification_json)
        )
        if (
            category != version.category
            or _system_managed_projection(spec)
            != _system_managed_projection(current_spec)
        ):
            raise ValueError("skill_system_managed_fields_immutable")
    version.name = name
    version.category = category
    version.specification_json = spec
    await db.flush()
    return version


async def update_reasoning_guidance(
    db: AsyncSession,
    version_id: int,
    *,
    objective: str,
    methodology: list[str],
) -> AISkillVersion:
    version = await db.scalar(
        select(AISkillVersion).where(AISkillVersion.id == version_id).with_for_update()
    )
    if version is None:
        raise ValueError("skill_version_not_found")
    require_active_skill(version.skill_key)
    if version.status != "DRAFT":
        raise ValueError("skill_version_immutable")
    if version.skill_key not in REASONING_GUIDANCE_SKILL_KEYS:
        raise ValueError("skill_instruction_edit_not_supported")

    objective = objective.strip()
    methodology = [item.strip() for item in methodology if item and item.strip()]
    if not objective or len(objective) > 1200:
        raise ValueError("skill_instruction_objective_invalid")
    if not methodology or len(methodology) > 40 or any(
        len(item) > 1000 for item in methodology
    ):
        raise ValueError("skill_instruction_methodology_invalid")

    specification = prepare_reasoning_guidance_specification(version.specification_json)
    specification["reasoning_guidance"] = {
        "objective": objective,
        "methodology": methodology,
    }
    version.specification_json = validate_skill_specification(specification)
    await db.flush()
    return version


async def update_s1_reasoning_guidance(
    db: AsyncSession,
    version_id: int,
    *,
    objective: str,
    methodology: list[str],
) -> AISkillVersion:
    """Compatibility alias for callers that historically edited S1 only."""
    return await update_reasoning_guidance(
        db,
        version_id,
        objective=objective,
        methodology=methodology,
    )


async def publish_skill_version(
    db: AsyncSession, version_id: int, *, published_by: int | None
) -> AISkillVersion:
    version = await db.scalar(
        select(AISkillVersion).where(AISkillVersion.id == version_id).with_for_update()
    )
    if version is None:
        raise ValueError("skill_version_not_found")
    require_active_skill(version.skill_key)
    if version.status != "DRAFT":
        raise ValueError("skill_version_immutable")
    version.specification_json = validate_skill_specification(
        version.specification_json
    )
    version.status = "PUBLISHED"
    version.published_by = published_by
    version.published_at = _now()
    await db.flush()
    return version


async def ensure_default_skill_version(db: AsyncSession) -> AISkillVersion:
    """Read a historical version for old callers; never initialize this skill."""
    existing = await db.scalar(select(AISkillVersion).where(
        AISkillVersion.skill_key == DEFAULT_SKILL_KEY,
        AISkillVersion.version == 1,
    ))
    if existing is None:
        raise ValueError("skill_retired")
    return existing


async def ensure_default_narrative_skill_versions(
    db: AsyncSession,
) -> list[AISkillVersion]:
    return [
        await _ensure_published_builtin_version(
            db,
            skill_key=spec["identity"]["skill_key"],
            category="AUTHORING",
            specification=spec,
        )
        for spec in default_narrative_skill_specifications()
    ]


async def ensure_default_analysis_skill_versions(
    db: AsyncSession,
) -> list[AISkillVersion]:
    return [
        await _ensure_published_builtin_version(
            db,
            skill_key=spec["identity"]["skill_key"],
            category="ANALYSIS",
            specification=spec,
        )
        for spec in default_analysis_skill_specifications()
    ]


async def ensure_default_validator_skill_version(db: AsyncSession) -> AISkillVersion:
    spec = default_validator_skill_specification()
    return await _ensure_published_builtin_version(
        db,
        skill_key="report.final_validator",
        category="VALIDATOR",
        specification=spec,
    )


async def create_skill_run(
    db: AsyncSession,
    *,
    skill_version_id: int,
    idempotency_key: str,
    input_snapshot: dict[str, Any],
    context_snapshot: dict[str, Any],
    run_type: str = "EVALUATION",
    target_type: str = "DEBUG",
    target_key: str | None = None,
    report_case_id: int | None = None,
    workflow_instance_id: int | None = None,
    step_task_id: int | None = None,
    runtime_instruction: str | None = None,
    selected_examples: list[dict[str, Any]] | None = None,
) -> tuple[SkillRun, bool]:
    existing = await db.scalar(
        select(SkillRun).where(SkillRun.idempotency_key == idempotency_key)
    )
    if existing:
        if (
            existing.skill_version_id != skill_version_id
            or existing.report_case_id != report_case_id
            or existing.target_type != target_type
            or existing.target_key != target_key
        ):
            raise ValueError("skill_run_idempotency_conflict")
        return existing, False
    skill = await db.get(AISkillVersion, skill_version_id)
    if skill is None:
        raise ValueError("skill_version_not_found")
    if skill.status == "RETIRED":
        raise ValueError("skill_version_retired")
    if report_case_id is not None and target_type != "CALENDAR_PRODUCTION":
        from app.domains.workflow.models import ReportCase
        from .bindings import resolve_case_skill
        case = await db.get(ReportCase, report_case_id)
        if case is not None and (case.application_snapshot or {}).get("skill_bindings") is not None:
            pinned = await resolve_case_skill(db, case, skill.skill_key)
            if pinned.id != skill.id:
                raise ValueError("case_skill_version_mismatch")
    if run_type not in {"INITIAL", "REGENERATE", "REWRITE", "VALIDATE", "EVALUATION"}:
        raise ValueError("skill_run_type_invalid")
    now = _now()
    run = SkillRun(
        skill_version_id=skill_version_id,
        report_case_id=report_case_id,
        workflow_instance_id=workflow_instance_id,
        step_task_id=step_task_id,
        target_type=target_type,
        target_key=target_key,
        run_type=run_type,
        status="PENDING",
        idempotency_key=idempotency_key,
        runtime_instruction=runtime_instruction,
        input_snapshot=input_snapshot,
        context_snapshot=context_snapshot,
        selected_examples=selected_examples or [],
        selected_knowledge=[],
        model_trace={},
        retry_count=0,
        created_at=now,
    )
    db.add(run)
    await db.flush()
    return run, True
