from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarEntry, UserCalendar
from app.domains.calendar.schemas import (
    CalendarCreate,
    CalendarEntryInput,
    CalendarUpdate,
)
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.calendar.query_service import load_calendar_entries


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


async def create_calendar(
    db: AsyncSession,
    user_id: int,
    created_by: int,
    data: CalendarCreate,
    audit_context: Optional[AuditContext] = None,
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
        meta_payload=data.meta_payload,
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar



async def update_calendar(
    db: AsyncSession,
    calendar: UserCalendar,
    updated_by: int,
    data: CalendarUpdate,
    audit_context: Optional[AuditContext] = None,
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
        entries_for_validation = await load_calendar_entries(db, calendar.id)
    _validate_entries(entries_for_validation, next_start_date, next_end_date)
    for field, value in update_data.items():
        setattr(calendar, field, value)
    calendar.updated_by = updated_by

    if data.entries is not None:
        existing_entries = await load_calendar_entries(db, calendar.id)
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def clone_calendar_as_draft(
    db: AsyncSession,
    calendar: UserCalendar,
    created_by: int,
    audit_context: Optional[AuditContext] = None,
) -> UserCalendar:
    entries = await load_calendar_entries(db, calendar.id)
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
        meta_payload=calendar.meta_payload,
        created_by=created_by,
        updated_by=created_by,
        calendar_request_id=calendar.calendar_request_id,
        source_report_id=calendar.source_report_id,
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(draft)
    return draft


async def publish_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int, audit_context: Optional[AuditContext] = None) -> UserCalendar:
    entries = await load_calendar_entries(db, calendar.id)
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def archive_calendar(db: AsyncSession, calendar: UserCalendar, updated_by: int, audit_context: Optional[AuditContext] = None) -> UserCalendar:
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar)
    return calendar
