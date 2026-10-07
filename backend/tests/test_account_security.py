from datetime import date
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app.api.v1 import auth_account_routes
from app.core.security import get_password_hash, verify_password
from app.dependencies import require_roles
from app.main import app
from app.domains.auth.schemas import LoginRequest, RegisterRequest, ResetPasswordRequest
from app.domains.calendar.schemas import CalendarEntryInput
from app.domains.calendar.service import _validate_entries


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


def test_auth_route_aggregator_preserves_public_paths():
    expected_routes = {
        ("/api/v1/auth/verification-code", "POST"),
        ("/api/v1/auth/register", "POST"),
        ("/api/v1/auth/password/reset", "POST"),
        ("/api/v1/auth/login", "POST"),
        ("/api/v1/auth/refresh", "POST"),
        ("/api/v1/auth/logout", "POST"),
        ("/api/v1/auth/staff/accept-invite", "POST"),
    }
    actual_routes = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}
    }

    assert expected_routes.issubset(actual_routes)


@pytest.mark.asyncio
async def test_password_reset_route_records_audit_with_request_context(monkeypatch):
    user = SimpleNamespace(id=42, phone="13800138000")

    class FakeResult:
        def scalar_one_or_none(self):
            return user

    class FakeSession:
        def __init__(self):
            self.events = []
            self.commit_count = 0

        @property
        def new(self):
            return ()

        @property
        def dirty(self):
            return ()

        @property
        def deleted(self):
            return ()

        @asynccontextmanager
        async def begin_nested(self):
            yield

        async def execute(self, _query):
            return FakeResult()

        def add(self, event):
            self.events.append(event)

        async def flush(self, _objects=None):
            return None

        async def commit(self):
            self.commit_count += 1

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/password/reset",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 1234),
            "query_string": b"",
        }
    )
    request.state.request_id = "reset-test-request"
    session = FakeSession()

    async def verify_code(*_args, **_kwargs):
        return True

    async def reset_password_with_code(*_args, **_kwargs):
        return user

    monkeypatch.setattr(auth_account_routes, "verify_code", verify_code)
    monkeypatch.setattr(auth_account_routes, "reset_password_with_code", reset_password_with_code)

    response = await auth_account_routes.reset_password(
        ResetPasswordRequest(
            phone=user.phone,
            code="123456",
            new_password="new-password-123",
        ),
        request,
        session,
    )

    assert response == {"success": True, "message": "Password reset successfully"}
    assert session.commit_count == 1
    assert len(session.events) == 1
    event = session.events[0]
    assert event.action == "auth.password.reset"
    assert event.request_id == "reset-test-request"
    assert event.ip_address == "127.0.0.1"
    assert event.user_agent == "pytest"


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
