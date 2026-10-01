"""Manual real-Celery/DeepSeek acceptance checks for service request drafts."""

import asyncio
import hashlib
import secrets
import time
from datetime import date, datetime, timedelta

import httpx
from sqlalchemy import and_, delete, or_, select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.domains.calendar.models import UserCalendar
from app.domains.reports.models import Report
from app.models.service_request import ServiceRequest, ServiceRequestDraft, ServiceRequestTask
from app.models.user import AuditLog, User


BASE_URL = "http://localhost:8000"
PASSWORD = "E2ePassw0rd!"
POLL_SECONDS = 4
POLL_TIMEOUT_SECONDS = 300
engine.echo = False


def check(condition: bool, label: str, detail: str = "") -> None:
    if not condition:
        suffix = f" ({detail})" if detail else ""
        raise AssertionError(f"{label}{suffix}")
    print(f"PASS {label}")


def expect_status(response: httpx.Response, expected: int, label: str) -> dict:
    detail = ""
    if response.status_code != expected:
        try:
            payload = response.json()
            detail = str(payload.get("detail", payload))[:300]
        except Exception:
            detail = response.text[:300]
    check(response.status_code == expected, label, f"got {response.status_code}: {detail}")
    return response.json() if response.content else {}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def wait_for_task(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
    label: str,
) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    last_payload: dict = {}
    while time.monotonic() < deadline:
        response = await client.get(
            f"/api/v1/staff/service-request-tasks/{task_id}",
            headers=auth(token),
        )
        last_payload = expect_status(response, 200, f"{label} task status")
        status = last_payload["status"]
        progress = last_payload.get("progress")
        print(f"INFO {label} task {status} progress={progress}")
        if status in {"completed", "failed"}:
            return last_payload
        await asyncio.sleep(POLL_SECONDS)
    raise AssertionError(
        f"{label} timed out after {POLL_TIMEOUT_SECONDS}s; last={last_payload}"
    )


