from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.admin_quality_issues import list_admin_report_quality_issues
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.quality.schemas import AdminQAIssueListResponse
from app.models.user import User

router = APIRouter()


@router.get("/report-quality-issues", response_model=AdminQAIssueListResponse)
async def list_admin_report_quality_issues_route(
    issue_status: Optional[str] = Query(None, alias="status", pattern="^(OPEN|RESOLVED|ACCEPTED|DISMISSED)$"),
    severity: Optional[str] = Query(None, pattern="^(BLOCK|MAJOR|MINOR)$"),
    source_type: Optional[str] = Query(None, pattern="^(PROGRAMMATIC|VALIDATOR)$"),
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
    items, total = await list_admin_report_quality_issues(
        db,
        status=issue_status,
        severity=severity,
        source_type=source_type,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    return AdminQAIssueListResponse(total=total, page=page, size=size, items=items)
