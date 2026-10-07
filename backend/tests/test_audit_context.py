from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.api.audit_context import audit_context_from_request
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit


class SuccessfulSavepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, _exception_type, _exception, _traceback):
        return False


def test_audit_context_from_request_extracts_metadata():
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="request-123"),
        headers={"user-agent": "InnerPath test client"},
    )

    context = audit_context_from_request(request)

    assert context == AuditContext(
        ip_address="127.0.0.1",
        request_id="request-123",
        user_agent="InnerPath test client",
    )


@pytest.mark.asyncio
async def test_record_audit_uses_context_metadata():
    db = SimpleNamespace(
        add=Mock(),
        begin_nested=Mock(return_value=SuccessfulSavepoint()),
        flush=AsyncMock(),
        new=set(),
        dirty=set(),
        deleted=set(),
    )
    context = AuditContext(
        ip_address="127.0.0.1",
        request_id="request-123",
        user_agent="InnerPath test client",
    )

    event = await record_audit(
        db,
        actor_user_id=5,
        action="user.profile.update",
        resource_type="user",
        resource_id="5",
        audit_context=context,
    )

    assert event.ip_address == "127.0.0.1"
    assert event.request_id == "request-123"
    assert event.user_agent == "InnerPath test client"
    db.add.assert_called_once_with(event)
    db.begin_nested.assert_called_once_with()
    db.flush.assert_awaited_once_with([event])


@pytest.mark.asyncio
async def test_audit_insert_failure_does_not_abort_business_transaction():
    class Savepoint:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            self.db.in_savepoint = True

        async def __aexit__(self, exception_type, _exception, _traceback):
            self.db.in_savepoint = False
            if exception_type:
                self.db.audit_rows.clear()
            return False

    class FakeSession:
        new = set()
        dirty = set()
        deleted = set()

        def __init__(self):
            self.business_rows = ["business change already flushed"]
            self.audit_rows = []
            self.in_savepoint = False

        def begin_nested(self):
            return Savepoint(self)

        def add(self, event):
            self.audit_rows.append(event)

        async def flush(self, objects=None):
            if objects:
                raise RuntimeError("simulated audit constraint failure")

    db = FakeSession()

    event = await record_audit(
        db,
        actor_user_id=5,
        action="user.profile.update",
        resource_type="user",
        resource_id="5",
    )

    assert event.action == "user.profile.update"
    assert db.business_rows == ["business change already flushed"]
    assert db.audit_rows == []
    assert db.in_savepoint is False


@pytest.mark.asyncio
async def test_business_flush_failure_is_not_hidden_as_an_audit_failure():
    db = SimpleNamespace(
        add=Mock(),
        begin_nested=Mock(),
        flush=AsyncMock(side_effect=RuntimeError("business constraint failure")),
        new={object()},
        dirty=set(),
        deleted=set(),
    )

    with pytest.raises(RuntimeError, match="business constraint failure"):
        await record_audit(
            db,
            actor_user_id=5,
            action="user.profile.update",
            resource_type="user",
            resource_id="5",
        )

    db.begin_nested.assert_not_called()
    db.add.assert_not_called()
