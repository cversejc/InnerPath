from fastapi import APIRouter

from app.api.v1.admin_activity import router as activity_router
from app.api.v1.admin_bookings import router as bookings_router
from app.api.v1.admin_calendars import router as calendars_router
from app.api.v1.admin_courses import router as courses_router
from app.api.v1.admin_dashboard import router as dashboard_router
from app.api.v1.admin_exports import router as exports_router
from app.api.v1.admin_reports import router as reports_router
from app.api.v1.admin_users import router as users_router

router = APIRouter()
for resource_router in (
    dashboard_router,
    users_router,
    calendars_router,
    bookings_router,
    reports_router,
    activity_router,
    courses_router,
    exports_router,
):
    router.include_router(resource_router)
