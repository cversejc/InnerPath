from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1 import report_cases
from app.domains.content.schemas import ContentFragmentRevisionCreate


@pytest.mark.asyncio
async def test_style_revision_from_final_review_preserves_original_step_owner(monkeypatch):
    original_fragment = SimpleNamespace(
        report_case_id=10,
        fragment_key="report.identity.outer_self",
        revision_no=2,
        owner_step_task_id=59,
    )
    final_review_step = SimpleNamespace(id=60)
    revised_fragment = SimpleNamespace(revision_no=3)
    monkeypatch.setattr(
        report_cases,
        "_authorize_step_action",
        AsyncMock(return_value=(SimpleNamespace(id=10), final_review_step)),
    )
    create_revision = AsyncMock(return_value=revised_fragment)
    monkeypatch.setattr(report_cases, "create_content_fragment_revision", create_revision)
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=original_fragment)

    result = await report_cases.revise_report_case_fragment(
        10,
        "S6",
        "report.identity.outer_self",
        ContentFragmentRevisionCreate(
            expected_revision_no=2,
            fragment_type="REPORT",
            title="当前职业处境",
            content="调整表达后的报告内容。",
            status="CONFIRMED",
            edit_kind="STYLE",
        ),
        current_user=SimpleNamespace(id=35, role="consultant"),
        db=db,
    )

    assert result is revised_fragment
    assert create_revision.await_args.kwargs["owner_step_task_id"] == 59
    assert "finding_refs" not in create_revision.await_args.kwargs
    assert "fragment_refs" not in create_revision.await_args.kwargs
    assert "evidence_refs" not in create_revision.await_args.kwargs
    db.commit.assert_awaited_once()

