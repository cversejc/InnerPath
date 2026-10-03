from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import service_request_staff_routes


@pytest.mark.asyncio
async def test_assigned_consultant_can_load_staff_request_workspace(monkeypatch):
    request = SimpleNamespace(id=12, service_type="calendar", assigned_consultant_id=4)
    workspace = {"request": {}, "user": {}, "draft": None, "task": None}
    monkeypatch.setattr(
        service_request_staff_routes,
        "get_service_request",
        AsyncMock(return_value=request),
    )
    monkeypatch.setattr(
        service_request_staff_routes, "get_workspace", AsyncMock(return_value=workspace)
    )
    monkeypatch.setattr(service_request_staff_routes, "_workspace_response", lambda value: value)

    result = await service_request_staff_routes.get_staff_request_workspace(
        12,
        current_user=SimpleNamespace(id=4, role="consultant"),
        db=AsyncMock(),
    )

    assert result is workspace


@pytest.mark.asyncio
async def test_unassigned_consultant_cannot_load_staff_request_workspace(monkeypatch):
    request = SimpleNamespace(id=12, service_type="calendar", assigned_consultant_id=8)
    monkeypatch.setattr(
        service_request_staff_routes,
        "get_service_request",
        AsyncMock(return_value=request),
    )

    with pytest.raises(HTTPException) as error:
        await service_request_staff_routes.get_staff_request_workspace(
            12,
            current_user=SimpleNamespace(id=4, role="consultant"),
            db=AsyncMock(),
        )

    assert error.value.status_code == 403
