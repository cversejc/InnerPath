"""Recover skill runs whose Outbox event was never picked up by a worker.

Queued work depends on a background consumer reading ``workflow_outbox``.
When that consumer is stopped, misconfigured or interrupted, the run stays
``PENDING`` forever and blocks a retry of the same workflow action. This
module marks such orphaned runs as failed so the action can be retried.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.core.time import utc_now_naive
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import WorkflowOutbox


logger = get_logger(__name__)

# A healthy consumer picks a queued run up within seconds. This window is
# deliberately generous so a busy single worker never has work reclaimed
# from under it.
SKILL_RUN_QUEUE_TIMEOUT_SECONDS = 900


async def recover_stalled_skill_runs(
    db: AsyncSession,
    *,
    timeout_seconds: int = SKILL_RUN_QUEUE_TIMEOUT_SECONDS,
    now: datetime | None = None,
) -> int:
    """Fail queued runs that no consumer has started within the timeout.

    Only ``PENDING`` runs are reclaimed: once a run reaches ``RUNNING`` the
    model call owns its own timeout policy.
    """

    current = now or utc_now_naive()
    cutoff = current - timedelta(seconds=timeout_seconds)
    runs = list(
        await db.scalars(
            select(SkillRun)
            .where(
                SkillRun.status == "PENDING",
                SkillRun.created_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        )
    )
    if not runs:
        return 0

    run_ids = [run.id for run in runs]
    events = list(
        await db.scalars(
            select(WorkflowOutbox)
            .where(
                WorkflowOutbox.aggregate_type == "skill_run",
                WorkflowOutbox.aggregate_id.in_(run_ids),
                WorkflowOutbox.status.in_({"PENDING", "PUBLISHED"}),
            )
            .with_for_update(skip_locked=True)
        )
    )
    for run in runs:
        run.status = "FAILED"
        run.error = "skill_run_queue_timeout"
        run.completed_at = current
        logger.warning(
            "Skill run 排队超时已回收 | run_id=%s target_type=%s created_at=%s",
            run.id,
            run.target_type,
            run.created_at,
        )
    # Keep the stale Outbox row from being consumed later and rerunning the
    # same action after the retry has already produced a fresh run.
    for event in events:
        event.status = "FAILED"
        event.retry_count += 1
    return len(runs)
