from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.api.v1.admin_support import _get_calendar_or_404
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.domains.calendar.schemas import (
    CalendarCreate,
    CalendarImportRequest,
    CalendarListResponse,
    CalendarResponse,
    CalendarUpdate,
    AdminCalendarRequestListResponse,
)
from app.domains.audit.service import record_audit
from app.domains.calendar.service import (
    archive_calendar,
    clone_calendar_as_draft,
    create_calendar,
    publish_calendar,
    update_calendar,
)
from app.domains.calendar.query_service import get_user_calendars, serialize_calendar
from app.domains.calendar.requests import get_calendar_requests_for_admin

router = APIRouter()


@router.get("/calendar-requests", response_model=AdminCalendarRequestListResponse)
async def list_admin_calendar_requests(
    request_status: str | None = Query(None, alias="status", max_length=30),
    user_id: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_calendar_requests_for_admin(
        db,
        status_filter=request_status,
        user_id=user_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    return AdminCalendarRequestListResponse(**result)


@router.get("/users/{user_id}/calendars", response_model=CalendarListResponse)
async def list_user_calendars(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return CalendarListResponse(items=await get_user_calendars(db, user_id, published_only=False))

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
        calendar = await create_calendar(
            db,
            user_id,
            current_user.id,
            data,
            audit_context=audit_context_from_request(request),
        )
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
            audit_context=audit_context_from_request(request),
        )
        await record_audit(
            db,
            current_user.id,
            "calendar.import",
            "calendar",
            str(calendar.id),
            target_user_id=data.user_id,
            details={"entry_count": len(data.entries)},
            audit_context=audit_context_from_request(request),
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
    draft = await clone_calendar_as_draft(
        db,
        calendar,
        current_user.id,
        audit_context=audit_context_from_request(request),
    )
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
        calendar = await update_calendar(
            db,
            calendar,
            current_user.id,
            data,
            audit_context=audit_context_from_request(request),
        )
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
        calendar = await publish_calendar(
            db,
            calendar,
            current_user.id,
            audit_context=audit_context_from_request(request),
        )
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
    calendar = await archive_calendar(
        db,
        calendar,
        current_user.id,
        audit_context=audit_context_from_request(request),
    )
    return await serialize_calendar(db, calendar)
