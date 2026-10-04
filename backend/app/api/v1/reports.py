from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.domains.reports.models import Report
from app.models.user import User
from app.domains.reports.schemas import (
    LatestReportContextResponse,
    ReportListResponse,
    ReportResponse,
)
from app.domains.reports.service import (
    delete_report,
    format_report_list_item,
    format_report_response,
    get_report_by_id,
    get_user_reports,
)
from app.domains.audit.service import record_audit
from app.services.intake_service import normalize_context
from app.domains.service_requests.service import has_staff_assignment

router = APIRouter()


@router.get("", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's reports with pagination."""
    skip = (page - 1) * size
    reports, total = await get_user_reports(db, current_user.id, skip=skip, limit=size)

    return ReportListResponse(total=total, items=[format_report_list_item(report) for report in reports])


@router.get("/staff/users/{user_id}", response_model=ReportListResponse)
async def get_staff_user_reports(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "consultant":
        if not await has_staff_assignment(db, current_user.id, user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned")
    reports, total = await get_user_reports(db, user_id)
    return ReportListResponse(total=total, items=[format_report_list_item(report) for report in reports])


@router.get("/admin/users/{user_id}", response_model=ReportListResponse)
async def get_admin_user_reports(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    reports, total = await get_user_reports(db, user_id)
    return ReportListResponse(total=total, items=[format_report_list_item(report) for report in reports])


@router.get("/latest/context", response_model=LatestReportContextResponse)
async def get_latest_report_context(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id, Report.is_deleted.is_(False))
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return LatestReportContextResponse()
    snapshot = report.input_snapshot or {}
    context = snapshot.get("context")
    if not context:
        context = normalize_context(
            selected_topics=snapshot.get("selected_topics") or report.selected_topics or [],
            additional_info=snapshot.get("additional_info") or report.additional_info,
        )
    return LatestReportContextResponse(
        report_id=report.id,
        created_at=report.created_at,
        context=context,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get report details."""
    report = await get_report_by_id(db, report_id, current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return format_report_response(report)


@router.delete("/{report_id}")
async def delete_report_endpoint(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    success = await delete_report(db, report_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await record_audit(
        db,
        current_user.id,
        "report.delete",
        "report",
        str(report_id),
        target_user_id=current_user.id,
        audit_context=audit_context_from_request(request),
    )
    await db.commit()

    return {"success": True, "message": "Report deleted successfully"}
