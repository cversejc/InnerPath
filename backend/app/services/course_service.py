from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.course import Course, UserCourse


async def get_all_courses(db: AsyncSession, user_id: Optional[int] = None) -> List[Course]:
    """Get all active courses"""
    query = select(Course).where(Course.status == "active")
    result = await db.execute(query)
    courses = result.scalars().all()

    # Check enrollment status if user_id provided
    if user_id:
        enrolled_course_ids = await get_enrolled_course_ids(db, user_id)
        for course in courses:
            course.is_enrolled = course.id in enrolled_course_ids

    return list(courses)


async def get_enrolled_course_ids(db: AsyncSession, user_id: int) -> set:
    """Get IDs of courses user is enrolled in"""
    query = select(UserCourse.course_id).where(UserCourse.user_id == user_id)
    result = await db.execute(query)
    return set(result.scalars().all())


async def get_user_courses(db: AsyncSession, user_id: int) -> List[dict]:
    """Get user's enrolled courses with progress"""
    query = select(UserCourse, Course).join(
        Course, UserCourse.course_id == Course.id
    ).where(UserCourse.user_id == user_id)

    result = await db.execute(query)
    rows = result.all()

    user_courses = []
    for user_course, course in rows:
        user_courses.append({
            "course_id": course.id,
            "title": course.title,
            "progress": user_course.progress_percentage,
            "completed_lessons": user_course.completed_lessons,
            "total_lessons": course.total_lessons,
            "enrolled_at": user_course.enrolled_at,
            "completed_at": user_course.completed_at
        })

    return user_courses
