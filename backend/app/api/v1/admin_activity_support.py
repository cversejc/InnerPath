from datetime import date
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.v1.admin_support import _count, _date_filter
from app.domains.calendar.models import DecisionLog
from app.models.user import User
from app.domains.audit.models import AuditLog
from app.domains.audit.service import parse_audit_details


def _serialize_audit(log: AuditLog, actor_name: Optional[str] = None, target_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "details_json": parse_audit_details(log.details),
        "ip_address": log.ip_address,
        "target_user_id": log.target_user_id,
        "actor_name": actor_name,
        "target_user_name": target_name,
        "request_id": log.request_id,
        "user_agent": log.user_agent,
        "created_at": log.created_at,
    }


async def _load_audits(
    db: AsyncSession,
    *,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    actor = aliased(User)
    target = aliased(User)
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if actor_user_id is not None:
        conditions.append(AuditLog.actor_user_id == actor_user_id)
    if target_user_id is not None:
        conditions.append(AuditLog.target_user_id == target_user_id)
    conditions.extend(_date_filter(AuditLog.created_at, date_from, date_to))
    if search:
        like = f"%{search}%"
        conditions.append(or_(AuditLog.action.ilike(like), AuditLog.resource_type.ilike(like), AuditLog.resource_id.ilike(like), AuditLog.details.ilike(like), actor.name.ilike(like), target.name.ilike(like)))

    count_statement = (
        select(func.count(AuditLog.id))
        .select_from(AuditLog)
        .outerjoin(actor, AuditLog.actor_user_id == actor.id)
        .outerjoin(target, AuditLog.target_user_id == target.id)
    )
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)

    statement = (
        select(AuditLog, actor.name, target.name)
        .outerjoin(actor, AuditLog.actor_user_id == actor.id)
        .outerjoin(target, AuditLog.target_user_id == target.id)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    return [_serialize_audit(log, actor_name, target_name) for log, actor_name, target_name in rows], total


async def _load_decision_logs(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    kind: Optional[str] = None,
    log_status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    conditions = []
    if user_id is not None:
        conditions.append(DecisionLog.user_id == user_id)
    if kind:
        conditions.append(DecisionLog.kind == kind)
    if log_status:
        conditions.append(DecisionLog.status == log_status)
    if date_from:
        conditions.append(DecisionLog.log_date >= date_from)
    if date_to:
        conditions.append(DecisionLog.log_date <= date_to)
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.name.ilike(like), User.phone.ilike(like), DecisionLog.content.ilike(like)))

    count_statement = select(func.count(DecisionLog.id)).select_from(DecisionLog).join(User, DecisionLog.user_id == User.id)
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(DecisionLog, User)
        .join(User, DecisionLog.user_id == User.id)
        .order_by(DecisionLog.log_date.desc(), DecisionLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user.name,
            "log_date": log.log_date,
            "kind": log.kind,
            "status": log.status,
            "content": log.content,
            "note": log.note,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
        }
        for log, user in rows
    ], total
