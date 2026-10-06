from fastapi import APIRouter

from app.api.v1.admin_activity import router as activity_router
from app.api.v1.admin_calendars import router as calendars_router
from app.api.v1.admin_dashboard import router as dashboard_router
from app.api.v1.admin_exports import router as exports_router
from app.api.v1.admin_feedback import router as feedback_router
from app.api.v1.admin_quality import router as quality_router
from app.api.v1.admin_reports import router as reports_router
from app.api.v1.admin_users import router as users_router

router = APIRouter()
for resource_router in (
    dashboard_router,
    users_router,
    calendars_router,
    reports_router,
    activity_router,
    exports_router,
    feedback_router,
    quality_router,
):
    router.include_router(resource_router)
