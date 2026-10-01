"""Manual end-to-end acceptance checks for the consultant service workflow.

Run inside the backend container while the full stack is healthy:

    python tests/manual_service_request_e2e.py

This script intentionally uses the real HTTP API and real PostgreSQL database.
It creates uniquely named fixture users and removes all of them at the end.
"""

import asyncio
import hashlib
import secrets
import time
from datetime import date, timedelta

import httpx
from sqlalchemy import and_, delete, or_, select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.domains.calendar.models import UserCalendar
from app.domains.reports.models import Report
from app.domains.service_requests.models import (
    ServiceRequest,
    ServiceRequestDraft,
    ServiceRequestTask,
)
from app.models.user import AuditLog, User


BASE_URL = "http://localhost:8000"
PASSWORD = "E2ePassw0rd!"
CHECKS = []
engine.echo = False


def check(condition: bool, label: str, detail: str = "") -> None:
    if not condition:
        suffix = f" ({detail})" if detail else ""
        raise AssertionError(f"{label}{suffix}")
    CHECKS.append(label)
    print(f"PASS {label}")


def expect_status(response: httpx.Response, expected: int, label: str) -> dict:
    detail = ""
    if response.status_code != expected:
        try:
            payload = response.json()
            detail = str(payload.get("detail", payload))
        except Exception:
            detail = response.text[:200]
    check(response.status_code == expected, label, f"got {response.status_code}: {detail}")
    if response.content:
        return response.json()
    return {}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def report_draft() -> dict:
    return {
        "title": "E2E reviewed report",
        "energy_profile": {
            "type": "balanced",
            "core_traits": ["steady", "curious"],
        },
        "career_guidance": {
            "suitable_paths": ["research", "product design"],
            "summary": "Prefer sustained, structured problem solving.",
        },
        "relationship_pattern": {
            "style": "clear boundaries",
            "summary": "State needs directly and allow time to process.",
        },
        "personal_growth": {
            "action_plan": ["Keep a weekly reflection note."],
            "summary": "Turn observations into small repeatable actions.",
        },
        "summary": "A consultant-reviewed, evidence-oriented draft.",
    }


def calendar_draft(start: date) -> dict:
    return {
        "title": "E2E reviewed calendar",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=29)).isoformat(),
        "meta_payload": {
            "subtitle": "PERSONAL TIMEZONE",
            "rhythm": "Observe, act, review.",
            "intro": "A private decision reference calendar.",
            "overview": ["Keep decisions reversible where possible."],
            "pillars": "Consistency",
        },
        "entries": [
            {
                "entry_date": (start + timedelta(days=index)).isoformat(),
                "day_pillar": f"D{index + 1}",
                "tone": "yellow" if index % 3 else "green",
                "status_label": f"Day {index + 1}",
                "keyword": f"Focus {index + 1}",
                "summary": "Clarify the next useful step before acting.",
                "suitable": ["plan", "review"],
                "unsuitable": ["rush a permanent decision"],
                "time_window": "morning",
                "admin_note": "internal note",
            }
            for index in range(30)
        ],
    }


async def seed_draft(request_id: int, service_type: str, payload: dict) -> None:
    async with AsyncSessionLocal() as db:
        service_request = await db.get(ServiceRequest, request_id)
        if service_request is None:
            raise AssertionError(f"seed target request {request_id} missing")
        service_request.status = "ai_ready"
        draft = await db.scalar(
            select(ServiceRequestDraft).where(ServiceRequestDraft.request_id == request_id)
        )
        if draft is None:
            draft = ServiceRequestDraft(
                request_id=request_id,
                ai_payload=payload,
                editable_payload=payload,
                ai_version=1,
                content_version=1,
            )
            db.add(draft)
        else:
            draft.ai_payload = payload
            draft.editable_payload = payload
            draft.ai_version = 1
            draft.content_version = 1
        await db.commit()


