from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserUpdate
from app.core.security import get_password_hash, verify_password


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_profile(db: AsyncSession, user: User, user_update: UserUpdate) -> User:
    """Update user profile"""
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def change_user_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise ValueError("invalid_current_password")
    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user
