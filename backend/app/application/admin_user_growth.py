"""Read-only user conversion and return-activity metrics for admin overview."""

from datetime import date, datetime

from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarRequest
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.schemas.admin import AdminUserGrowthChannel, AdminUserGrowthSummary


def _report_cohort_users(start_at: datetime, end_at: datetime):
    return (
        select(
            ServiceRequest.user_id.label("user_id"),
            func.max(
                case((ServiceRequest.status == "delivered", 1), else_=0)
            ).label("delivered"),
        )
        .join(User, User.id == ServiceRequest.user_id)
        .where(
            ServiceRequest.service_type == "report",
            ServiceRequest.created_at >= User.created_at,
            ServiceRequest.created_at < end_at,
            User.role == "user",
            User.created_at >= start_at,
        )
        .group_by(ServiceRequest.user_id)
        .subquery("report_cohort_users")
    )


def _calendar_cohort_users(start_at: datetime, end_at: datetime):
    return (
        select(
            CalendarRequest.user_id.label("user_id"),
            func.max(
                case(
                    (CalendarRequest.status.in_(("fulfilled", "delivered")), 1),
                    else_=0,
                )
            ).label("delivered"),
        )
        .join(User, User.id == CalendarRequest.user_id)
        .where(
            CalendarRequest.created_at >= User.created_at,
            CalendarRequest.created_at < end_at,
            User.role == "user",
            User.created_at >= start_at,
            User.created_at < end_at,
        )
        .group_by(CalendarRequest.user_id)
        .subquery("calendar_cohort_users")
    )


def _cohort_query(start_at: datetime, end_at: datetime):
    report_users = _report_cohort_users(start_at, end_at)
    calendar_users = _calendar_cohort_users(start_at, end_at)
    profile_complete = and_(
        User.gender.is_not(None),
        User.gender != "",
        User.birth_year.is_not(None),
        User.birth_month.is_not(None),
        User.birth_day.is_not(None),
    )
    has_request = or_(
        report_users.c.user_id.is_not(None),
        calendar_users.c.user_id.is_not(None),
    )
    has_delivery = or_(report_users.c.delivered == 1, calendar_users.c.delivered == 1)
    return (
        select(
            func.count(distinct(User.id)).label("registered_users"),
            func.count(distinct(case((profile_complete, User.id)))).label(
                "profile_completed_users"
            ),
            func.count(distinct(case((has_request, User.id)))).label("applicant_users"),
            func.count(distinct(case((has_delivery, User.id)))).label("delivered_users"),
            func.count(
                distinct(case((report_users.c.user_id.is_not(None), User.id)))
            ).label("report_applicant_users"),
            func.count(
                distinct(case((report_users.c.delivered == 1, User.id)))
            ).label("report_delivered_users"),
            func.count(
                distinct(case((calendar_users.c.user_id.is_not(None), User.id)))
            ).label("calendar_applicant_users"),
            func.count(
                distinct(case((calendar_users.c.delivered == 1, User.id)))
            ).label("calendar_delivered_users"),
        )
        .select_from(User)
        .outerjoin(report_users, report_users.c.user_id == User.id)
        .outerjoin(calendar_users, calendar_users.c.user_id == User.id)
        .where(
            User.role == "user",
            User.created_at >= start_at,
            User.created_at < end_at,
        )
    )


def _login_activity_query(start_at: datetime, end_at: datetime):
    login_in_period = and_(
        User.last_login_at >= start_at,
        User.last_login_at < end_at,
    )
    existing_account = and_(User.is_active.is_(True), User.created_at < start_at)
    return (
        select(
            func.count(distinct(case((login_in_period, User.id)))).label(
                "active_login_users"
            ),
            func.count(distinct(case((existing_account, User.id)))).label(
                "existing_user_base"
            ),
            func.count(
                distinct(case((and_(existing_account, login_in_period), User.id)))
            ).label("returning_users"),
        )
        .select_from(User)
        .where(User.role == "user", User.is_active.is_(True))
    )


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator * 100 / denominator, 1) if denominator else None


async def get_admin_user_growth_summary(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    range_start: date,
    range_end: date,
) -> AdminUserGrowthSummary:
    cohort = (await db.execute(_cohort_query(start_at, end_at))).one()
    activity = (await db.execute(_login_activity_query(start_at, end_at))).one()

    registered_users = int(cohort.registered_users or 0)
    applicant_users = int(cohort.applicant_users or 0)
    delivered_users = int(cohort.delivered_users or 0)
    profile_completed_users = int(cohort.profile_completed_users or 0)
    existing_user_base = int(activity.existing_user_base or 0)
    returning_users = int(activity.returning_users or 0)

    return AdminUserGrowthSummary(
        range_start=range_start,
        range_end=range_end,
        registered_users=registered_users,
        profile_completed_users=profile_completed_users,
        profile_completion_rate_percent=_rate(profile_completed_users, registered_users),
        applicant_users=applicant_users,
        applicant_rate_percent=_rate(applicant_users, registered_users),
        delivered_users=delivered_users,
        delivery_rate_percent=_rate(delivered_users, applicant_users),
        active_login_users=int(activity.active_login_users or 0),
        existing_user_base=existing_user_base,
        returning_users=returning_users,
        existing_user_login_rate_percent=_rate(returning_users, existing_user_base),
        by_service=[
            AdminUserGrowthChannel(
                key="report",
                label="报告",
                applicant_users=int(cohort.report_applicant_users or 0),
                delivered_users=int(cohort.report_delivered_users or 0),
                delivery_rate_percent=_rate(
                    int(cohort.report_delivered_users or 0),
                    int(cohort.report_applicant_users or 0),
                ),
            ),
            AdminUserGrowthChannel(
                key="calendar",
                label="日历",
                applicant_users=int(cohort.calendar_applicant_users or 0),
                delivered_users=int(cohort.calendar_delivered_users or 0),
                delivery_rate_percent=_rate(
                    int(cohort.calendar_delivered_users or 0),
                    int(cohort.calendar_applicant_users or 0),
                ),
            ),
        ],
    )
