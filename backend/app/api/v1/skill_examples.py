from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.skill_runtime import authorize_report_case
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.skills.examples import (
    create_example_candidate,
    create_example_revision,
    list_skill_examples,
    publish_skill_example,
    retire_skill_example,
    update_example_redaction,
)
from app.domains.skills.models import SkillRun
from app.domains.skills.schemas import (
    SkillExampleAdminResponse,
    SkillExamplePublicResponse,
    SkillExampleRecommendation,
    SkillExampleRedaction,
)
from app.models.user import User


admin_router = APIRouter()
staff_router = APIRouter()


def _example_error(error: ValueError) -> None:
    code = str(error)
    if code in {"skill_example_not_found", "skill_run_not_found", "report_case_not_found"}:
        raise HTTPException(status_code=404, detail=code)
    if code == "report_case_forbidden":
        raise HTTPException(status_code=403, detail=code)
    if code in {
        "skill_example_immutable",
        "skill_example_not_candidate",
        "skill_example_already_retired",
        "skill_example_revision_requires_published_source",
    }:
        raise HTTPException(status_code=409, detail=code)
    if code.startswith("skill_example_"):
        raise HTTPException(status_code=422, detail=code)
    raise HTTPException(status_code=400, detail=code)


@staff_router.get("/skill-examples", response_model=list[SkillExamplePublicResponse])
async def list_published_examples(
    skill_key: str | None = None,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin", "consultant")),
):
    return await list_skill_examples(
        db, skill_key=skill_key, status="PUBLISHED", limit=200
    )


@staff_router.post(
    "/report-cases/{case_id}/skill-examples",
    response_model=SkillExampleAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def recommend_skill_example(
    case_id: int,
    payload: SkillExampleRecommendation,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin", "consultant")),
):
    try:
        await authorize_report_case(db, case_id, actor)
        run = await db.get(SkillRun, payload.skill_run_id)
        if run is None:
            raise ValueError("skill_run_not_found")
        example = await create_example_candidate(
            db,
            report_case_id=case_id,
            skill_run=run,
            example_type=payload.example_type,
            scenario_tags=payload.scenario_tags,
            teaching_points=payload.teaching_points,
            expected_output=payload.expected_output,
            created_by=actor.id,
        )
        await db.commit()
        await db.refresh(example)
        return example
    except ValueError as error:
        await db.rollback()
        _example_error(error)


@admin_router.get("/skill-examples", response_model=list[SkillExampleAdminResponse])
async def list_examples(
    skill_key: str | None = None,
    example_status: str | None = Query(
        None, alias="status", pattern="^(CANDIDATE|PUBLISHED|RETIRED)$"
    ),
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    return await list_skill_examples(
        db, skill_key=skill_key, status=example_status, limit=200
    )


@admin_router.put(
    "/skill-examples/{example_id}/redaction",
    response_model=SkillExampleAdminResponse,
)
async def edit_example_candidate(
    example_id: int,
    payload: SkillExampleRedaction,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        row = await update_example_redaction(
            db, example_id=example_id, **payload.model_dump()
        )
        await db.commit()
        await db.refresh(row)
        return row
    except ValueError as error:
        await db.rollback()
        _example_error(error)


@admin_router.post(
    "/skill-examples/{example_id}/publish",
    response_model=SkillExampleAdminResponse,
)
async def publish_example(
    example_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    try:
        row = await publish_skill_example(db, example_id, reviewed_by=actor.id)
        await db.commit()
        await db.refresh(row)
        return row
    except ValueError as error:
        await db.rollback()
        _example_error(error)


@admin_router.post(
    "/skill-examples/{example_id}/retire",
    response_model=SkillExampleAdminResponse,
)
async def retire_example(
    example_id: int,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        row = await retire_skill_example(db, example_id)
        await db.commit()
        await db.refresh(row)
        return row
    except ValueError as error:
        await db.rollback()
        _example_error(error)


@admin_router.post(
    "/skill-examples/{example_id}/revisions",
    response_model=SkillExampleAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_example_revision_route(
    example_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    try:
        row = await create_example_revision(db, example_id, created_by=actor.id)
        await db.commit()
        await db.refresh(row)
        return row
    except ValueError as error:
        await db.rollback()
        _example_error(error)
