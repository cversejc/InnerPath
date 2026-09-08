import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User


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
    parser = argparse.ArgumentParser(description="InnerSeek account administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin_parser = subparsers.add_parser("create-admin", help="Create or promote an administrator")
    admin_parser.add_argument("--phone", required=True)
    admin_parser.add_argument("--name", default="系统管理员")
    admin_parser.add_argument("--password")
    args = parser.parse_args()

    if args.command == "create-admin":
        password = args.password or getpass.getpass("Admin password: ")
        asyncio.run(create_admin(args.phone, args.name, password))


if __name__ == "__main__":
    main()
