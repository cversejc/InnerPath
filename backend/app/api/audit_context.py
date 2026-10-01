from fastapi import Request

from app.domains.audit.context import AuditContext


def audit_context_from_request(request: Request) -> AuditContext:
    client = request.client
    return AuditContext(
        ip_address=client.host if client else None,
        request_id=getattr(request.state, "request_id", None),
        user_agent=request.headers.get("user-agent"),
    )
