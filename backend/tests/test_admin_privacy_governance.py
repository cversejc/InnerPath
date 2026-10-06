import csv
import io
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.api.v1 import admin_activity, admin_dashboard, admin_exports, admin_users
from app.api.v1 import admin_support
from app.api.v1.admin_support import (
    _admin_access_details,
    _record_admin_data_access,
)
from app.api.v1.admin_user_timeline_support import build_admin_user_timeline


class SuccessfulSavepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, _error_type, _error, _traceback):
        return False


class ExportRows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


def test_admin_access_details_keep_filter_names_without_filter_values():
    details = _admin_access_details(
        page=2,
        page_size=20,
        result_count=4,
        filters={
            "search": "alice@example.invalid",
            "is_active": False,
            "status": None,
        },
    )

    assert details == {
        "page": 2,
        "page_size": 20,
        "result_count": 4,
        "filter_fields": ["is_active", "search"],
    }
    assert "alice@example.invalid" not in json.dumps(details)


@pytest.mark.asyncio
async def test_admin_data_access_audit_records_request_context_and_minimal_details():
    db = SimpleNamespace(
        add=Mock(),
        begin_nested=Mock(return_value=SuccessfulSavepoint()),
        flush=AsyncMock(),
        new=set(),
        dirty=set(),
        deleted=set(),
    )
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="request-42"),
        headers={"user-agent": "admin-test"},
    )

    await _record_admin_data_access(
        db,
        request,
        SimpleNamespace(id=7),
        action="admin.export.csv",
        resource_type="export",
        resource_id="users",
        details=_admin_access_details(
            result_count=3,
            filters={"search": "private search value"},
        ),
    )

    event = db.add.call_args.args[0]
    assert event.actor_user_id == 7
    assert event.action == "admin.export.csv"
    assert event.resource_type == "export"
    assert event.resource_id == "users"
    assert event.ip_address == "127.0.0.1"
    assert event.request_id == "request-42"
    assert json.loads(event.details) == {
        "result_count": 3,
        "filter_fields": ["search"],
    }
    assert "private search value" not in event.details


@pytest.mark.asyncio
async def test_admin_user_detail_read_is_audited(monkeypatch):
    access_events = []

    async def record_access(*_args, **kwargs):
        access_events.append(kwargs)

    monkeypatch.setattr(admin_users, "_record_admin_data_access", record_access)
    user = SimpleNamespace(id=23, name="Member")
    db = SimpleNamespace(get=AsyncMock(return_value=user))
    actor = SimpleNamespace(id=5)

    result = await admin_users.get_user(
        user_id=23,
        request=SimpleNamespace(),
        current_user=actor,
        db=db,
    )

    assert result is user
    assert access_events == [
        {
            "action": "admin.user.read",
            "resource_type": "user",
            "resource_id": "23",
            "target_user_id": 23,
        }
    ]


@pytest.mark.asyncio
async def test_admin_user_read_continues_when_access_audit_raises(monkeypatch, caplog):
    async def fail_to_record(*_args, **_kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(admin_support, "record_audit", fail_to_record)
    user = SimpleNamespace(id=23, name="Member")
    db = SimpleNamespace(get=AsyncMock(return_value=user))
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="request-43"),
        headers={"user-agent": "admin-test"},
    )

    result = await admin_users.get_user(
        user_id=23,
        request=request,
        current_user=SimpleNamespace(id=5),
        db=db,
    )

    assert result is user
    assert "Admin data access audit failed; request continues" in caplog.text


