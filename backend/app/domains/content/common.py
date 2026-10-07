from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase, StepTask
from app.core.time import utc_now_naive


def now() -> datetime:
    return utc_now_naive()


def same_json(left, right) -> bool:
    import json

    return json.dumps(left, sort_keys=True, ensure_ascii=True, default=str) == json.dumps(
        right, sort_keys=True, ensure_ascii=True, default=str
    )


def require_key(value: str, code: str, limit: int = 200) -> str:
    key = value.strip() if isinstance(value, str) else ""
    if not key or len(key) > limit:
        raise ValueError(code)
    return key


async def require_case(db: AsyncSession, report_case_id: int) -> ReportCase:
    report_case = await db.get(ReportCase, report_case_id)
    if report_case is None:
        raise ValueError("report_case_not_found")
    return report_case


async def validate_owner_refs(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    owner_step_task_id: Optional[int],
    source_skill_run_id: Optional[int],
) -> None:
    if owner_step_task_id is not None:
        step = await db.get(StepTask, owner_step_task_id)
        if (
            step is None
            or report_case.workflow_instance_id is None
            or step.workflow_instance_id != report_case.workflow_instance_id
        ):
            raise ValueError("content_owner_step_invalid")
    if source_skill_run_id is not None:
        run = await db.get(SkillRun, source_skill_run_id)
        if run is None or run.report_case_id != report_case.id:
            raise ValueError("content_source_skill_run_invalid")
