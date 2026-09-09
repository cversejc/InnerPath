from datetime import date, datetime
from typing import Iterable, Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.calendar import CalendarEntry, DecisionLog, UserCalendar
from app.schemas.calendar import CalendarCreate, CalendarEntryInput, CalendarUpdate, DecisionLogInput
from app.services.audit_service import record_audit


def _validate_entries(
    entries: Iterable[CalendarEntryInput],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> None:
    dates = [entry.entry_date for entry in entries]
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate_entry_date")
    if start_date and end_date and start_date > end_date:
        raise ValueError("invalid_calendar_range")
    if start_date and any(entry_date < start_date for entry_date in dates):
        raise ValueError("entry_outside_calendar_range")
    if end_date and any(entry_date > end_date for entry_date in dates):
        raise ValueError("entry_outside_calendar_range")


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
        "series_id": calendar.series_id,
        "version_number": calendar.version_number,
        "is_current": calendar.status == "published",
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
    request: Optional[Request] = None,
) -> UserCalendar:
    _validate_entries(data.entries, data.start_date, data.end_date)
    calendar = UserCalendar(
        user_id=user_id,
        series_id=str(uuid4()),
        version_number=1,
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
    await record_audit(
        db,
        created_by,
        "calendar.create",
        "calendar",
        str(calendar.id),
        target_user_id=user_id,
        details={"version_number": calendar.version_number, "entry_count": len(data.entries)},
        request=request,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def update_calendar(
    db: AsyncSession,
    calendar: UserCalendar,
    updated_by: int,
    data: CalendarUpdate,
    request: Optional[Request] = None,
) -> UserCalendar:
    if calendar.status != "draft":
        raise ValueError("published_calendar_requires_revision")
    if data.status is not None and data.status != calendar.status:
        raise ValueError("calendar_status_transition")

    update_data = data.model_dump(exclude_unset=True, exclude={"entries", "status"})
    next_start_date = update_data.get("start_date", calendar.start_date)
    next_end_date = update_data.get("end_date", calendar.end_date)
    entries_for_validation = data.entries
    if entries_for_validation is None:
        entries_for_validation = await _load_calendar_entries(db, calendar.id)
    _validate_entries(entries_for_validation, next_start_date, next_end_date)
    for field, value in update_data.items():
        setattr(calendar, field, value)
    calendar.updated_by = updated_by

    if data.entries is not None:
        existing_entries = await _load_calendar_entries(db, calendar.id)
        for entry in existing_entries:
            await db.delete(entry)
        await db.flush()
        for entry in data.entries:
            db.add(CalendarEntry(calendar_id=calendar.id, **entry.model_dump()))

    await record_audit(
        db,
        updated_by,
        "calendar.update",
        "calendar",
        str(calendar.id),
        target_user_id=calendar.user_id,
        details={"version_number": calendar.version_number, "entry_count": len(data.entries) if data.entries is not None else None},
        request=request,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def clone_calendar_as_draft(
    db: AsyncSession,
    calendar: UserCalendar,
    created_by: int,
    request: Optional[Request] = None,
) -> UserCalendar:
    entries = await _load_calendar_entries(db, calendar.id)
    max_version = await db.scalar(
        select(func.max(UserCalendar.version_number)).where(UserCalendar.series_id == calendar.series_id)
    )
    draft = UserCalendar(
        user_id=calendar.user_id,
        series_id=calendar.series_id,
        version_number=(max_version or calendar.version_number or 0) + 1,
        title=calendar.title,
        start_date=calendar.start_date,
        end_date=calendar.end_date,
        status="draft",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(draft)
    await db.flush()
    for entry in entries:
        db.add(
            CalendarEntry(
                calendar_id=draft.id,
                entry_date=entry.entry_date,
                day_pillar=entry.day_pillar,
                tone=entry.tone,
                status_label=entry.status_label,
                keyword=entry.keyword,
                summary=entry.summary,
                suitable=entry.suitable or [],
                unsuitable=entry.unsuitable or [],
                time_window=entry.time_window,
                admin_note=entry.admin_note,
            )
        )
    await record_audit(
        db,
        created_by,
        "calendar.revision.create",
        "calendar",
        str(draft.id),
        target_user_id=calendar.user_id,
        details={"source_calendar_id": calendar.id, "version_number": draft.version_number},
        request=request,
    )
    await db.commit()
    await db.refresh(draft)
    return draft


async def publish_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int, request: Optional[Request] = None) -> UserCalendar:
    entries = await _load_calendar_entries(db, calendar.id)
    if not entries:
        raise ValueError("calendar_without_entries")
    if calendar.status == "archived":
        raise ValueError("archived_calendar_cannot_publish")
    if calendar.status == "published":
        return calendar
    _validate_entries(entries, calendar.start_date, calendar.end_date)
    previous = await db.execute(
        select(UserCalendar).where(
            UserCalendar.series_id == calendar.series_id,
            UserCalendar.status == "published",
            UserCalendar.id != calendar.id,
        )
    )
    for old_calendar in previous.scalars().all():
        old_calendar.status = "archived"
        old_calendar.updated_by = updated_by
    calendar.status = "published"
    calendar.published_at = datetime.utcnow()
    calendar.updated_by = updated_by
    await record_audit(
        db,
        updated_by,
        "calendar.publish",
        "calendar",
        str(calendar.id),
        target_user_id=calendar.user_id,
        details={"version_number": calendar.version_number},
        request=request,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def archive_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int, request: Optional[Request] = None) -> UserCalendar:
    calendar.status = "archived"
    calendar.updated_by = updated_by
    await record_audit(
        db,
        updated_by,
        "calendar.archive",
        "calendar",
        str(calendar.id),
        target_user_id=calendar.user_id,
        details={"version_number": calendar.version_number},
        request=request,
    )
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
