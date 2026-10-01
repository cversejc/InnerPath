from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.course import UserCourseProgressUpdate
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/courses/users/{user_id}")
async def list_user_courses(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import get_user_courses

    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"items": await get_user_courses(db, user_id)}

@router.patch("/courses/users/{user_id}/{course_id}/progress")
async def update_user_course_progress_for_admin(
    user_id: int,
    course_id: int,
    data: UserCourseProgressUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import update_course_progress_for_admin

    try:
        user_course = await update_course_progress_for_admin(db, user_id, course_id, data)
    except ValueError as error:
        if str(error) == "completed_lessons_exceed_total":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Completed lessons exceed course total")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await record_audit(
        db,
        current_user.id,
        "course.progress.update",
        "user_course",
        str(user_course.id),
        target_user_id=user_id,
        details={"progress_percentage": data.progress_percentage, "completed_lessons": data.completed_lessons},
        request=request,
    )
    await db.commit()
    return {"course_id": user_course.course_id, "user_id": user_course.user_id, "progress": user_course.progress_percentage, "completed_lessons": user_course.completed_lessons, "status": user_course.status}
