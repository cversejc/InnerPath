from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import create_access_token
from app.core.sms import verify_code
from datetime import timedelta
from app.config import settings


async def get_or_create_user(db: AsyncSession, phone: str, name: Optional[str] = None) -> User:
    """Get existing user or create new one"""
    # Check if user exists
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Create new user
    user = User(
        phone=phone,
        name=name or f"用户{phone[-4:]}",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, phone: str, code: str) -> Optional[User]:
    """Authenticate user with phone and SMS code"""
    # Verify SMS code
    if not await verify_code(phone, code):
        return None

    # Get or create user
    user = await get_or_create_user(db, phone)
    return user


async def update_user(db: AsyncSession, user: User, user_update: UserUpdate) -> User:
    """Update user information"""
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
