"""Create explicitly synthetic accounts for local collaboration UI acceptance."""
import asyncio
import argparse
import json
import secrets
from pathlib import Path
from datetime import date
from sqlalchemy.engine import make_url
from app.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from sqlalchemy import select


def require_local_database():
    engine.echo = False
    url = make_url(settings.DATABASE_URL)
    if settings.ENVIRONMENT.lower() not in {"development", "dev", "local"} or url.host not in {"postgres", "localhost", "127.0.0.1"} or url.database != "innerpath":
        raise ValueError("Local development database required")


async def seed():
    require_local_database()
    async with AsyncSessionLocal() as db:
        result = []
        for role, specialty, name in [("admin", None, "合成验收管理员"), ("consultant", "mingli", "合成命理咨询师"),
                                      ("consultant", "psychology", "合成心理咨询师"), ("user", None, "合成验收用户")]:
            phone = "199" + "".join(str(secrets.randbelow(10)) for _ in range(8))
            password = secrets.token_urlsafe(18)
            row = User(phone=phone, name=name, role=role, consultant_type=specialty, password_hash=get_password_hash(password),
                gender="female", birth_year=1996, birth_month=6, birth_day=15, birth_hour=15,
                birth_minute=15, birth_time_precision="exact", birth_place="合成验收地点")
            db.add(row)
            await db.flush()
            result.append({"id": row.id, "role": role, "specialty": specialty, "phone": phone, "password": password})
        await db.commit()
        print(json.dumps(result))
    await engine.dispose()


async def deactivate(account_ids):
    require_local_database()
    allowed_names = {"合成验收管理员", "合成命理咨询师", "合成心理咨询师", "合成验收用户"}
    async with AsyncSessionLocal() as db:
        rows = list(await db.scalars(select(User).where(User.id.in_(account_ids)).with_for_update()))
        if len(rows) != len(set(account_ids)) or any(row.name not in allowed_names or not row.phone.startswith("199") for row in rows):
            raise ValueError("Only named synthetic acceptance accounts can be deactivated")
        for row in rows:
            row.is_active = False
        await db.commit()
        print(json.dumps({"deactivated_synthetic_ids": sorted(account_ids)}))
    await engine.dispose()


async def seed_source_report(user_id, artifact):
    """Load a labelled synthetic report fixture to exercise the real user/queue UI."""
    from app.main import app  # register the full model registry without starting HTTP
    from app.domains.reports.models import Report
    require_local_database()
    snapshot = json.loads((artifact / "request-snapshot.json").read_text(encoding="utf-8"))
    if not str((snapshot.get("profile") or {}).get("name", "")).startswith("合成"):
        raise ValueError("Synthetic acceptance artifact required")
    source = snapshot["source_report"]
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None or user.name != "合成验收用户" or not user.phone.startswith("199"):
            raise ValueError("Named synthetic user required")
        report = await db.scalar(select(Report).where(Report.user_id == user_id,
            Report.title == "合成验收报告 · 仅用于日历联调", Report.is_deleted.is_(False)).limit(1))
        if report is None:
            report = Report(user_id=user_id, title="合成验收报告 · 仅用于日历联调",
                birth_date=date(user.birth_year, user.birth_month, user.birth_day),
                input_snapshot={**source.get("application", {}), "acceptance_fixture": True},
                energy_profile=source.get("energy_profile") or {}, career_guidance=source.get("career_guidance") or {},
                relationship_pattern=source.get("relationship_pattern") or {}, personal_growth=source.get("personal_growth") or {},
                summary=source.get("summary"), content_payload={**source,
                    "mingli_foundation": source["reviewed_foundation"]}, status="completed", is_deleted=False)
            db.add(report)
            await db.flush()
        await db.commit()
        print(json.dumps({"synthetic_user_id": user_id, "source_report_id": report.id}))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deactivate", type=int, nargs="+")
    parser.add_argument("--report-source", type=Path)
    parser.add_argument("--user-id", type=int)
    args = parser.parse_args()
    if args.report_source:
        if not args.user_id:
            parser.error("--user-id is required with --report-source")
        asyncio.run(seed_source_report(args.user_id, args.report_source))
    else:
        asyncio.run(deactivate(args.deactivate) if args.deactivate else seed())
