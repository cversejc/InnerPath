from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.application.service_feedback import (
    list_admin_service_feedback,
    update_admin_service_feedback,
)
from app.application.admin_service_quality import get_admin_service_quality_summary
from app.api.v1.admin_support import _admin_access_details, _record_admin_data_access
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.feedback.schemas import (
    AdminServiceQualitySummary,
    AdminServiceFeedbackItem,
    AdminServiceFeedbackListResponse,
    AdminServiceFeedbackStateResponse,
    AdminServiceFeedbackUpdate,
)
from app.models.user import User

router = APIRouter()


@router.get("/service-feedback/summary", response_model=AdminServiceQualitySummary)
async def admin_service_quality_summary_route(
    period_days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await get_admin_service_quality_summary(db, period_days=period_days)


@router.get("/service-feedback", response_model=AdminServiceFeedbackListResponse)
async def list_admin_service_feedback_route(
    request: Request,
    feedback_status: Optional[str] = Query(None, alias="status", pattern="^(NEW|IN_PROGRESS|RESOLVED)$"),
    feedback_type: Optional[str] = Query(None, pattern="^(PRAISE|SUGGESTION|COMPLAINT)$"),
    service_type: Optional[str] = Query(None, pattern="^(report|calendar)$"),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_range_invalid")
    items, total = await list_admin_service_feedback(
        db,
        status=feedback_status,
        feedback_type=feedback_type,
        service_type=service_type,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    await _record_admin_data_access(
        db,
        request,
        current_user,
        action="admin.service_feedback.list",
        resource_type="service_feedback",
        details=_admin_access_details(
            page=page,
            page_size=size,
            result_count=len(items),
            filters={
                "status": feedback_status,
                "feedback_type": feedback_type,
                "service_type": service_type,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        ),
    )
    return AdminServiceFeedbackListResponse(
        total=total,
        page=page,
        size=size,
        items=items,
    )


@router.patch(
    "/service-feedback/{feedback_id}",
    response_model=AdminServiceFeedbackStateResponse,
)
async def update_admin_service_feedback_route(
    feedback_id: int,
    data: AdminServiceFeedbackUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        feedback = await update_admin_service_feedback(
            db,
            feedback_id=feedback_id,
            actor=current_user,
            data=data,
            audit_context=audit_context_from_request(request),
        )
        await db.commit()
        await db.refresh(feedback)
        return feedback
    except ValueError as error:
        await db.rollback()
        code = str(error)
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if code == "feedback_not_found"
                else status.HTTP_422_UNPROCESSABLE_ENTITY
                if code in {"feedback_resolution_required", "feedback_assignee_invalid"}
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=code,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="feedback_update_conflict")
