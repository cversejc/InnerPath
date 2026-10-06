"""Common date, count, and lookup helpers for admin routes."""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.domains.audit.service import record_audit
from app.domains.calendar.models import UserCalendar
from app.models.user import User


USER_ROLE_LABELS = {"user": "用户", "consultant": "咨询师", "admin": "管理员"}
REPORT_STATUS_LABELS = {"processing": "生成中", "completed": "已完成", "failed": "失败"}
CALENDAR_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc
logger = logging.getLogger(__name__)


def _admin_access_details(
    *,
    page: int | None = None,
    page_size: int | None = None,
    result_count: int | None = None,
    filters: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = {
        key: value
        for key, value in (
            ("page", page),
            ("page_size", page_size),
            ("result_count", result_count),
        )
        if value is not None
    }
    filter_fields = sorted(
        key for key, value in (filters or {}).items() if value is not None and value != ""
    )
    if filter_fields:
        details["filter_fields"] = filter_fields
    if metadata:
        details.update(metadata)
    return details


async def _record_admin_data_access(
    db: AsyncSession,
    request: Request,
    actor: User,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    target_user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    try:
        await record_audit(
            db,
            actor.id,
            action,
            resource_type,
            resource_id,
            target_user_id=target_user_id,
            details=details,
            audit_context=audit_context_from_request(request),
        )
    except Exception as error:
        logger.warning(
            "Admin data access audit failed; request continues "
            "(action=%s resource_type=%s resource_id=%s error_type=%s)",
            action,
            resource_type,
            resource_id,
            type(error).__name__,
        )


def _db_start(date_value: date) -> datetime:
    return datetime.combine(date_value, time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)


def _db_end(date_value: date) -> datetime:
    return datetime.combine(date_value + timedelta(days=1), time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)


async def _count(db: AsyncSession, statement) -> int:
    return int((await db.scalar(statement)) or 0)


def _date_filter(column, date_from: Optional[date], date_to: Optional[date]):
    conditions = []
    if date_from:
        conditions.append(column >= _db_start(date_from))
    if date_to:
        conditions.append(column < _db_end(date_to))
    return conditions


async def _get_calendar_or_404(db: AsyncSession, calendar_id: int) -> UserCalendar:
    calendar = await db.get(UserCalendar, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar
