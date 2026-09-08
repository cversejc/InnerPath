from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import get_password_hash, verify_password
from app.dependencies import require_roles
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.calendar import CalendarEntryInput
from app.services.calendar_service import _validate_entries


def test_passwords_are_stored_as_verifiable_hashes():
    password = "secure-password-123"
    password_hash = get_password_hash(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_auth_schemas_require_eleven_digit_phone_numbers():
    with pytest.raises(ValidationError):
        LoginRequest(phone="1380013800a", password="secure-password-123")

    request = RegisterRequest(
        phone="13800138000",
        password="secure-password-123",
        name="测试用户",
    )
    assert request.phone == "13800138000"
    assert "code" not in request.model_dump()


@pytest.mark.asyncio
async def test_role_dependency_rejects_non_matching_role():
    dependency = require_roles("admin")
    user = SimpleNamespace(role="user", is_active=True)

    with pytest.raises(HTTPException) as error:
        await dependency(user)

    assert error.value.status_code == 403


def test_calendar_entries_reject_duplicate_dates():
    entries = [
        CalendarEntryInput(entry_date=date(2026, 9, 7), keyword="观察"),
        CalendarEntryInput(entry_date=date(2026, 9, 7), keyword="复盘"),
    ]

    with pytest.raises(ValueError, match="duplicate_entry_date"):
        _validate_entries(entries)
