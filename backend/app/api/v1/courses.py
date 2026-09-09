from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.course import (
    CourseListResponse,
    MyCourseListResponse,
    CourseResponse,
    UserCourseEnrollRequest,
    UserCourseProgressUpdate,
)
from app.services.course_service import (
    enroll_user_course,
    get_all_courses,
    get_user_courses,
    update_user_course_progress,
)
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("", response_model=CourseListResponse)
async def get_courses(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all courses"""
    courses = await get_all_courses(db, user_id=current_user.id)

    # Convert to response format
    course_responses = []
    for course in courses:
        course_responses.append(CourseResponse(
            id=course.id,
            title=course.title,
            description=course.description,
            cover_image=course.cover_image,
            price=course.price,
            original_price=course.original_price,
            total_lessons=course.total_lessons,
            duration_hours=course.duration_hours,
            modules=course.modules,
            status=course.status,
            is_featured=course.is_featured,
            is_enrolled=getattr(course, 'is_enrolled', False)
        ))

    return CourseListResponse(items=course_responses)


@router.get("/my-courses", response_model=MyCourseListResponse)
async def get_my_courses(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's enrolled courses"""
    user_courses = await get_user_courses(db, current_user.id)
    return MyCourseListResponse(items=user_courses)


@router.post("/{course_id}/enroll")
async def enroll_course(
    course_id: int,
    request: UserCourseEnrollRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_course = await enroll_user_course(
            db,
            current_user.id,
            course_id,
            request.purchase_price,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"course_id": user_course.course_id, "status": user_course.status}


@router.patch("/{course_id}/progress")
async def update_course_progress(
    course_id: int,
    request: UserCourseProgressUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_course = await update_user_course_progress(db, current_user.id, course_id, request)
    except ValueError as error:
        if str(error) == "completed_lessons_exceed_total":
            raise HTTPException(status_code=400, detail="Completed lessons exceed course total")
        raise HTTPException(status_code=404, detail="Course enrollment not found")
    await record_audit(
        db,
        current_user.id,
        "course.progress.update",
        "user_course",
        f"{current_user.id}:{course_id}",
        target_user_id=current_user.id,
        details={"progress_percentage": request.progress_percentage, "completed_lessons": request.completed_lessons},
        request=http_request,
    )
    await db.commit()
    return {
        "course_id": user_course.course_id,
        "progress": user_course.progress_percentage,
        "completed_lessons": user_course.completed_lessons,
        "status": user_course.status,
    }
