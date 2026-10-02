from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application import service_request_delivery


@pytest.mark.asyncio
async def test_calendar_request_delivery_keeps_the_calendar_assembler(monkeypatch):
    request = SimpleNamespace(
        id=23,
        service_type="calendar",
        status="reviewing",
        user_id=42,
        request_payload={},
        updated_by=None,
    )
    actor = SimpleNamespace(id=8, role="admin")
    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    draft = SimpleNamespace(editable_payload={"title": "测试日历"})
    calendar = SimpleNamespace(id=91)
    create_calendar = AsyncMock(return_value=calendar)

    monkeypatch.setattr(service_request_delivery, "staff_can_access", lambda *_: True)
    monkeypatch.setattr(
        service_request_delivery,
        "_get_request_for_update",
        AsyncMock(return_value=request),
    )
    monkeypatch.setattr(
        service_request_delivery, "_get_draft", AsyncMock(return_value=draft)
    )
    monkeypatch.setattr(
        service_request_delivery, "_create_final_calendar", create_calendar
    )
    monkeypatch.setattr(
        service_request_delivery, "_append_revision", AsyncMock()
    )
    monkeypatch.setattr(service_request_delivery, "record_audit", AsyncMock())

    delivered = await service_request_delivery.deliver_service_request(
        db, request, actor
    )

    assert delivered.result_type == "calendar"
    assert delivered.result_id == calendar.id
    create_calendar.assert_awaited_once_with(db, request, draft, actor)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_report_with_case_is_delivered_through_case_gate(monkeypatch):
    request = SimpleNamespace(
        id=24,
        service_type="report",
        status="accepted",
        user_id=42,
        request_payload={},
    )
    report_case = SimpleNamespace(id=37)
    actor = SimpleNamespace(id=8, role="admin")
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=report_case), refresh=AsyncMock()
    )
    deliver_case = AsyncMock(return_value=None)
    legacy_draft = AsyncMock(side_effect=AssertionError("legacy report draft used"))

    monkeypatch.setattr(service_request_delivery, "staff_can_access", lambda *_: True)
    monkeypatch.setattr(
        service_request_delivery,
        "_get_request_for_update",
        AsyncMock(return_value=request),
    )
    monkeypatch.setattr(service_request_delivery, "deliver_report_case", deliver_case)
    monkeypatch.setattr(service_request_delivery, "_get_draft", legacy_draft)

    await service_request_delivery.deliver_service_request(db, request, actor)

    deliver_case.assert_awaited_once()
    assert deliver_case.await_args.kwargs["report_case"] is report_case
    legacy_draft.assert_not_awaited()
