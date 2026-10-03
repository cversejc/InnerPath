from datetime import date, datetime
from types import SimpleNamespace

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
        ("/api/v1/reports/{report_id}", "GET"),
        ("/api/v1/reports/{report_id}", "DELETE"),
    }.issubset(routes)


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
