import json
from datetime import date, datetime
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.calendar import CalendarEntry, DecisionLog, UserCalendar
from app.models.user import AuditLog
from app.schemas.calendar import CalendarCreate, CalendarEntryInput, CalendarUpdate, DecisionLogInput


def _validate_entries(entries: Iterable[CalendarEntryInput]) -> None:
    dates = [entry.entry_date for entry in entries]
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate_entry_date")


async def record_audit(
    db: AsyncSession,
    actor_user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
        )
    )


async def _load_calendar_entries(db: AsyncSession, calendar_id: int) -> list[CalendarEntry]:
    result = await db.execute(
        select(CalendarEntry)
        .where(CalendarEntry.calendar_id == calendar_id)
        .order_by(CalendarEntry.entry_date)
    )
    return list(result.scalars().all())


async def serialize_calendar(db: AsyncSession, calendar: UserCalendar) -> dict:
    entries = await _load_calendar_entries(db, calendar.id)
    return {
        "id": calendar.id,
        "user_id": calendar.user_id,
        "title": calendar.title,
        "start_date": calendar.start_date,
        "end_date": calendar.end_date,
        "status": calendar.status,
        "published_at": calendar.published_at,
        "entries": entries,
        "created_at": calendar.created_at,
        "updated_at": calendar.updated_at,
    }


async def create_calendar(
    db: AsyncSession,
    user_id: int,
    created_by: int,
    data: CalendarCreate,
) -> UserCalendar:
    _validate_entries(data.entries)
    calendar = UserCalendar(
        user_id=user_id,
        title=data.title,
        start_date=data.start_date,
        end_date=data.end_date,
        status="draft",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(calendar)
    await db.flush()
    for entry in data.entries:
        db.add(CalendarEntry(calendar_id=calendar.id, **entry.model_dump()))
    await record_audit(db, created_by, "calendar.create", "calendar", str(calendar.id))
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def update_calendar(
    db: AsyncSession,
    calendar: UserCalendar,
    updated_by: int,
    data: CalendarUpdate,
) -> UserCalendar:
    if data.status is not None and data.status != calendar.status:
        raise ValueError("calendar_status_transition")

    update_data = data.model_dump(exclude_unset=True, exclude={"entries", "status"})
    for field, value in update_data.items():
        setattr(calendar, field, value)
    calendar.updated_by = updated_by

    if data.entries is not None:
        _validate_entries(data.entries)
        existing_entries = await _load_calendar_entries(db, calendar.id)
        for entry in existing_entries:
            await db.delete(entry)
        await db.flush()
        for entry in data.entries:
            db.add(CalendarEntry(calendar_id=calendar.id, **entry.model_dump()))

    await record_audit(db, updated_by, "calendar.update", "calendar", str(calendar.id))
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def publish_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int) -> UserCalendar:
    if not await _load_calendar_entries(db, calendar.id):
        raise ValueError("calendar_without_entries")
    calendar.status = "published"
    calendar.published_at = datetime.utcnow()
    calendar.updated_by = updated_by
    await record_audit(db, updated_by, "calendar.publish", "calendar", str(calendar.id))
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def archive_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int) -> UserCalendar:
    calendar.status = "archived"
    calendar.updated_by = updated_by
    await record_audit(db, updated_by, "calendar.archive", "calendar", str(calendar.id))
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def get_user_calendars(
    db: AsyncSession,
    user_id: int,
    published_only: bool = True,
) -> list[dict]:
    query = select(UserCalendar).where(UserCalendar.user_id == user_id)
    if published_only:
        query = query.where(UserCalendar.status == "published")
    query = query.order_by(UserCalendar.updated_at.desc())
    result = await db.execute(query)
    calendars = result.scalars().all()
    return [await serialize_calendar(db, calendar) for calendar in calendars]


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
) -> DecisionLog:
    log = DecisionLog(user_id=user_id, **data.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def delete_user_decision_log(
    db: AsyncSession,
    user_id: int,
    log_id: int,
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
    await db.commit()
    return True


async def has_staff_assignment(db: AsyncSession, staff_id: int, user_id: int) -> bool:
    assignment = await db.execute(
        select(Booking.id).where(
            Booking.user_id == user_id,
            Booking.consultant_id == staff_id,
            Booking.status != "cancelled",
        ).limit(1)
    )
    return assignment.scalar_one_or_none() is not None


async def get_calendar_for_staff(db: AsyncSession, staff_id: int, user_id: int) -> list[dict]:
    if not await has_staff_assignment(db, staff_id, user_id):
        return []
    return await get_user_calendars(db, user_id, published_only=True)
