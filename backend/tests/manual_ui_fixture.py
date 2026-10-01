"""Seed or remove short-lived data used for browser acceptance checks.

Usage (inside the backend container):

    python tests/manual_ui_fixture.py seed
    python tests/manual_ui_fixture.py cleanup

The seeded users, service requests, reports, calendars and audit rows are all
tracked in ``logs/ui_fixture_state.json`` so ``cleanup`` removes exactly what
``seed`` created.
"""

import asyncio
import hashlib
import json
import secrets
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import and_, delete, or_, select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.domains.calendar.models import CalendarEntry, UserCalendar
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.domains.audit.models import AuditLog

STATE_PATH = Path("/app/logs/ui_fixture_state.json")
PASSWORD = "UiCheck123!"


def report_payload() -> dict:
    return {
        "title": "UI 验收 · 人生说明书",
        "energy_profile": {
            "type": "balanced",
            "core_traits": ["稳重", "好奇"],
            "description": "在稳定与探索之间保持平衡。",
        },
        "career_guidance": {
            "suitable_paths": ["研究", "产品设计"],
            "work_style": "偏好长周期、可迭代的工作方式。",
            "development_suggestions": ["持续学习", "拓展协作"],
            "summary": "更适合长周期、结构化的问题解决场景。",
        },
        "relationship_pattern": {
            "style": "边界清晰",
            "strengths": ["真诚", "稳定"],
            "challenges": ["不轻易表达需求"],
            "growth_direction": "更早说出真实感受。",
            "summary": "直接表达需求，同时给对方留出处理时间。",
        },
        "personal_growth": {
            "action_plan": [
                {
                    "area": "节奏管理",
                    "action": "每周留一次复盘时间。",
                    "timeline": "本周开始",
                }
            ],
            "summary": "把观察转化成可重复的小行动。",
        },
        "summary": "用于界面验收的结构化报告内容。",
        "selected_topics": ["career", "growth"],
    }


def calendar_meta() -> dict:
    return {
        "subtitle": "PERSONAL TIMEZONE",
        "rhythm": "观察、行动、复盘。",
        "intro": "一份私人的决策参考日历。",
        "overview": ["尽量让决定保持可逆。"],
        "pillars": "节奏稳定",
    }


async def seed() -> None:
    tag = secrets.token_hex(4)
    suffix = int(hashlib.sha256(tag.encode()).hexdigest(), 16) % 100_000_000
    base = f"16{suffix:09d}"
    start = date.today() + timedelta(days=1)

    state = {"tag": tag, "user_ids": [], "request_ids": [], "report_ids": [], "calendar_ids": []}
    async with AsyncSessionLocal() as db:
        users = {}
        for index, (key, role, name) in enumerate(
            (
                ("customer", "user", "UI 验收用户"),
                ("consultant", "consultant", "UI 验收咨询师"),
                ("admin", "admin", "UI 验收管理员"),
            )
        ):
            user = User(
                phone=base[:10] + str(index),
                name=f"{name} {tag}",
                password_hash=get_password_hash(PASSWORD),
                role=role,
                is_active=True,
            )
            db.add(user)
            users[key] = user
        await db.commit()
        for user in users.values():
            await db.refresh(user)
            state["user_ids"].append(user.id)

        customer = users["customer"]
        consultant = users["consultant"]

        report = Report(
            user_id=customer.id,
            title="UI 验收 · 人生说明书",
            birth_date=date(1993, 4, 18),
            birth_calendar_type="solar",
            energy_profile=report_payload()["energy_profile"],
            career_guidance=report_payload()["career_guidance"],
            relationship_pattern=report_payload()["relationship_pattern"],
            personal_growth=report_payload()["personal_growth"],
            summary=report_payload()["summary"],
            content_payload=report_payload(),
            selected_topics=["career", "growth"],
            additional_info="希望更明确下一年的节奏。",
            status="completed",
            reviewed_by=consultant.id,
            reviewed_at=datetime.utcnow(),
        )
        db.add(report)

        calendar = UserCalendar(
            user_id=customer.id,
            series_id=f"ui-fixture-{tag}",
            version_number=1,
            title="UI 验收 · 30 天决策日历",
            start_date=start,
            end_date=start + timedelta(days=29),
            status="published",
            meta_payload=calendar_meta(),
            created_by=consultant.id,
            updated_by=consultant.id,
            published_at=datetime.utcnow(),
        )
        db.add(calendar)
        await db.commit()
        await db.refresh(report)
        await db.refresh(calendar)
        state["report_ids"].append(report.id)
        state["calendar_ids"].append(calendar.id)

        for index in range(30):
            db.add(
                CalendarEntry(
                    calendar_id=calendar.id,
                    entry_date=start + timedelta(days=index),
                    day_pillar=f"D{index + 1}",
                    tone="yellow" if index % 3 else "green",
                    status_label=f"第 {index + 1} 天",
                    keyword=f"专注 {index + 1}",
                    summary="先确认下一步最小可行动作，再决定是否投入。",
                    suitable=["规划", "复盘"],
                    unsuitable=["仓促做长期决定"],
                    time_window="上午",
                    admin_note="内部备注不应出现在用户端。",
                )
            )

        requests = [
            ServiceRequest(
                user_id=customer.id,
                service_type="report",
                status="submitted",
                request_payload={
                    "selected_topics": ["career", "stress"],
                    "additional_info": "等待咨询师接单的报告申请。",
                },
            ),
            ServiceRequest(
                user_id=customer.id,
                service_type="calendar",
                status="needs_info",
                request_payload={"calendar_goal": "为换工作做 30 天节奏安排。"},
                assigned_consultant_id=consultant.id,
                needs_info_reason="请补充你希望开始的具体日期。",
                needs_info_at=datetime.utcnow(),
            ),
            ServiceRequest(
                user_id=customer.id,
                service_type="report",
                status="delivered",
                request_payload={"selected_topics": ["relationship", "self"]},
                assigned_consultant_id=consultant.id,
                result_type="report",
                result_id=report.id,
                delivered_at=datetime.utcnow(),
            ),
            ServiceRequest(
                user_id=customer.id,
                service_type="calendar",
                status="delivered",
                request_payload={"calendar_goal": "稳定作息与复盘节奏。"},
                assigned_consultant_id=consultant.id,
                result_type="calendar",
                result_id=calendar.id,
                delivered_at=datetime.utcnow(),
            ),
            ServiceRequest(
                user_id=customer.id,
                service_type="report",
                status="failed",
                request_payload={"selected_topics": ["growth"]},
                assigned_consultant_id=consultant.id,
                last_error="synthetic_failure_for_ui_check",
                failed_at=datetime.utcnow(),
            ),
        ]
        for item in requests:
            db.add(item)
        await db.commit()
        for item in requests:
            await db.refresh(item)
            state["request_ids"].append(item.id)

        report.request_id = state["request_ids"][2]
        calendar.request_id = state["request_ids"][3]
        await db.commit()

    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"tag": tag, "phone": base[:10] + "0"}, ensure_ascii=False))
    print("SEEDED", len(state["user_ids"]), "users")