@pytest.mark.asyncio
async def test_csv_export_is_audited_without_persisting_search_values(monkeypatch):
    audit_events = []

    async def record_access(_db, _request, _actor, **kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(admin_exports, "_record_admin_data_access", record_access)
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=ExportRows(
                [
                    SimpleNamespace(
                        id=9,
                        name="=HYPERLINK(\"https://example.invalid\")",
                        phone="+123456789",
                        role="user",
                        is_active=True,
                        created_at=datetime(2026, 10, 6),
                        last_login_at=None,
                    )
                ]
            )
        )
    )

    response = await admin_exports.export_admin_resource(
        resource="users",
        request=SimpleNamespace(),
        search="private search value",
        role=None,
        is_active=None,
        record_status=None,
        user_id=None,
        action=None,
        resource_type=None,
        actor_user_id=None,
        target_user_id=None,
        ai_model=None,
        created_from=None,
        created_to=None,
        date_from=None,
        date_to=None,
        current_user=SimpleNamespace(id=5),
        db=db,
    )

    csv_rows = list(csv.reader(io.StringIO(response.body.decode("utf-8-sig"))))
    assert csv_rows[1][1].startswith("'=HYPERLINK")
    assert csv_rows[1][2].startswith("'+123456789")
    assert audit_events[0]["action"] == "admin.export.csv"
    assert audit_events[0]["resource_id"] == "users"
    assert audit_events[0]["details"]["result_count"] == 1
    assert audit_events[0]["details"]["filter_fields"] == ["search"]
    assert "private search value" not in json.dumps(audit_events[0])


@pytest.mark.asyncio
async def test_audit_log_reads_are_audited_without_persisting_search_values(monkeypatch):
    audit_events = []

    async def load_audits(*_args, **_kwargs):
        return [], 0

    async def record_access(_db, _request, _actor, **kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(admin_activity, "_load_audits", load_audits)
    monkeypatch.setattr(admin_activity, "_record_admin_data_access", record_access)

    response = await admin_activity.list_audit_logs(
        request=SimpleNamespace(),
        action=None,
        resource_type=None,
        actor_user_id=None,
        target_user_id=None,
        search="private audit search",
        date_from=None,
        date_to=None,
        page=1,
        size=50,
        current_user=SimpleNamespace(id=5),
        db=SimpleNamespace(),
    )

    assert response.total == 0
    assert audit_events[0]["action"] == "admin.audit_logs.list"
    assert audit_events[0]["details"]["filter_fields"] == ["search"]
    assert "private audit search" not in json.dumps(audit_events)


@pytest.mark.asyncio
async def test_dashboard_reads_are_audited_with_range_field_only(monkeypatch):
    audit_events = []
    response = SimpleNamespace(metrics={"user_total": 4})

    async def load_dashboard(_db, range_preset):
        assert range_preset == "7d"
        return response

    async def record_access(_db, _request, _actor, **kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(admin_dashboard, "_dashboard_data", load_dashboard)
    monkeypatch.setattr(admin_dashboard, "_record_admin_data_access", record_access)

    result = await admin_dashboard.get_dashboard_overview(
        request=SimpleNamespace(),
        range_preset="7d",
        current_user=SimpleNamespace(id=5),
        db=SimpleNamespace(),
    )

    assert result is response
    assert audit_events == [
        {
            "action": "admin.dashboard.overview.read",
            "resource_type": "dashboard",
            "resource_id": "overview",
            "details": {"filter_fields": ["range"]},
        }
    ]


def test_user_timeline_labels_privileged_reads_and_exports():
    now = datetime(2026, 10, 6, 8)
    audits = [
        (
            SimpleNamespace(
                id=81,
                action="admin.user.read",
                resource_type="user",
                resource_id="23",
                details=None,
                created_at=now,
            ),
            "管理员甲",
        ),
        (
            SimpleNamespace(
                id=82,
                action="admin.export.csv",
                resource_type="export",
                resource_id="reports",
                details='{"result_count":2}',
                created_at=now,
            ),
            "管理员乙",
        ),
    ]

    events = build_admin_user_timeline(
        user_created_at=None,
        service_requests=[],
        calendar_requests=[],
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[],
        audit_entries=audits,
    )

    assert {event["label"] for event in events} == {
        "管理员查看用户资料",
        "管理员导出管理数据",
    }
    export_event = next(event for event in events if event["resource_type"] == "export")
    assert "管理数据导出 #reports" in export_event["description"]
