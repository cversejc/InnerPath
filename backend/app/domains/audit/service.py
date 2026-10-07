"""Structured business audit helpers.

Audit events are deliberately kept separate from application log files. The
former are queryable business facts, while the latter remain useful for
diagnosing infrastructure and programming errors.
"""

import json
import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.context import AuditContext
from app.domains.audit.models import AuditLog

logger = logging.getLogger(__name__)


_SECRET_KEYS = {
    "password",
    "current_password",
    "new_password",
    "token",
    "access_token",
    "refresh_token",
    "token_hash",
    "password_hash",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "set_cookie",
    "secret",
    "prompt",
    "ai_prompt",
    "raw_prompt",
}


def _safe_value(value: Any, key: Optional[str] = None) -> Any:
    normalized_key = key.lower().replace("-", "_") if key else None
    if normalized_key and normalized_key in _SECRET_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(child_key): _safe_value(child_value, str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return value


def parse_audit_details(details: Optional[str]) -> Optional[dict[str, Any]]:
    if not details:
        return None
    try:
        parsed = json.loads(details)
    except (TypeError, ValueError):
        return {"message": details}
    if isinstance(parsed, dict):
        return _safe_value(parsed)
    return {"value": _safe_value(parsed)}


async def record_audit(
    db: AsyncSession,
    actor_user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    target_user_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
    audit_context: Optional[AuditContext] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Best-effort add an audit event without aborting business writes.

    Existing business changes are flushed first so their errors remain visible
    to the caller. The audit insert then runs inside a savepoint; recoverable
    audit-row failures roll back only that savepoint and are logged.
    """

    context_ip = audit_context.ip_address if audit_context else None
    client_ip = context_ip or ip_address
    resolved_request_id = request_id or (audit_context.request_id if audit_context else None)
    resolved_user_agent = user_agent or (audit_context.user_agent if audit_context else None)
    event = AuditLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(_safe_value(details), ensure_ascii=False) if details is not None else None,
        ip_address=client_ip,
        request_id=resolved_request_id[:64] if resolved_request_id else None,
        user_agent=resolved_user_agent[:500] if resolved_user_agent else None,
    )
    if db.new or db.dirty or db.deleted:
        await db.flush()

    try:
        async with db.begin_nested():
            db.add(event)
            await db.flush([event])
    except Exception as error:
        logger.warning(
            "Audit write failed; business operation continues "
            "(action=%s resource_type=%s resource_id=%s error_type=%s)",
            action,
            resource_type,
            resource_id,
            type(error).__name__,
        )
    return event
