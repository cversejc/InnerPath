from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.schemas import UserUpdate
from app.models.user import User


PROFILE_LIST_FIELDS = {
    "personality_keywords",
    "mingli_experience",
    "default_usage_scenarios",
}

PROFILE_VERSION_FIELDS = {
    "name",
    "gender",
    "birth_year",
    "birth_month",
    "birth_day",
    "birth_hour",
    "birth_minute",
    "birth_place",
    "calendar_type",
    "birth_time_precision",
    "current_residence",
    "marital_status",
    "occupation_status",
    "highest_education",
    "mbti",
    "personality_keywords",
    "strengths",
    "limitations",
    "mingli_experience",
    "mingli_attitude",
    "preferred_content_depth",
    "default_usage_scenarios",
}


def apply_user_profile_update(user: User, update_data: dict) -> list[str]:
    """Apply profile fields and return the fields whose values changed.

    This helper is shared by self-service and admin updates so profile version
    semantics stay identical regardless of who edited the user.
    """
    update_data = dict(update_data)
    if "name" in update_data:
        name = str(update_data["name"] or "").strip()
        if not name:
            raise ValueError("name_required")
        update_data["name"] = name
    if "calendar_type" in update_data and update_data["calendar_type"] is None:
        raise ValueError("calendar_type_required")
    next_birth = {
        field: update_data.get(field, getattr(user, field, None))
        for field in ("birth_year", "birth_month", "birth_day")
    }
    if all(value is not None for value in next_birth.values()):
        calendar_type = update_data.get("calendar_type", getattr(user, "calendar_type", "solar"))
        if calendar_type == "lunar" and int(next_birth["birth_day"]) > 30:
            raise ValueError("birth_date_invalid")
        try:
            date(int(next_birth["birth_year"]), int(next_birth["birth_month"]), int(next_birth["birth_day"]))
        except (TypeError, ValueError):
            raise ValueError("birth_date_invalid")
    if "birth_time_precision" in update_data:
        precision = update_data["birth_time_precision"] or "unknown"
        update_data["birth_time_precision"] = precision
        if precision == "unknown":
            update_data["birth_hour"] = None
            update_data["birth_minute"] = None
        else:
            next_hour = update_data.get("birth_hour", user.birth_hour)
            next_minute = update_data.get("birth_minute", user.birth_minute)
            if next_hour is None or next_minute is None:
                raise ValueError("birth_time_requires_hour_and_minute")
    elif "birth_hour" in update_data or "birth_minute" in update_data:
        next_hour = update_data.get("birth_hour", user.birth_hour)
        next_minute = update_data.get("birth_minute", user.birth_minute)
        if next_hour is None or next_minute is None:
            raise ValueError("birth_time_requires_hour_and_minute")
        if getattr(user, "birth_time_precision", "unknown") == "unknown":
            raise ValueError("birth_time_requires_precision")

    for field in PROFILE_LIST_FIELDS:
        if field in update_data:
            value = update_data[field]
            if value is None:
                update_data[field] = []
            elif isinstance(value, (list, tuple)):
                update_data[field] = [str(item).strip() for item in value if str(item).strip()]

    changed_fields: list[str] = []
    for field, value in update_data.items():
        if not hasattr(user, field):
            continue
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed_fields.append(field)

    if any(field in PROFILE_VERSION_FIELDS for field in changed_fields):
        user.profile_version = int(user.profile_version or 1) + 1
        user.profile_last_confirmed_at = datetime.utcnow()
    elif any(field in PROFILE_VERSION_FIELDS for field in update_data):
        user.profile_last_confirmed_at = datetime.utcnow()

    return changed_fields


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_profile(db: AsyncSession, user: User, user_update: UserUpdate) -> User:
    """Update user profile"""
    update_data = user_update.model_dump(exclude_unset=True)
    apply_user_profile_update(user, update_data)

    await db.commit()
    await db.refresh(user)
    return user
