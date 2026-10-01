from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.query_service import get_user_calendars
from app.domains.service_requests.service import has_staff_assignment


async def get_calendar_for_staff(db: AsyncSession, staff_id: int, user_id: int) -> list[dict]:
    if not await has_staff_assignment(db, staff_id, user_id):
        return []
    return await get_user_calendars(db, user_id, published_only=True)
