"""Public Service Requests use-case facade."""

from .payloads import (
    PUBLIC_STATUS_LABELS,
    _normalize_payload,
    flatten_ai_input,
    payload_from_create,
    payload_from_update,
)
from .drafts import (
    normalize_calendar_draft,
    normalize_report_draft,
    validate_draft,
)
from .repository import _append_revision
from .users import (
    create_service_request,
    get_service_request,
    get_user_service_requests,
    resubmit_service_request,
    update_user_service_request,
    withdraw_service_request,
)
from .staff import (
    accept_service_request,
    get_workspace,
    has_staff_assignment,
    list_staff_service_requests,
    serialize_service_request,
    serialize_staff_user,
    serialize_task,
    staff_can_access,
)
from .workflow import (
    create_ai_draft_task,
    request_more_info,
    save_service_request_draft,
)

__all__ = [
    "PUBLIC_STATUS_LABELS",
    "_append_revision",
    "_normalize_payload",
    "accept_service_request",
    "create_service_request",
    "create_ai_draft_task",
    "flatten_ai_input",
    "get_service_request",
    "get_user_service_requests",
    "get_workspace",
    "has_staff_assignment",
    "list_staff_service_requests",
    "normalize_calendar_draft",
    "normalize_report_draft",
    "payload_from_create",
    "payload_from_update",
    "request_more_info",
    "save_service_request_draft",
    "serialize_service_request",
    "serialize_staff_user",
    "serialize_task",
    "staff_can_access",
    "update_user_service_request",
    "validate_draft",
    "withdraw_service_request",
    "resubmit_service_request",
]