async def seed_completed_task(request_id: int, task_id: str, service_type: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.get(ServiceRequestTask, task_id)
        if existing is None:
            db.add(
                ServiceRequestTask(
                    task_id=task_id,
                    request_id=request_id,
                    service_type=service_type,
                    status="completed",
                    progress=100,
                )
            )
            await db.commit()


async def cleanup(user_ids: list[int]) -> None:
    if not user_ids:
        return
    async with AsyncSessionLocal() as db:
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
        report_ids = [
            str(value)
            for value in (
                await db.scalars(select(Report.id).where(Report.user_id.in_(user_ids)))
            ).all()
        ]
        request_ids = [
            str(value)
            for value in (
                await db.scalars(
                    select(ServiceRequest.id).where(ServiceRequest.user_id.in_(user_ids))
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


async def main() -> None:
    tag = secrets.token_hex(5)
    suffix = int(hashlib.sha256(tag.encode()).hexdigest(), 16) % 100_000_000
    phone_base = f"19{suffix:09d}"
    if len(phone_base) != 11:
        raise AssertionError("fixture phone generation failed")

    roles = (
        ("customer", "user"),
        ("other", "user"),
        ("consultant_a", "consultant"),
        ("consultant_b", "consultant"),
        ("admin", "admin"),
    )
    users: dict[str, User] = {}
    user_ids: list[int] = []
    async with AsyncSessionLocal() as db:
        for index, (key, role) in enumerate(roles):
            phone = phone_base[:10] + str(index)
            user = User(
                phone=phone,
                name=f"E2E {key} {tag}",
                password_hash=get_password_hash(PASSWORD),
                role=role,
                is_active=True,
            )
            db.add(user)
            users[key] = user
        await db.commit()
        for user in users.values():
            await db.refresh(user)
            user_ids.append(user.id)

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            tokens: dict[str, str] = {}
            for key, spec in users.items():
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"phone": spec.phone, "password": PASSWORD},
                )
                payload = expect_status(response, 200, f"login {key}")
                tokens[key] = payload["access_token"]

            customer = tokens["customer"]
            other = tokens["other"]
            consultant_a = tokens["consultant_a"]
            consultant_b = tokens["consultant_b"]
            admin = tokens["admin"]

            profile = {
                "name": f"E2E subject {tag}",
                "gender": "female",
                "birth_year": 1991,
                "birth_month": 6,
                "birth_day": 18,
                "birth_hour": 9,
                "birth_minute": 30,
                "birth_place": "Shanghai",
                "calendar_type": "solar",
                "time_accuracy": "exact",
            }
            report_create = {
                "service_type": "report",
                "profile": profile,
                "selected_topics": ["career", "growth"],
                "additional_info": "E2E only",
            }
            calendar_create = {
                "service_type": "calendar",
                "profile": profile,
                "selected_topics": ["growth"],
                "calendar_goal": "Plan the next 30 days",
                "start_date": (date.today() + timedelta(days=3)).isoformat(),
                "additional_info": "E2E only",
            }

            idempotency_key = f"e2e-idem-{tag}"
            first = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": idempotency_key},
            )
            first_payload = expect_status(first, 201, "create request")
            second = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": idempotency_key},
            )
            second_payload = expect_status(second, 201, "repeat idempotent request")
            check(first_payload["id"] == second_payload["id"], "idempotency returns same request")

            listing = await client.get(
                "/api/v1/service-requests",
                headers=auth(customer),
                params={"service_type": "report"},
            )
            listing_payload = expect_status(listing, 200, "list own requests")
            check(
                any(item["id"] == first_payload["id"] for item in listing_payload["items"]),
                "own request appears in list",
            )

            withdrawn = await client.post(
                f"/api/v1/service-requests/{first_payload['id']}/withdraw",
                headers=auth(customer),
            )
            withdrawn_payload = expect_status(withdrawn, 200, "withdraw submitted request")
            check(withdrawn_payload["status"] == "withdrawn", "withdraw status persisted")
            repeated_withdraw = await client.post(
                f"/api/v1/service-requests/{first_payload['id']}/withdraw",
                headers=auth(customer),
            )
            expect_status(repeated_withdraw, 409, "repeated withdraw rejected")

            needs_info_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": f"e2e-info-{tag}"},
            )
            needs_info_id = expect_status(needs_info_create, 201, "create needs-info request")["id"]
            accepted = await client.post(
                f"/api/v1/staff/service-requests/{needs_info_id}/accept",
                headers=auth(consultant_a),
            )
            accepted_payload = expect_status(accepted, 200, "consultant accepts request")
            check(accepted_payload["status"] == "accepted", "accept status persisted")

            info_request = await client.post(
                f"/api/v1/staff/service-requests/{needs_info_id}/request-info",
                headers=auth(consultant_a),
                json={"reason": "Please add the relevant context."},
            )
            info_payload = expect_status(info_request, 200, "consultant requests more information")
            check(info_payload["status"] == "needs_info", "needs-info status persisted")

            updated = await client.patch(
                f"/api/v1/service-requests/{needs_info_id}",
                headers=auth(customer),
                json={"additional_info": "Additional E2E context."},
            )
            updated_payload = expect_status(updated, 200, "user updates requested information")
            check(
                updated_payload["request_payload"]["additional_info"]
                == "Additional E2E context.",
                "user update persisted",
            )

            resubmitted = await client.post(
                f"/api/v1/service-requests/{needs_info_id}/resubmit",
                headers=auth(customer),
            )
            resubmitted_payload = expect_status(resubmitted, 200, "user resubmits request")
            check(
                resubmitted_payload["status"] == "accepted"
                and resubmitted_payload["assigned_consultant_id"] == users["consultant_a"].id,
                "resubmit keeps existing assignment",
            )

            race_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": f"e2e-race-{tag}"},
            )
            race_id = expect_status(race_create, 201, "create concurrency request")["id"]
            race_responses = await asyncio.gather(
                client.post(
                    f"/api/v1/staff/service-requests/{race_id}/accept",
                    headers=auth(consultant_a),
                ),
                client.post(
                    f"/api/v1/staff/service-requests/{race_id}/accept",
                    headers=auth(consultant_b),
                ),
            )
            race_codes = sorted(response.status_code for response in race_responses)
            check(
                race_codes == [200, 409],
                "concurrent accept allows exactly one consultant",
                f"codes={race_codes}",
            )
            winner_token = consultant_a if race_responses[0].status_code == 200 else consultant_b
            loser_token = consultant_b if winner_token == consultant_a else consultant_a
            loser_workspace = await client.get(
                f"/api/v1/staff/service-requests/{race_id}",
                headers=auth(loser_token),
            )
            expect_status(loser_workspace, 403, "non-assigned consultant workspace denied")
            consultant_all = await client.get(
                "/api/v1/staff/service-requests",
                headers=auth(winner_token),
                params={"scope": "all"},
            )
            expect_status(consultant_all, 403, "consultant all-scope list denied")

            admin_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": f"e2e-admin-{tag}"},
            )
            admin_request_id = expect_status(admin_create, 201, "create admin workflow request")["id"]
            assigned = await client.patch(
                f"/api/v1/admin/service-requests/{admin_request_id}/assignment",
                headers=auth(admin),
                json={"consultant_id": users["consultant_b"].id},
            )
            assigned_payload = expect_status(assigned, 200, "admin assigns consultant")
            check(
                assigned_payload["status"] == "accepted"
                and assigned_payload["assigned_consultant_id"] == users["consultant_b"].id,
                "admin assignment persisted",
            )
            unassigned = await client.patch(
                f"/api/v1/admin/service-requests/{admin_request_id}/assignment",
                headers=auth(admin),
                json={"consultant_id": None},
            )
            unassigned_payload = expect_status(unassigned, 200, "admin unassigns consultant")
            check(
                unassigned_payload["status"] == "submitted"
                and unassigned_payload["assigned_consultant_id"] is None,
                "unassignment returns request to pool",
            )
            rejected = await client.post(
                f"/api/v1/admin/service-requests/{admin_request_id}/reject",
                headers=auth(admin),
                json={"reason": "E2E rejection path."},
            )
            rejected_payload = expect_status(rejected, 200, "admin rejects request")
            check(
                rejected_payload["status"] == "rejected"
                and rejected_payload["rejection_reason"] == "E2E rejection path.",
                "admin rejection persisted",
            )

            legacy = await client.post(
                "/api/v1/reports",
                headers=auth(customer),
                json={
                    "name": f"E2E subject {tag}",
                    "gender": "female",
                    "birth_year": 1991,
                    "birth_month": 6,
                    "birth_day": 18,
                    "birth_hour": 9,
                    "birth_minute": 30,
                    "birth_place": "Shanghai",
                },
            )
            expect_status(legacy, 410, "legacy direct report generation retired")

            report_req_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**report_create, "idempotency_key": f"e2e-report-{tag}"},
            )
            report_request_id = expect_status(
                report_req_create, 201, "create report delivery request"
            )["id"]
            expect_status(
                await client.post(
                    f"/api/v1/staff/service-requests/{report_request_id}/accept",
                    headers=auth(consultant_a),
                ),
                200,
                "accept report delivery request",
            )
            await seed_draft(report_request_id, "report", report_draft())
            workspace = await client.get(
                f"/api/v1/staff/service-requests/{report_request_id}",
                headers=auth(consultant_a),
            )
            workspace_payload = expect_status(workspace, 200, "assigned consultant reads workspace")
            check(
                workspace_payload["draft"]["content_version"] == 1,
                "seeded report draft visible",
            )
            saved = await client.put(
                f"/api/v1/staff/service-requests/{report_request_id}/draft",
                headers=auth(consultant_a),
                json={"payload": report_draft(), "expected_version": 1},
            )
            saved_payload = expect_status(saved, 200, "consultant saves report draft")
            check(saved_payload["content_version"] == 2, "draft version increments")
            conflict = await client.put(
                f"/api/v1/staff/service-requests/{report_request_id}/draft",
                headers=auth(consultant_a),
                json={"payload": report_draft(), "expected_version": 1},
            )
            expect_status(conflict, 409, "stale report draft version conflicts")
            await seed_completed_task(
                report_request_id,
                f"e2e-task-{tag}",
                "report",
            )
            own_task = await client.get(
                f"/api/v1/staff/service-request-tasks/e2e-task-{tag}",
                headers=auth(consultant_a),
            )
            expect_status(own_task, 200, "assigned consultant reads task")
            other_task = await client.get(
                f"/api/v1/staff/service-request-tasks/e2e-task-{tag}",
                headers=auth(consultant_b),
            )
            expect_status(other_task, 403, "non-assigned consultant task denied")

            delivered = await client.post(
                f"/api/v1/staff/service-requests/{report_request_id}/deliver",
                headers=auth(consultant_a),
            )
            delivered_payload = expect_status(delivered, 200, "deliver report")
            check(
                delivered_payload["status"] == "delivered"
                and delivered_payload["result_type"] == "report",
                "report delivery persisted",
            )
            report_id = delivered_payload["result_id"]
            report_response = await client.get(
                f"/api/v1/reports/{report_id}",
                headers=auth(customer),
            )
            report_payload = expect_status(report_response, 200, "customer reads delivered report")
            check(
                report_payload["summary"] == report_draft()["summary"],
                "delivered report content is readable",
            )
            other_report = await client.get(
                f"/api/v1/reports/{report_id}",
                headers=auth(other),
            )
            expect_status(other_report, 404, "other user cannot read report")

            calendar_req_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer),
                json={**calendar_create, "idempotency_key": f"e2e-calendar-{tag}"},
            )
            calendar_request_id = expect_status(
                calendar_req_create, 201, "create calendar delivery request"
            )["id"]
            expect_status(
                await client.post(
                    f"/api/v1/staff/service-requests/{calendar_request_id}/accept",
                    headers=auth(consultant_a),
                ),
                200,
                "accept calendar delivery request",
            )
            start = date.today() + timedelta(days=3)
            await seed_draft(calendar_request_id, "calendar", calendar_draft(start))
            calendar_delivered = await client.post(
                f"/api/v1/staff/service-requests/{calendar_request_id}/deliver",
                headers=auth(consultant_a),
            )
            calendar_delivered_payload = expect_status(
                calendar_delivered, 200, "deliver calendar"
            )
            check(
                calendar_delivered_payload["result_type"] == "calendar",
                "calendar delivery persisted",
            )
            calendar_id = calendar_delivered_payload["result_id"]
            calendars = await client.get("/api/v1/calendar/me", headers=auth(customer))
            calendars_payload = expect_status(calendars, 200, "customer reads calendars")
            delivered_calendar = next(
                (
                    item
                    for item in calendars_payload["items"]
                    if item["id"] == calendar_id
                ),
                None,
            )
            check(delivered_calendar is not None, "delivered calendar is current")
            check(
                len(delivered_calendar["entries"]) == 30,
                "delivered calendar contains all 30 days",
            )
            check(
                all(entry["admin_note"] is None for entry in delivered_calendar["entries"]),
                "public calendar hides consultant notes",
            )
            other_calendars = await client.get("/api/v1/calendar/me", headers=auth(other))
            other_calendars_payload = expect_status(
                other_calendars, 200, "other user reads own calendars"
            )
            check(
                all(item["id"] != calendar_id for item in other_calendars_payload["items"]),
                "other user cannot see delivered calendar",
            )
            staff_calendars = await client.get(
                f"/api/v1/calendar/staff/users/{users['customer'].id}",
                headers=auth(consultant_b),
            )
            staff_calendars_payload = expect_status(
                staff_calendars, 200, "non-assigned consultant calendar list"
            )
            check(
                all(item["id"] != calendar_id for item in staff_calendars_payload["items"]),
                "non-assigned consultant gets no calendar data",
            )

            admin_list = await client.get(
                "/api/v1/admin/service-requests",
                headers=auth(admin),
            )
            admin_list_payload = expect_status(admin_list, 200, "admin lists all requests")
            check(
                any(item["id"] == report_request_id for item in admin_list_payload["items"]),
                "admin list includes delivered request",
            )
    finally:
        await cleanup(user_ids)
        print(f"CLEANED {len(user_ids)} fixture users")

    print(f"ALL {len(CHECKS)} E2E CHECKS PASSED")


if __name__ == "__main__":
    started = time.time()
    asyncio.run(main())
    print(f"ELAPSED {time.time() - started:.2f}s")
