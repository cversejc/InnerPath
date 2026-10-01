from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditContext:
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    user_agent: Optional[str] = None
