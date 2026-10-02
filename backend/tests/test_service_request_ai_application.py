from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.application import service_request_ai
from app.tasks import service_request_dispatch


@pytest.mark.asyncio
async def test_start_dispatches_new_ai_task(monkeypatch):
    task = SimpleNamespace(request_id=17, task_id="task-17")
    create_task = AsyncMock(return_value=(task, True))
    dispatch_task = Mock()
    monkeypatch.setattr(service_request_ai, "create_ai_draft_task", create_task)
    monkeypatch.setattr(
        service_request_ai, "ensure_legacy_report_request", AsyncMock()
    )

    result = await service_request_ai.start_service_request_ai_draft(
        None,
        None,
        None,
        dispatch_task=dispatch_task,
    )

    assert result is task
    dispatch_task.assert_called_once_with(17, "task-17")


@pytest.mark.asyncio
async def test_start_does_not_redispatch_active_ai_task(monkeypatch):
    task = SimpleNamespace(request_id=17, task_id="task-17")
    create_task = AsyncMock(return_value=(task, False))
    dispatch_task = Mock()
    monkeypatch.setattr(service_request_ai, "create_ai_draft_task", create_task)
    monkeypatch.setattr(
        service_request_ai, "ensure_legacy_report_request", AsyncMock()
    )

    result = await service_request_ai.start_service_request_ai_draft(
        None,
        None,
        None,
        dispatch_task=dispatch_task,
    )

    assert result is task
    dispatch_task.assert_not_called()


def test_dispatch_adapter_sends_registered_celery_task(monkeypatch):
    send_task = Mock()
    monkeypatch.setattr(service_request_dispatch, "celery_app", SimpleNamespace(send_task=send_task))

    service_request_dispatch.dispatch_service_request_draft(17, "task-17")

    send_task.assert_called_once_with(
        "generate_service_request_draft",
        args=[17],
        task_id="task-17",
    )