async def seed_failed_report_task(request_id: int, task_id: str) -> None:
    async with AsyncSessionLocal() as db:
        service_request = await db.get(ServiceRequest, request_id)
        if service_request is None:
            raise AssertionError("failed-task request missing")
        service_request.status = "failed"
        service_request.last_error = "synthetic_provider_failure"
        service_request.failed_at = datetime.utcnow()
        db.add(
            ServiceRequestTask(
                task_id=task_id,
                request_id=request_id,
                service_type="report",
                status="failed",
                progress=0,
                error="synthetic_provider_failure",
                input_snapshot=service_request.request_payload,
                retry_count=0,
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
    phone_base = f"18{suffix:09d}"
    roles = (
        ("customer", "user"),
        ("consultant", "consultant"),
        ("other", "consultant"),
    )
    users: dict[str, User] = {}
    user_ids: list[int] = []
    async with AsyncSessionLocal() as db:
        for index, (key, role) in enumerate(roles):
            user = User(
                phone=phone_base[:10] + str(index),
                name=f"AI E2E {key} {tag}",
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
            for key, user in users.items():
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"phone": user.phone, "password": PASSWORD},
                )
                tokens[key] = expect_status(response, 200, f"AI login {key}")["access_token"]

            customer_token = tokens["customer"]
            consultant_token = tokens["consultant"]
            other_token = tokens["other"]
            profile = {
                "name": f"AI E2E subject {tag}",
                "gender": "female",
                "birth_year": 1992,
                "birth_month": 4,
                "birth_day": 12,
                "birth_hour": 8,
                "birth_minute": 15,
                "birth_place": "Hangzhou",
                "calendar_type": "solar",
                "time_accuracy": "exact",
            }

            report_payload = {
                "service_type": "report",
                "profile": profile,
                "selected_topics": ["career", "growth"],
                "additional_info": "Focus on a realistic weekly action plan.",
                "idempotency_key": f"ai-report-{tag}",
            }
            report_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer_token),
                json=report_payload,
            )
            report_request_id = expect_status(
                report_create, 201, "create AI report request"
            )["id"]
            expect_status(
                await client.post(
                    f"/api/v1/staff/service-requests/{report_request_id}/accept",
                    headers=auth(consultant_token),
                ),
                200,
                "accept AI report request",
            )

            failed_task_id = f"e2e-failed-{tag}"
            await seed_failed_report_task(report_request_id, failed_task_id)
            failed_status = await client.get(
                f"/api/v1/staff/service-request-tasks/{failed_task_id}",
                headers=auth(consultant_token),
            )
            failed_payload = expect_status(
                failed_status, 200, "read synthetic failed task"
            )
            check(
                failed_payload["status"] == "failed"
                and failed_payload["error"] == "synthetic_provider_failure",
                "AI failure is persisted with error",
            )
            denied_failed_task = await client.get(
                f"/api/v1/staff/service-request-tasks/{failed_task_id}",
                headers=auth(other_token),
            )
            expect_status(denied_failed_task, 403, "other consultant cannot read failed task")

            retried = await client.post(
                f"/api/v1/staff/service-requests/{report_request_id}/retry-ai",
                headers=auth(consultant_token),
                json={"confirm_overwrite": False},
            )
            retried_payload = expect_status(retried, 202, "retry real report AI task")
            check(
                retried_payload["status"] == "processing"
                and retried_payload["retry_count"] == 1,
                "retry metadata links to failed task",
            )
            report_task = await wait_for_task(
                client,
                consultant_token,
                retried_payload["task_id"],
                "report",
            )
            check(
                report_task["status"] == "completed",
                "real report Celery task succeeds",
                report_task.get("error", ""),
            )
            report_workspace = await client.get(
                f"/api/v1/staff/service-requests/{report_request_id}",
                headers=auth(consultant_token),
            )
            report_workspace_payload = expect_status(
                report_workspace, 200, "read real report workspace"
            )
            report_draft = report_workspace_payload["draft"]
            check(report_draft is not None, "real report draft exists")
            for section in (
                "energy_profile",
                "career_guidance",
                "relationship_pattern",
                "personal_growth",
                "summary",
            ):
                check(section in report_draft["editable_payload"], f"real report has {section}")

            report_delivery = await client.post(
                f"/api/v1/staff/service-requests/{report_request_id}/deliver",
                headers=auth(consultant_token),
            )
            report_delivery_payload = expect_status(
                report_delivery, 200, "deliver real report draft"
            )
            check(
                report_delivery_payload["status"] == "delivered"
                and report_delivery_payload["result_type"] == "report",
                "real report draft passes delivery validation",
            )
            delivered_report = await client.get(
                f"/api/v1/reports/{report_delivery_payload['result_id']}",
                headers=auth(customer_token),
            )
            report_payload_response = expect_status(
                delivered_report, 200, "read real AI report"
            )
            check(
                bool(report_payload_response["energy_profile"])
                and bool(report_payload_response["summary"]),
                "real AI report has reviewable content",
            )

            start = date.today() + timedelta(days=5)
            calendar_create = await client.post(
                "/api/v1/service-requests",
                headers=auth(customer_token),
                json={
                    "service_type": "calendar",
                    "profile": profile,
                    "selected_topics": ["career", "growth"],
                    "calendar_goal": "Plan steady weekly progress.",
                    "start_date": start.isoformat(),
                    "additional_info": "Keep each day concrete and low-pressure.",
                    "idempotency_key": f"ai-calendar-{tag}",
                },
            )
            calendar_request_id = expect_status(
                calendar_create, 201, "create AI calendar request"
            )["id"]
            expect_status(
                await client.post(
                    f"/api/v1/staff/service-requests/{calendar_request_id}/accept",
                    headers=auth(consultant_token),
                ),
                200,
                "accept AI calendar request",
            )
            calendar_task_response = await client.post(
                f"/api/v1/staff/service-requests/{calendar_request_id}/ai-draft",
                headers=auth(consultant_token),
            )
            calendar_task_payload = expect_status(
                calendar_task_response, 202, "start real calendar AI task"
            )
            calendar_task = await wait_for_task(
                client,
                consultant_token,
                calendar_task_payload["task_id"],
                "calendar",
            )
            check(
                calendar_task["status"] == "completed",
                "real calendar Celery task succeeds",
                calendar_task.get("error", ""),
            )
            calendar_workspace = await client.get(
                f"/api/v1/staff/service-requests/{calendar_request_id}",
                headers=auth(consultant_token),
            )
            calendar_workspace_payload = expect_status(
                calendar_workspace, 200, "read real calendar workspace"
            )
            generated_calendar = calendar_workspace_payload["draft"]["editable_payload"]
            entries = generated_calendar["entries"]
            entry_dates = [date.fromisoformat(item["entry_date"]) for item in entries]
            expected_dates = [start + timedelta(days=index) for index in range(30)]
            check(len(entries) == 30, "AI calendar has exactly 30 entries")
            check(len(set(entry_dates)) == 30, "AI calendar dates are unique")
            check(
                sorted(entry_dates) == expected_dates,
                "AI calendar covers the exact requested window",
            )
            check(
                all(
                    item.get("keyword")
                    and item.get("status_label")
                    and item.get("summary")
                    for item in entries
                ),
                "AI calendar entries are complete",
            )

            calendar_delivery = await client.post(
                f"/api/v1/staff/service-requests/{calendar_request_id}/deliver",
                headers=auth(consultant_token),
            )
            calendar_delivery_payload = expect_status(
                calendar_delivery, 200, "deliver real calendar draft"
            )
            check(
                calendar_delivery_payload["status"] == "delivered"
                and calendar_delivery_payload["result_type"] == "calendar",
                "real AI calendar passes delivery validation",
            )
            customer_calendars = await client.get(
                "/api/v1/calendar/me",
                headers=auth(customer_token),
            )
            customer_calendar_payload = expect_status(
                customer_calendars, 200, "read delivered real calendar"
            )
            delivered_calendar = next(
                item
                for item in customer_calendar_payload["items"]
                if item["id"] == calendar_delivery_payload["result_id"]
            )
            check(
                len(delivered_calendar["entries"]) == 30,
                "delivered real calendar keeps 30 entries",
            )
            other_calendars = await client.get(
                "/api/v1/calendar/me",
                headers=auth(other_token),
            )
            other_calendar_payload = expect_status(
                other_calendars, 200, "other consultant reads own calendar list"
            )
            check(
                all(
                    item["id"] != calendar_delivery_payload["result_id"]
                    for item in other_calendar_payload["items"]
                ),
                "real calendar remains private to the customer",
            )
    finally:
        await cleanup(user_ids)
        print(f"CLEANED {len(user_ids)} AI E2E fixture users")

    print("ALL REAL AI E2E CHECKS PASSED")


if __name__ == "__main__":
    started = time.time()
    asyncio.run(main())
    print(f"ELAPSED {time.time() - started:.2f}s")
