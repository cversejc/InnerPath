from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    cover_image: Optional[str]
    price: Decimal
    original_price: Optional[Decimal]
    total_lessons: int
    duration_hours: Optional[Decimal]
    modules: Dict[str, Any]
    status: str
    is_featured: bool
    is_enrolled: bool = False

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    items: List[CourseResponse]


class UserCourseResponse(BaseModel):
    course_id: int
    title: str
    progress: int
    completed_lessons: int
    total_lessons: int
    enrolled_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class MyCourseListResponse(BaseModel):
    items: List[UserCourseResponse]
