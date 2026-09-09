from datetime import date

import pytest

from app.api.v1.admin import _dashboard_range
from app.models.calendar import UserCalendar
from app.schemas.calendar import CalendarEntryInput
from app.schemas.admin import AdminReportTaskResponse
from app.services.audit_service import _safe_value, parse_audit_details
from app.services.booking_service import BOOKING_STATUS_TRANSITIONS
from app.services.calendar_service import _validate_entries


def test_dashboard_ranges_have_expected_number_of_days():
    for preset, expected_days in (("7d", 7), ("30d", 30), ("90d", 90)):
        start_date, end_date = _dashboard_range(preset)
        assert (end_date - start_date).days + 1 == expected_days


def test_dashboard_rejects_unknown_range():
    with pytest.raises(Exception):
        _dashboard_range("14d")


def test_calendar_entries_validate_range_and_duplicates():
    entries = [CalendarEntryInput(entry_date=date(2026, 9, 7), keyword="观察")]

    with pytest.raises(ValueError, match="invalid_calendar_range"):
        _validate_entries(entries, date(2026, 9, 8), date(2026, 9, 7))
    with pytest.raises(ValueError, match="entry_outside_calendar_range"):
        _validate_entries(entries, date(2026, 9, 8), date(2026, 9, 9))


def test_calendar_model_declares_series_version_constraint():
    constraint_names = {constraint.name for constraint in UserCalendar.__table__.constraints}
    assert "uq_user_calendar_series_version" in constraint_names


def test_booking_status_transitions_are_forward_only():
    assert "completed" in BOOKING_STATUS_TRANSITIONS["confirmed"]
    assert "pending" not in BOOKING_STATUS_TRANSITIONS["completed"]
    assert "confirmed" not in BOOKING_STATUS_TRANSITIONS["cancelled"]


def test_audit_details_redact_secrets_and_parse_legacy_text():
    safe = _safe_value({"password": "secret", "nested": {"token": "raw", "ok": "kept"}})
    assert safe == {"password": "[REDACTED]", "nested": {"token": "[REDACTED]", "ok": "kept"}}
    assert parse_audit_details("legacy detail") == {"message": "legacy detail"}


def test_report_task_response_exposes_retry_capability_without_snapshot():
    payload = AdminReportTaskResponse(
        task_id="task-1",
        user_id=1,
        status="failed",
        progress=0,
        created_at="2026-09-09T00:00:00",
        updated_at="2026-09-09T00:00:00",
    )
    assert payload.has_input_snapshot is False
