from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.course import CourseListResponse, MyCourseListResponse, CourseResponse
from app.services.course_service import get_all_courses, get_user_courses

router = APIRouter()


@router.get("", response_model=CourseListResponse)
async def get_courses(
    current_user: Optional[User] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all courses"""
    user_id = current_user.id if current_user else None
    courses = await get_all_courses(db, user_id=user_id)

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
