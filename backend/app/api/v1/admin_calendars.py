from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import _get_calendar_or_404
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.calendar import CalendarRequest
from app.models.user import User
from app.schemas.calendar import (
    CalendarCreate,
    CalendarImportRequest,
    CalendarListResponse,
    CalendarRequestAdminUpdate,
    CalendarRequestListResponse,
    CalendarRequestResponse,
    CalendarResponse,
    CalendarUpdate,
)
from app.services.audit_service import record_audit
from app.services.calendar_service import (
    archive_calendar,
    clone_calendar_as_draft,
    create_calendar,
    get_calendar_requests_for_admin,
    get_user_calendars,
    publish_calendar,
    serialize_calendar,
    update_calendar,
    update_calendar_request,
)

router = APIRouter()


@router.get("/users/{user_id}/calendars", response_model=CalendarListResponse)
async def list_user_calendars(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return CalendarListResponse(items=await get_user_calendars(db, user_id, published_only=False))

@router.get("/calendar-requests", response_model=CalendarRequestListResponse)
async def list_calendar_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[int] = Query(None, ge=1),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items = await get_calendar_requests_for_admin(db, status_filter=status_filter, user_id=user_id)
    return CalendarRequestListResponse(items=items)

@router.patch("/calendar-requests/{request_id}", response_model=CalendarRequestResponse)
async def review_calendar_request(
    request_id: int,
    data: CalendarRequestAdminUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar_request = await db.get(CalendarRequest, request_id)
    if not calendar_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar request not found")
    try:
        return await update_calendar_request(db, calendar_request, current_user.id, data, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

@router.post("/users/{user_id}/calendars", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_user_calendar(
    user_id: int,
    data: CalendarCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        calendar = await create_calendar(db, user_id, current_user.id, data, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)

@router.post("/calendars/import", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def import_calendar(
    data: CalendarImportRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, data.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        calendar = await create_calendar(
            db,
            data.user_id,
            current_user.id,
            CalendarCreate(title=data.title, start_date=data.start_date, end_date=data.end_date, entries=data.entries),
            request=request,
        )
        await record_audit(
            db,
            current_user.id,
            "calendar.import",
            "calendar",
            str(calendar.id),
            target_user_id=data.user_id,
            details={"entry_count": len(data.entries)},
            request=request,
        )
        await db.commit()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)

@router.post("/calendars/{calendar_id}/draft", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_draft(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    draft = await clone_calendar_as_draft(db, calendar, current_user.id, request=request)
    return await serialize_calendar(db, draft)

@router.put("/calendars/{calendar_id}", response_model=CalendarResponse)
async def update_user_calendar(
    calendar_id: int,
    data: CalendarUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    try:
        calendar = await update_calendar(db, calendar, current_user.id, data, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)

@router.post("/calendars/{calendar_id}/publish", response_model=CalendarResponse)
async def publish_user_calendar(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    try:
        calendar = await publish_calendar(db, calendar, current_user.id, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)

@router.post("/calendars/{calendar_id}/archive", response_model=CalendarResponse)
async def archive_user_calendar(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    calendar = await archive_calendar(db, calendar, current_user.id, request=request)
    return await serialize_calendar(db, calendar)
