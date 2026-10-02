from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.skill_runtime import (
    list_case_skill_runs,
    queue_case_step_skill_run,
    queue_debug_skill_run,
)
from app.application.skill_evaluation import ensure_evaluation_passed_before_publish
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.schemas import (
    SkillRunCreate,
    SkillRunResponse,
    ConsultantSkillRunResponse,
    SkillVersionCreate,
    SkillVersionResponse,
    SkillVersionUpdate,
    StepSkillRunCreate,
)
from app.domains.skills.service import (
    create_skill_draft,
    publish_skill_version,
    update_skill_draft,
)
from app.models.user import User


admin_router = APIRouter()
staff_router = APIRouter()


def _skill_error(error: ValueError) -> None:
    code = str(error)
    if code in {
        "skill_version_not_found",
        "skill_run_not_found",
        "report_case_not_found",
        "workflow_instance_not_found",
        "step_task_not_found",
    }:
        raise HTTPException(status_code=404, detail=code)
    if code in {
        "skill_version_immutable",
        "skill_run_idempotency_conflict",
        "step_not_ready",
        "step_assigned_to_another_consultant",
        "step_skill_not_configured",
        "step_skill_version_unavailable",
        "skill_evaluation_required",
        "skill_evaluation_full_dataset_required",
        "skill_evaluation_incomplete",
        "skill_evaluation_failed",
    }:
        raise HTTPException(status_code=409, detail=code)
    if code == "report_case_forbidden":
        raise HTTPException(status_code=403, detail=code)
    if code.startswith("skill_") or code.startswith("step_"):
        raise HTTPException(status_code=422, detail=code)
    raise HTTPException(status_code=400, detail=code)


@admin_router.get("/skills", response_model=list[SkillVersionResponse])
async def list_skills(
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    rows = await db.scalars(
        select(AISkillVersion).order_by(
            AISkillVersion.skill_key, AISkillVersion.version.desc()
        )
    )
    return list(rows.all())


@admin_router.post(
    "/skills", response_model=SkillVersionResponse, status_code=status.HTTP_201_CREATED
)
async def create_skill(
    payload: SkillVersionCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    try:
        version = await create_skill_draft(
            db,
            skill_key=payload.skill_key,
            name=payload.name,
            category=payload.category,
            specification=payload.specification_json,
            created_by=actor.id,
        )
        await db.commit()
        await db.refresh(version)
        return version
    except ValueError as error:
        await db.rollback()
        _skill_error(error)


@admin_router.put("/skills/{version_id}", response_model=SkillVersionResponse)
async def update_skill(
    version_id: int,
    payload: SkillVersionUpdate,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        version = await update_skill_draft(
            db,
            version_id,
            name=payload.name,
            category=payload.category,
            specification=payload.specification_json,
        )
        await db.commit()
        await db.refresh(version)
        return version
    except ValueError as error:
        await db.rollback()
        _skill_error(error)


@admin_router.post("/skills/{version_id}/publish", response_model=SkillVersionResponse)
async def publish_skill(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    try:
        await ensure_evaluation_passed_before_publish(db, version_id)
        version = await publish_skill_version(db, version_id, published_by=actor.id)
        await db.commit()
        await db.refresh(version)
        return version
    except ValueError as error:
        await db.rollback()
        _skill_error(error)


@admin_router.post(
    "/skills/{version_id}/runs",
    response_model=SkillRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_skill(
    version_id: int,
    payload: SkillRunCreate,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        run, _created = await queue_debug_skill_run(
            db,
            version_id=version_id,
            idempotency_key=payload.idempotency_key,
            input_data=payload.input_data,
            runtime_instruction=payload.runtime_instruction,
        )
        return run
    except ValueError as error:
        await db.rollback()
        _skill_error(error)


@admin_router.get("/skills/{version_id}/runs", response_model=list[SkillRunResponse])
async def list_skill_runs(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    rows = await db.scalars(
        select(SkillRun)
        .where(SkillRun.skill_version_id == version_id)
        .order_by(SkillRun.created_at.desc(), SkillRun.id.desc())
        .limit(100)
    )
    return list(rows.all())


@staff_router.get(
    "/report-cases/{case_id}/skill-runs",
    response_model=list[ConsultantSkillRunResponse],
)
async def list_case_runs(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin", "consultant")),
):
    try:
        return await list_case_skill_runs(db, case_id=case_id, actor=actor)
    except ValueError as error:
        _skill_error(error)


@staff_router.post(
    "/report-cases/{case_id}/steps/{step_key}/skill-runs",
    response_model=SkillRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_case_step_skill(
    case_id: int,
    step_key: str,
    payload: StepSkillRunCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin", "consultant")),
):
    try:
        run, _created = await queue_case_step_skill_run(
            db,
            case_id=case_id,
            step_key=step_key,
            actor=actor,
            idempotency_key=payload.idempotency_key,
            runtime_instruction=payload.runtime_instruction,
        )
        return run
    except ValueError as error:
        await db.rollback()
        _skill_error(error)
