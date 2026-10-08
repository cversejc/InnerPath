from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.domains.review.schemas import ReviewPatch, ReviewVersion, ReviewCommandInput, ReviewCheckpointInput, RevisionInput, IssueResolution, IssueResolutionGroup
from app.application.node_review_workspace import review_workspace, command_data
from app.application.node_review_commands import patch_review, queue_review_command, apply_revision, approve_review, approve_checkpoint, resolve_review_issue, resolve_review_issues
from app.application.report_delivery import approve_and_deliver
from app.application.node_review_workspace import review_context, require_fingerprint
from app.domains.workflow.authorization import validate_step_actor
from app.domains.workflow.service import start_step

router = APIRouter()


async def execute(db, operation):
    try:
        return await operation
    except ValueError as error:
        await db.rollback()
        code = str(error)
        raise HTTPException(status_code=403 if code in {"report_case_forbidden", "step_specialty_required", "step_assigned_to_another_consultant"} else 404 if code.endswith("not_found") else 409, detail=code) from error


@router.get("/{case_id}/steps/{step_key}/review")
async def get_review(case_id: int, step_key: str, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    return await execute(db, review_workspace(db, case_id, step_key, actor))


@router.patch("/{case_id}/steps/{step_key}/review")
async def update_review(case_id: int, step_key: str, payload: ReviewPatch, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    await execute(db, patch_review(db, case_id, step_key, actor, payload))
    return await execute(db, review_workspace(db, case_id, step_key, actor))


@router.post("/{case_id}/steps/{step_key}/review/revisions")
async def request_revision(case_id: int, step_key: str, payload: RevisionInput, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    return command_data(await execute(db, queue_review_command(db, case_id, step_key, actor, payload, "REVISION")))


@router.post("/{case_id}/steps/{step_key}/review/revisions/{run_id}/apply")
async def accept_revision(case_id: int, step_key: str, run_id: int, payload: ReviewVersion, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    return command_data(await execute(db, apply_revision(db, case_id, step_key, run_id, actor, payload.fingerprint)))


@router.post("/{case_id}/steps/{step_key}/review/check")
async def check_review(case_id: int, step_key: str, payload: ReviewCommandInput, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    return command_data(await execute(db, queue_review_command(db, case_id, step_key, actor, payload, "CHECK")))


@router.post("/{case_id}/steps/{step_key}/review/checkpoints")
async def approve_review_checkpoint(case_id: int, step_key: str, payload: ReviewCheckpointInput, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    record = await execute(db, approve_checkpoint(db, case_id, step_key, actor, payload))
    return {"approval_id": record.id, "checkpoint_key": record.checkpoint_key, "fingerprint": record.fingerprint,
            "approved_by": record.approved_by, "approved_at": record.approved_at.isoformat()}


@router.post("/{case_id}/steps/{step_key}/review/prepare")
async def prepare_review(case_id: int, step_key: str, payload: ReviewCommandInput, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    async def operation():
        case, step, state = await review_context(db, case_id, step_key, actor)
        validate_step_actor(step, actor)
        await require_fingerprint(db, case, step, state, payload.fingerprint)
        if step.status == "READY":
            await start_step(db, case_id, step_key)
        return await queue_review_command(db, case_id, step_key, actor, payload, "PREPARE")
    return command_data(await execute(db, operation()))


@router.post("/{case_id}/steps/{step_key}/review/issues/resolve")
async def resolve_issue(case_id: int, step_key: str, payload: IssueResolution, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    await execute(db, resolve_review_issue(db, case_id, step_key, actor, payload))
    return await execute(db, review_workspace(db, case_id, step_key, actor))


@router.post("/{case_id}/steps/{step_key}/review/issues/resolve-group")
async def resolve_issue_group(case_id: int, step_key: str, payload: IssueResolutionGroup, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    await execute(db, resolve_review_issues(db, case_id, step_key, actor, payload))
    return await execute(db, review_workspace(db, case_id, step_key, actor))


@router.post("/{case_id}/steps/{step_key}/review/approve")
async def approve(case_id: int, step_key: str, payload: ReviewVersion, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    record = await execute(db, approve_review(db, case_id, step_key, actor, payload.fingerprint))
    return {"approval_id": record.id, "step_key": step_key, "fingerprint": record.fingerprint}


@router.post("/{case_id}/approve-and-deliver")
async def final_approve(case_id: int, payload: ReviewVersion, actor: User = Depends(require_roles("admin", "consultant")), db: AsyncSession = Depends(get_db)):
    version = await execute(db, approve_and_deliver(db, case_id, actor, payload.fingerprint))
    return {"report_version_id": version.id, "version_no": version.version_no, "status": "DELIVERED"}
