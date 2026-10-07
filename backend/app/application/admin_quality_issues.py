from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.report_quality import quality_state
from app.domains.quality.models import QAIssue
from app.domains.quality.schemas import AdminQAIssueItem
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import ReportCase
from app.models.user import User


async def list_admin_report_quality_issues(
    db: AsyncSession,
    *,
    status: Optional[str] = "OPEN",
    severity: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[AdminQAIssueItem], int]:
    conditions = []
    if status:
        conditions.append(QAIssue.status == status)
    if severity:
        conditions.append(QAIssue.severity == severity)
    if source_type:
        conditions.append(QAIssue.source_type == source_type)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.name.ilike(pattern),
                User.phone.ilike(pattern),
                QAIssue.message.ilike(pattern),
                QAIssue.issue_type.ilike(pattern),
                cast(QAIssue.id, String).ilike(pattern),
                cast(QAIssue.report_case_id, String).ilike(pattern),
            )
        )
    if date_from:
        conditions.append(QAIssue.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        conditions.append(
            QAIssue.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )

    base = (
        select(QAIssue, ReportCase, User, ServiceRequest)
        .join(ReportCase, ReportCase.id == QAIssue.report_case_id)
        .join(User, User.id == ReportCase.user_id)
        .outerjoin(ServiceRequest, ServiceRequest.id == ReportCase.service_request_id)
    )
    total = await db.scalar(
        select(func.count(QAIssue.id))
        .select_from(QAIssue)
        .join(ReportCase, ReportCase.id == QAIssue.report_case_id)
        .join(User, User.id == ReportCase.user_id)
        .outerjoin(ServiceRequest, ServiceRequest.id == ReportCase.service_request_id)
        .where(*conditions)
    )
    result = await db.execute(
        base.where(*conditions)
        .order_by(
            case((QAIssue.severity == "BLOCK", 0), (QAIssue.severity == "MAJOR", 1), else_=2),
            QAIssue.created_at.desc(),
            QAIssue.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = result.all()
    current_issue_ids = set()
    cases = {report_case.id: report_case for _issue, report_case, _user, _request in rows}
    for report_case in cases.values():
        state = await quality_state(db, report_case)
        current_issue_ids.update(issue.id for issue in state.issues)

    items = [
        AdminQAIssueItem(
            id=issue.id,
            is_current=issue.id in current_issue_ids,
            report_case_id=report_case.id,
            report_case_status=report_case.status,
            user_id=user.id,
            user_name=user.name,
            user_phone=user.phone,
            service_request_id=report_case.service_request_id,
            source_type=issue.source_type,
            source_ref_id=issue.source_ref_id,
            issue_type=issue.issue_type,
            severity=issue.severity,
            status=issue.status,
            target_fragment_key=issue.target_fragment_key,
            message=issue.message,
            suggestion=issue.suggestion,
            resolution=issue.resolution,
            resolved_at=issue.resolved_at,
            created_at=issue.created_at,
        )
        for issue, report_case, user, _service_request in rows
    ]
    return items, int(total or 0)
