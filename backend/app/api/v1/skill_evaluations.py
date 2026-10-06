from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.skill_evaluation import (
    get_evaluation_batch,
    list_evaluation_batches,
    list_evaluation_cases,
    start_evaluation_batch,
)
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.skills.schemas import (
    SkillEvaluationBatchResponse,
    SkillEvaluationCaseResponse,
    SkillEvaluationCreate,
)
from app.models.user import User


router = APIRouter()


def _evaluation_error(error: ValueError) -> None:
    code = str(error)
    if code in {"skill_version_not_found", "skill_evaluation_batch_not_found"}:
        raise HTTPException(status_code=404, detail=code)
    if code == "skill_version_retired":
        raise HTTPException(status_code=409, detail=code)
    if code.startswith("skill_"):
        raise HTTPException(status_code=422, detail=code)
    raise HTTPException(status_code=400, detail=code)


@router.get("/skill-evaluation-cases", response_model=list[SkillEvaluationCaseResponse])
async def get_regression_cases(
    skill_key: str | None = None,
    _actor: User = Depends(require_roles("admin")),
):
    return list_evaluation_cases(skill_key=skill_key)


@router.post(
    "/skill-versions/{version_id}/evaluations",
    response_model=SkillEvaluationBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_skill_evaluation(
    version_id: int,
    payload: SkillEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        return await start_evaluation_batch(
            db, version_id=version_id, case_keys=payload.case_keys
        )
    except ValueError as error:
        await db.rollback()
        _evaluation_error(error)


@router.get(
    "/skill-evaluations/{batch_id}", response_model=SkillEvaluationBatchResponse
)
async def get_skill_evaluation(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    try:
        return await get_evaluation_batch(db, batch_id)
    except ValueError as error:
        _evaluation_error(error)


@router.get(
    "/skill-versions/{version_id}/evaluations",
    response_model=list[SkillEvaluationBatchResponse],
)
async def list_skill_evaluations(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    _actor: User = Depends(require_roles("admin")),
):
    return await list_evaluation_batches(db, version_id=version_id)
