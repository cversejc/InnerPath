from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_activity_support import _load_audits, _load_decision_logs
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.admin import AdminDecisionLogListResponse, AuditLogListResponse, AuditLogResponse

router = APIRouter()


@router.get("/decision-logs", response_model=AdminDecisionLogListResponse)
async def list_admin_decision_logs(
    user_id: Optional[int] = None,
    kind: Optional[str] = Query(None, pattern="^(action|decision)$"),
    log_status: Optional[str] = Query(None, alias="status", pattern="^(done|doing|skipped)$"),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_decision_logs(db, user_id=user_id, kind=kind, log_status=log_status, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminDecisionLogListResponse(total=total, page=page, size=size, items=items)

@router.get("/users/{user_id}/decision-logs", response_model=AdminDecisionLogListResponse)
async def list_user_decision_logs(
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    items, total = await _load_decision_logs(db, user_id=user_id, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminDecisionLogListResponse(total=total, page=page, size=size, items=items)

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=50),
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_audits(db, action=action, resource_type=resource_type, actor_user_id=actor_user_id, target_user_id=target_user_id, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AuditLogListResponse(total=total, page=page, size=size, items=[AuditLogResponse.model_validate(item) for item in items])
