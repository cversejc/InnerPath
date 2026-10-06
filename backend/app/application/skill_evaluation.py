"""Application use cases for queued Skill regression batches."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.skill_runtime import queue_regression_skill_run
from app.domains.skills.evaluation import (
    load_regression_dataset,
    regression_cases,
    select_regression_cases,
    specification_digest,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.definitions import REASONING_GUIDANCE_SKILL_KEYS


def list_evaluation_cases(*, skill_key: str | None = None) -> list[dict]:
    return [
        {
            "case_key": case["case_key"],
            "title": case["title"],
            "description": case["description"],
            "skill_key": case["skill_key"],
        }
        for case in regression_cases(skill_key=skill_key)
    ]


async def start_evaluation_batch(
    db: AsyncSession, *, version_id: int, case_keys: list[str] | None = None
) -> dict:
    version = await db.get(AISkillVersion, version_id)
    if version is None:
        raise ValueError("skill_version_not_found")
    if version.status == "RETIRED":
        raise ValueError("skill_version_retired")
    selected = select_regression_cases(
        skill_key=version.skill_key,
        case_keys=case_keys,
    )
    dataset_version = load_regression_dataset()["version"]
    spec_hash = specification_digest(version.specification_json)
    batch_id = uuid4().hex
    runs = []
    for case in selected:
        metadata = {
            "evaluation": {
                "batch_id": batch_id,
                "dataset_version": dataset_version,
                "specification_sha256": spec_hash,
                "case_key": case["case_key"],
                "title": case["title"],
                "expectation": case.get("expectation") or {},
                "result": None,
            }
        }
        run, _created = await queue_regression_skill_run(
            db,
            version_id=version.id,
            idempotency_key=f"evaluation:{batch_id}:{version.id}:{case['case_key']}",
            input_data=case.get("input_data") or {},
            context_metadata=metadata,
            case_key=case["case_key"],
        )
        runs.append(run)
    return await _serialize_batch(batch_id, dataset_version, runs)


async def get_evaluation_batch(db: AsyncSession, batch_id: str) -> dict:
    runs = await _load_regression_runs(db)
    matching = [
        run
        for run in runs
        if (run.context_snapshot or {}).get("evaluation", {}).get("batch_id")
        == batch_id
    ]
    if not matching:
        raise ValueError("skill_evaluation_batch_not_found")
    dataset_version = (
        (matching[0].context_snapshot or {}).get("evaluation", {}).get(
            "dataset_version"
        )
        or "unknown"
    )
    return await _serialize_batch(batch_id, dataset_version, matching)


async def list_evaluation_batches(
    db: AsyncSession, *, version_id: int, limit: int = 30
) -> list[dict]:
    runs = await _load_regression_runs(db, version_id=version_id)
    grouped: dict[str, list[SkillRun]] = {}
    for run in runs:
        evaluation = (run.context_snapshot or {}).get("evaluation") or {}
        batch_id = evaluation.get("batch_id")
        if batch_id:
            grouped.setdefault(batch_id, []).append(run)
    results = []
    for batch_id, batch_runs in grouped.items():
        dataset_version = (
            (batch_runs[0].context_snapshot or {}).get("evaluation", {}).get(
                "dataset_version"
            )
            or "unknown"
        )
        results.append(await _serialize_batch(batch_id, dataset_version, batch_runs))
    results.sort(
        key=lambda item: max(
            (run.created_at for run in grouped[item["batch_id"]]), default=None
        ),
        reverse=True,
    )
    return results[:limit]


async def ensure_evaluation_passed_before_publish(
    db: AsyncSession, version_id: int
) -> None:
    version = await db.get(AISkillVersion, version_id)
    if version is None:
        raise ValueError("skill_version_not_found")
    if version.skill_key in REASONING_GUIDANCE_SKILL_KEYS:
        # These built-in skills contain human-maintained reasoning guidance;
        # their runtime input/output contract is fixed and evaluated in code.
        # Requiring a regression batch here blocks routine guidance publishing
        # without validating a user-editable schema.
        return
    required_cases = regression_cases(skill_key=version.skill_key)
    if not required_cases:
        return
    expected_keys = {case["case_key"] for case in required_cases}
    expected_hash = specification_digest(version.specification_json)
    batches: dict[str, list[SkillRun]] = {}
    for run in await _load_regression_runs(db, version_id=version_id):
        evaluation = (run.context_snapshot or {}).get("evaluation") or {}
        if evaluation.get("specification_sha256") != expected_hash:
            continue
        batch_id = evaluation.get("batch_id")
        if batch_id:
            batches.setdefault(batch_id, []).append(run)
    if not batches:
        raise ValueError("skill_evaluation_required")
    latest = max(
        batches.values(),
        key=lambda rows: max(run.created_at for run in rows),
    )
    batch_keys = {
        (run.context_snapshot or {}).get("evaluation", {}).get("case_key")
        for run in latest
    }
    if batch_keys != expected_keys:
        raise ValueError("skill_evaluation_full_dataset_required")
    if any(run.status in {"PENDING", "RUNNING"} for run in latest):
        raise ValueError("skill_evaluation_incomplete")
    if any(
        run.status != "COMPLETED"
        or not ((run.context_snapshot or {}).get("evaluation", {}).get("result") or {}).get("passed")
        for run in latest
    ):
        raise ValueError("skill_evaluation_failed")


async def _load_regression_runs(
    db: AsyncSession, *, version_id: int | None = None
) -> list[SkillRun]:
    query = select(SkillRun).where(SkillRun.target_type == "REGRESSION")
    if version_id is not None:
        query = query.where(SkillRun.skill_version_id == version_id)
    rows = await db.scalars(query.order_by(SkillRun.created_at.desc(), SkillRun.id.desc()))
    return list(rows.all())


async def _serialize_batch(
    batch_id: str, dataset_version: str, runs: list[SkillRun]
) -> dict:
    run_items = []
    completed = 0
    failed = 0
    passed = 0
    for run in runs:
        evaluation = (run.context_snapshot or {}).get("evaluation") or {}
        result = evaluation.get("result") or {}
        completed += run.status == "COMPLETED"
        failed += run.status == "FAILED"
        passed += result.get("passed") is True
        run_items.append(
            {
                "run_id": run.id,
                "case_key": evaluation.get("case_key") or run.target_key,
                "title": evaluation.get("title") or run.target_key,
                "status": run.status,
                "score": result.get("score"),
                "passed": result.get("passed"),
                "checks": result.get("checks") or [],
                "error": run.error,
                "selected_examples": run.selected_examples or [],
            }
        )
    total = len(runs)
    done = completed + failed == total
    return {
        "batch_id": batch_id,
        "dataset_version": dataset_version,
        "total": total,
        "completed": completed,
        "failed": failed,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if done and total else None,
        "runs": run_items,
    }
