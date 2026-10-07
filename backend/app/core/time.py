"""Shared time rules for the application.

Database timestamp columns are currently PostgreSQL timestamp-without-timezone
values. They are stored as UTC-naive values for compatibility with the
existing schema, while API timestamps are serialized with an explicit
Shanghai offset.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
SHANGHAI = ZoneInfo("Asia/Shanghai")


def utc_now() -> datetime:
    """Return the current instant as an aware UTC datetime."""
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """Return the current instant in the database's UTC-naive representation."""
    return utc_now().replace(tzinfo=None)


def shanghai_now() -> datetime:
    """Return the current instant rendered in Shanghai time."""
    return utc_now().astimezone(SHANGHAI)


def shanghai_today() -> date:
    return shanghai_now().date()


def shanghai_date_for(value: datetime | None) -> date | None:
    """Return the Shanghai calendar date for a stored or aware datetime."""
    if value is None:
        return None
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(SHANGHAI).date()


def utc_naive_for_shanghai_date(value: date, *, end: bool = False) -> datetime:
    """Convert a Shanghai calendar boundary to a UTC-naive database value."""
    boundary = datetime.combine(value + timedelta(days=1) if end else value, time.min, tzinfo=SHANGHAI)
    return boundary.astimezone(UTC).replace(tzinfo=None)


def api_datetime(value: datetime | None) -> str | None:
    """Serialize a database or application datetime with a Shanghai offset."""
    if value is None:
        return None
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(SHANGHAI).isoformat(timespec="seconds")


def utc_now_iso() -> str:
    """Return an explicit UTC ISO timestamp for JSON payloads and snapshots."""
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")
