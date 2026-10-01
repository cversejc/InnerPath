from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import DecisionLog
from app.domains.calendar.schemas import DecisionLogInput
from app.domains.audit.service import record_audit


async def get_user_decision_logs(
    db: AsyncSession,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[DecisionLog]:
    query = select(DecisionLog).where(DecisionLog.user_id == user_id)
    if start_date is not None:
        query = query.where(DecisionLog.log_date >= start_date)
    if end_date is not None:
        query = query.where(DecisionLog.log_date <= end_date)
    query = query.order_by(DecisionLog.log_date, DecisionLog.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_user_decision_log(
    db: AsyncSession,
    user_id: int,
    data: DecisionLogInput,
    request: Optional[Request] = None,
) -> DecisionLog:
    log = DecisionLog(user_id=user_id, **data.model_dump())
    db.add(log)
    await db.flush()
    await record_audit(
        db,
        user_id,
        "decision_log.create",
        "decision_log",
        str(log.id),
        target_user_id=user_id,
        details={"log_date": data.log_date.isoformat(), "kind": data.kind, "status": data.status},
        request=request,
    )
    await db.commit()
    await db.refresh(log)
    return log


async def delete_user_decision_log(
    db: AsyncSession,
    user_id: int,
    log_id: int,
    request: Optional[Request] = None,
) -> bool:
    result = await db.execute(
        select(DecisionLog).where(
            DecisionLog.id == log_id,
            DecisionLog.user_id == user_id,
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        return False
    await db.delete(log)
    await record_audit(
        db,
        user_id,
        "decision_log.delete",
        "decision_log",
        str(log_id),
        target_user_id=user_id,
        request=request,
    )
    await db.commit()
    return True
