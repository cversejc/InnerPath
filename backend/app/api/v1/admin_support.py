"""Common date, count, and lookup helpers for admin routes."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import UserCalendar


USER_ROLE_LABELS = {"user": "用户", "consultant": "咨询师", "admin": "管理员"}
REPORT_STATUS_LABELS = {"processing": "生成中", "completed": "已完成", "failed": "失败"}
CALENDAR_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc


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
