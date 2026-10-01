from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarEntry, UserCalendar


async def load_calendar_entries(
    db: AsyncSession, calendar_id: int
) -> list[CalendarEntry]:
    result = await db.execute(
        select(CalendarEntry)
        .where(CalendarEntry.calendar_id == calendar_id)
        .order_by(CalendarEntry.entry_date)
    )
    return list(result.scalars().all())


async def serialize_calendar(
    db: AsyncSession,
    calendar: UserCalendar,
    *,
    include_internal: bool = True,
) -> dict:
    entries = await load_calendar_entries(db, calendar.id)
    if not include_internal:
        entries = [
            {
                "id": entry.id,
                "entry_date": entry.entry_date,
                "day_pillar": entry.day_pillar,
                "tone": entry.tone,
                "status_label": entry.status_label,
                "keyword": entry.keyword,
                "summary": entry.summary,
                "suitable": entry.suitable or [],
                "unsuitable": entry.unsuitable or [],
                "time_window": entry.time_window,
                "admin_note": None,
            }
            for entry in entries
        ]
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
        "meta_payload": calendar.meta_payload,
        "calendar_request_id": calendar.calendar_request_id,
        "published_at": calendar.published_at,
        "entries": entries,
        "created_at": calendar.created_at,
        "updated_at": calendar.updated_at,
    }


async def get_user_calendars(
    db: AsyncSession,
    user_id: int,
    published_only: bool = True,
    *,
    include_internal: bool = True,
) -> list[dict]:
    query = select(UserCalendar).where(UserCalendar.user_id == user_id)
    if published_only:
        query = query.where(UserCalendar.status == "published")
    query = query.order_by(UserCalendar.updated_at.desc())
    result = await db.execute(query)
    calendars = result.scalars().all()
    return [
        await serialize_calendar(db, calendar, include_internal=include_internal)
        for calendar in calendars
    ]
