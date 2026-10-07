import argparse
import asyncio

from sqlalchemy import select

from app.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User


DEFAULT_ADMIN_PHONE = "00000000000"
DEFAULT_ADMIN_NAME = "系统管理员"
DEFAULT_ADMIN_PASSWORD = "Admin@chenvis"


async def create_admin(phone: str, name: str, password: str) -> None:
    if not phone.isdigit() or len(phone) != 11:
        raise ValueError("phone must contain 11 digits")
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must contain at least {settings.PASSWORD_MIN_LENGTH} characters")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if not user:
            user = User(phone=phone, name=name, role="admin", is_active=True)
            db.add(user)
        user.name = name
        user.role = "admin"
        user.password_hash = get_password_hash(password)
        user.is_active = True
        await db.commit()
        print(f"Admin account ready for {phone}")


def main() -> None:
    parser = argparse.ArgumentParser(description="chenvis account administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin_parser = subparsers.add_parser("create-admin", help="Create or promote an administrator")
    admin_parser.add_argument("--phone", default=DEFAULT_ADMIN_PHONE)
    admin_parser.add_argument("--name", default=DEFAULT_ADMIN_NAME)
    admin_parser.add_argument("--password", default=DEFAULT_ADMIN_PASSWORD)
    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(create_admin(args.phone, args.name, args.password))


if __name__ == "__main__":
    main()
