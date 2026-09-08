from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select
from app.models.course import Course, UserCourse
from app.schemas.course import UserCourseProgressUpdate


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


async def enroll_user_course(
    db: AsyncSession,
    user_id: int,
    course_id: int,
    purchase_price=0,
) -> UserCourse:
    course = await db.get(Course, course_id)
    if not course:
        raise ValueError("course_not_found")
    result = await db.execute(
        select(UserCourse).where(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
    )
    user_course = result.scalar_one_or_none()
    if user_course:
        return user_course
    user_course = UserCourse(
        user_id=user_id,
        course_id=course_id,
        purchase_price=purchase_price,
        enrolled_at=datetime.utcnow(),
        status="active",
    )
    db.add(user_course)
    await db.commit()
    await db.refresh(user_course)
    return user_course


async def update_user_course_progress(
    db: AsyncSession,
    user_id: int,
    course_id: int,
    data: UserCourseProgressUpdate,
) -> UserCourse:
    result = await db.execute(
        select(UserCourse).where(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
    )
    user_course = result.scalar_one_or_none()
    if not user_course:
        raise ValueError("course_not_enrolled")
    user_course.completed_lessons = data.completed_lessons
    user_course.progress_percentage = data.progress_percentage
    user_course.last_lesson_id = data.last_lesson_id
    if data.progress_percentage >= 100:
        user_course.status = "completed"
        user_course.completed_at = user_course.completed_at or datetime.utcnow()
    else:
        user_course.status = "active"
        user_course.completed_at = None
    await db.commit()
    await db.refresh(user_course)
    return user_course


async def update_course_progress_for_admin(
    db: AsyncSession,
    user_id: int,
    course_id: int,
    data: UserCourseProgressUpdate,
) -> UserCourse:
    try:
        return await update_user_course_progress(db, user_id, course_id, data)
    except ValueError as error:
        if str(error) != "course_not_enrolled":
            raise
        await enroll_user_course(db, user_id, course_id, purchase_price=0)
        return await update_user_course_progress(db, user_id, course_id, data)
