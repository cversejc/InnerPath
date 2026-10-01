from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.api.audit_context import audit_context_from_request
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit


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
    db = SimpleNamespace(add=Mock())
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
