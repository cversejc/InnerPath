from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.admin_quality_issues import list_admin_report_quality_issues


@pytest.mark.asyncio
async def test_admin_quality_issue_list_exposes_case_context_without_resolution_controls(monkeypatch):
    from app.application import admin_quality_issues

    issue = SimpleNamespace(
        id=17,
        source_type="PROGRAMMATIC",
        source_ref_id=None,
        issue_type="MISSING_REQUIRED_FRAGMENT",
        severity="BLOCK",
        status="OPEN",
        target_fragment_key="career_guidance",
        message="报告缺少必需的事业建议章节。",
        suggestion="请补充事业建议章节后重新检查。",
        resolution=None,
        resolved_at=None,
        created_at=datetime(2026, 10, 2),
    )
    report_case = SimpleNamespace(
        id=73,
        status="ACTIVE",
        user_id=8,
        service_request_id=91,
    )
    user = SimpleNamespace(id=8, name="质检用户", phone="13900000000")

    class Result:
        def all(self):
            return [(issue, report_case, user, SimpleNamespace(id=91))]

    db = SimpleNamespace(
        scalar=AsyncMock(return_value=1),
        execute=AsyncMock(return_value=Result()),
    )
    monkeypatch.setattr(
        admin_quality_issues,
        "quality_state",
        AsyncMock(return_value=SimpleNamespace(issues=[issue])),
    )
    items, total = await list_admin_report_quality_issues(
        db,
        status="OPEN",
        severity="BLOCK",
        page=1,
        size=20,
    )

    assert total == 1
    assert items[0].report_case_id == 73
    assert items[0].service_request_id == 91
    assert items[0].user_name == "质检用户"
    assert items[0].severity == "BLOCK"
    assert items[0].is_current is True
    assert not hasattr(items[0], "evidence_json")