async def cleanup() -> None:
    if not STATE_PATH.exists():
        print("NO_STATE")
        return
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    user_ids = state["user_ids"]
    async with AsyncSessionLocal() as db:
        request_ids = [
            str(value)
            for value in (
                await db.scalars(
                    select(ServiceRequest.id).where(ServiceRequest.user_id.in_(user_ids))
                )
            ).all()
        ]
        report_ids = [
            str(value)
            for value in (
                await db.scalars(select(Report.id).where(Report.user_id.in_(user_ids)))
            ).all()
        ]
        calendar_ids = [
            str(value)
            for value in (
                await db.scalars(
                    select(UserCalendar.id).where(
                        or_(
                            UserCalendar.user_id.in_(user_ids),
                            UserCalendar.created_by.in_(user_ids),
                        )
                    )
                )
            ).all()
        ]
        await db.execute(
            delete(AuditLog).where(
                or_(
                    AuditLog.actor_user_id.in_(user_ids),
                    AuditLog.target_user_id.in_(user_ids),
                    and_(
                        AuditLog.resource_type == "service_request",
                        AuditLog.resource_id.in_(request_ids),
                    ),
                    and_(
                        AuditLog.resource_type == "report",
                        AuditLog.resource_id.in_(report_ids),
                    ),
                    and_(
                        AuditLog.resource_type == "calendar",
                        AuditLog.resource_id.in_(calendar_ids),
                    ),
                    and_(
                        AuditLog.resource_type.in_(("user", "auth")),
                        AuditLog.resource_id.in_([str(value) for value in user_ids]),
                    ),
                )
            )
        )
        await db.execute(
            delete(UserCalendar).where(
                or_(
                    UserCalendar.user_id.in_(user_ids),
                    UserCalendar.created_by.in_(user_ids),
                )
            )
        )
        await db.execute(delete(Report).where(Report.user_id.in_(user_ids)))
        await db.execute(delete(ServiceRequest).where(ServiceRequest.user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()
    STATE_PATH.unlink(missing_ok=True)
    print("CLEANED", len(user_ids), "users")


async def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if action == "seed":
        await seed()
    elif action == "cleanup":
        await cleanup()
    else:
        raise SystemExit(f"unknown action: {action}")


if __name__ == "__main__":
    asyncio.run(main())
