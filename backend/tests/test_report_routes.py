import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import httpx
import app.api.v1.reports as reports_api

from app.dependencies import get_current_active_user
from app.main import app
from app.domains.reports.schemas import ReportResponse
from app.domains.reports.service import format_report_response


def test_report_router_keeps_task_and_report_endpoints_registered():
    routes = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}
    }

    assert {
        ("/api/v1/reports", "POST"),
        ("/api/v1/reports/tasks/{task_id}", "GET"),
        ("/api/v1/reports/staff/tasks/{task_id}", "GET"),
        ("/api/v1/reports", "GET"),
        ("/api/v1/reports/staff/users/{user_id}", "GET"),
        ("/api/v1/reports/admin/users/{user_id}", "GET"),
        ("/api/v1/reports/latest/context", "GET"),
        ("/api/v1/reports/{report_id}/pdf", "GET"),
        ("/api/v1/reports/{report_id}", "GET"),
        ("/api/v1/reports/{report_id}", "DELETE"),
    }.issubset(routes)


def test_legacy_report_generation_and_retry_are_retired_without_creating_tasks():
    async def request_retired_endpoints():
        previous_overrides = dict(app.dependency_overrides)

        async def admin_user():
            return SimpleNamespace(id=1, role="admin", is_active=True)

        app.dependency_overrides[get_current_active_user] = admin_user
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                create_response = await client.post(
                    "/api/v1/reports", json={"name": "legacy"}
                )
                retry_response = await client.post(
                    "/api/v1/admin/report-tasks/legacy-task/retry"
                )
            return create_response, retry_response
        finally:
            app.dependency_overrides = previous_overrides

    create_response, retry_response = asyncio.run(request_retired_endpoints())
    assert create_response.status_code == 410
    assert "服务申请" in create_response.json()["detail"]
    assert retry_response.status_code == 410
    assert "服务申请工作流" in retry_response.json()["detail"]

    openapi = app.openapi()
    direct_report_operation = openapi["paths"]["/api/v1/reports"]["post"]
    retry_operation = openapi["paths"][
        "/api/v1/admin/report-tasks/{task_id}/retry"
    ]["post"]
    assert direct_report_operation["deprecated"] is True
    assert "410" in direct_report_operation["responses"]
    assert retry_operation["deprecated"] is True
    assert "410" in retry_operation["responses"]


def test_report_response_normalizes_decision_style_from_application_snapshot():
    now = datetime(2026, 10, 3)
    report = SimpleNamespace(
        id=17,
        title="辰鉴·人生说明书",
        input_snapshot={
            "profile": {
                "name": "演示用户",
                "birth_year": 1992,
                "birth_month": 3,
                "birth_day": 9,
                "calendar_type": "solar",
            },
            "profile_version": 1,
            "context": {
                "focus_topics": ["career"],
                "expected_outcomes": ["下一步"],
                "decision_style": "先收集信息，再小步验证",
            },
        },
        birth_date=date(1992, 3, 9),
        birth_calendar_type="solar",
        created_at=now,
        energy_profile={},
        career_guidance={},
        relationship_pattern={},
        personal_growth={},
        summary="工作节奏",
        content_payload={"structured_sections": []},
        ai_raw_content=None,
        reviewed_at=now,
        selected_topics=["career"],
        additional_info=None,
    )

    response = ReportResponse.model_validate(format_report_response(report))

    assert response.context is not None
    assert response.context.decision_style == ["先收集信息，再小步验证"]


def test_pdf_export_passes_delivered_structured_sections_to_renderer(monkeypatch):
    now = datetime(2026, 10, 4)
    structured_sections = [
        {
            "section_key": "identity",
            "section_title": "你是谁",
            "fragment_key": "report.identity.psychic_structure",
            "title": "内在驱动力",
            "content": "你会先理解全局，再确认自己的立场。",
            "revision_no": 3,
        }
    ]
    report = SimpleNamespace(
        id=17,
        title="辰鉴·人生说明书",
        input_snapshot={
            "profile": {
                "name": "青鸟",
                "birth_year": 1992,
                "birth_month": 3,
                "birth_day": 9,
                "calendar_type": "solar",
            }
        },
        birth_date=date(1992, 3, 9),
        birth_calendar_type="solar",
        created_at=now,
        energy_profile={},
        career_guidance={},
        relationship_pattern={},
        personal_growth={},
        summary="从一个可完成的小步开始。",
        content_payload={
            "structured_sections": structured_sections,
            "summary": "从一个可完成的小步开始。",
        },
        ai_raw_content=None,
        reviewed_at=now,
    )
    actor = SimpleNamespace(id=3, name="咨询师", role="admin")
    captured = {}

    async def report_for_read(db, report_id, current_user):
        assert report_id == report.id
        assert current_user is actor
        return report

    async def render_pdf(report_id, report_payload, user_payload, *, preview=False):
        captured["report_id"] = report_id
        captured["report_payload"] = report_payload
        captured["user_payload"] = user_payload
        captured["preview"] = preview
        return b"%PDF-test"

    monkeypatch.setattr(reports_api, "_report_for_read", report_for_read)
    monkeypatch.setattr(reports_api, "render_report_pdf", render_pdf)

    response = asyncio.run(reports_api.export_report_pdf(report.id, actor, None))

    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-test"
    assert captured["report_id"] == report.id
    assert captured["report_payload"]["content_payload"]["structured_sections"] == structured_sections
    assert captured["report_payload"]["ai_generated_content"] is None
    assert captured["user_payload"] == {"id": actor.id, "name": actor.name, "role": actor.role}
    assert captured["preview"] is False
