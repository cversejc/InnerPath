from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.auth.models import AuthSession, StaffInvite
from app.models.user import User
from app.core.security import create_refresh_token, get_password_hash, hash_refresh_token, verify_password
from app.core.cache import cache_delete, cache_get, cache_increment
from app.config import settings
import secrets


async def _enforce_registration_rate_limit(phone: str, ip_address: Optional[str] = None) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return

    limits = [
        (
            f"auth:register:phone:{phone}",
            settings.RATE_LIMIT_REGISTER_PER_PHONE_PER_HOUR,
        )
    ]
    if ip_address:
        limits.append(
            (
                f"auth:register:ip:{ip_address}",
                settings.RATE_LIMIT_REGISTER_PER_HOUR,
            )
        )

    for key, limit in limits:
        count = await cache_increment(key, expire=3600)
        if count > limit:
            raise ValueError("registration_rate_limited")


async def register_user(
    db: AsyncSession,
    phone: str,
    password: str,
    name: str,
    ip_address: Optional[str] = None,
    phone_verified: bool = False,
) -> User:
    await _enforce_registration_rate_limit(phone, ip_address)

    result = await db.execute(select(User).where(User.phone == phone))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ValueError("phone_already_registered")

    user = User(
        phone=phone,
        name=name,
        password_hash=get_password_hash(password),
        phone_verified_at=datetime.utcnow() if phone_verified else None,
        role="user",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_with_password(db: AsyncSession, phone: str, password: str) -> Optional[User]:
    failure_key = f"auth:password-failures:{phone}"
    failure_count = await cache_get(failure_key)
    if failure_count and int(failure_count) >= 5:
        return None

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        return user
    if not verify_password(password, user.password_hash):
        await cache_increment(failure_key, expire=900)
        return None
    await cache_delete(failure_key)
    return user


async def revoke_all_auth_sessions(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    )
    now = datetime.utcnow()
    for session in result.scalars().all():
        session.revoked_at = now
    await db.commit()


async def change_user_phone(db: AsyncSession, user: User, new_phone: str) -> User:
    result = await db.execute(select(User).where(User.phone == new_phone, User.id != user.id))
    if result.scalar_one_or_none():
        raise ValueError("phone_already_registered")
    user.phone = new_phone
    user.phone_verified_at = datetime.utcnow()
    return user


async def deactivate_user_account(db: AsyncSession, user: User) -> None:
    """Disable an account and revoke its sessions without deleting retained data."""
    now = datetime.utcnow()
    user.is_active = False
    result = await db.execute(
        select(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
    )
    for session in result.scalars().all():
        session.revoked_at = now


async def admin_reset_password(db: AsyncSession, user: User, password: str) -> User:
    user.password_hash = get_password_hash(password)
    user.updated_at = datetime.utcnow()
    await db.commit()
    await revoke_all_auth_sessions(db, user.id)
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


async def reset_password_with_code(db: AsyncSession, user: User, password: str) -> User:
    now = datetime.utcnow()
    user.password_hash = get_password_hash(password)
    user.phone_verified_at = user.phone_verified_at or now
    user.updated_at = now

    result = await db.execute(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    )
    for session in result.scalars().all():
        session.revoked_at = now

    await db.commit()
    await db.refresh(user)
    return user


async def create_auth_session(
    db: AsyncSession,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> str:
    raw_token = create_refresh_token()
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    user.last_login_at = datetime.utcnow()
    await db.commit()
    return raw_token


async def rotate_auth_session(db: AsyncSession, raw_token: str) -> tuple[User, str] | None:
    result = await db.execute(
        select(AuthSession, User)
        .join(User, AuthSession.user_id == User.id)
        .where(AuthSession.token_hash == hash_refresh_token(raw_token))
    )
    row = result.first()
    if not row:
        return None
    session, user = row
    if session.revoked_at or session.expires_at <= datetime.utcnow() or not user.is_active:
        return None
    session.revoked_at = datetime.utcnow()
    new_token = await create_auth_session(db, user)
    return user, new_token


async def revoke_auth_session(db: AsyncSession, raw_token: str) -> Optional[int]:
    result = await db.execute(select(AuthSession).where(AuthSession.token_hash == hash_refresh_token(raw_token)))
    session = result.scalar_one_or_none()
    if session and not session.revoked_at:
        session.revoked_at = datetime.utcnow()
        await db.commit()
        return session.user_id
    return None


async def create_staff_invite(db: AsyncSession, phone: str, role: str, invited_by: int) -> tuple[StaffInvite, str]:
    raw_token = secrets.token_urlsafe(32)
    invite = StaffInvite(
        phone=phone,
        role=role,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(days=2),
        invited_by=invited_by,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite, raw_token


async def accept_staff_invite(
    db: AsyncSession,
    token: str,
    phone: str,
    password: str,
    name: str,
) -> User:
    result = await db.execute(
        select(StaffInvite).where(StaffInvite.token_hash == hash_refresh_token(token))
    )
    invite = result.scalar_one_or_none()
    if not invite or invite.accepted_at or invite.expires_at <= datetime.utcnow() or invite.phone != phone:
        raise ValueError("invalid_invite")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if user and user.password_hash:
        raise ValueError("phone_already_registered")
    if not user:
        user = User(phone=phone, name=name, role=invite.role, is_active=True)
        db.add(user)
    user.name = name
    user.role = invite.role
    user.password_hash = get_password_hash(password)
    invite.accepted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user
