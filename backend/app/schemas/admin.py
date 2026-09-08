from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(user|consultant|admin)$")


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminUserListItem(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    user_type: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserListItem]


class AdminBookingListResponse(BaseModel):
    total: int
    items: list


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogResponse]
