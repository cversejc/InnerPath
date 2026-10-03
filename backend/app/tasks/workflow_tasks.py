import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.domains.workflow.models import StepTask, WorkflowOutbox
from app.tasks.celery_app import celery_app


logger = get_logger(__name__)


async def _run_with_engine_disposal(operation):
    try:
        return await operation
    finally:
        try:
            await engine.dispose()
        except Exception:
            logger.exception("Workflow task database connection disposal failed")


async def _dispatch_pending_events(batch_size: int = 100) -> int:
    published = 0
    async with AsyncSessionLocal() as db:
        events = await db.scalars(
            select(WorkflowOutbox)
            .where(WorkflowOutbox.status == "PENDING")
            .order_by(WorkflowOutbox.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        for event in events:
            try:
                celery_app.send_task(
                    "consume_workflow_outbox_event",
                    args=[event.id],
                    task_id=f"workflow-outbox-{event.id}",
                )
                event.status = "PUBLISHED"
                event.published_at = datetime.utcnow()
                published += 1
            except Exception:
                event.retry_count += 1
                logger.exception("Workflow Outbox 投递失败 | event_id=%s", event.id)
        await db.commit()
    return published


async def _consume_outbox_event(event_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        event = await db.get(WorkflowOutbox, event_id)
        if event is None:
            return {"event_id": event_id, "status": "missing"}
        if event.status == "FAILED":
            return {"event_id": event_id, "status": "not_published"}

        if event.event_type == "workflow.step.ready":
            payload = event.payload_json or {}
            step = await db.get(StepTask, payload.get("step_task_id"))
            if (
                step is None
                or step.status != "READY"
                or step.activation_no != payload.get("activation_no")
            ):
                return {"event_id": event_id, "status": "stale"}
            # Phase 1 steps are manual. Later executors can consume the same
            # event after checking its activation number and current state.
            return {"event_id": event_id, "status": "ready", "step_key": step.step_key}

        if event.event_type == "skill.run.requested":
            from app.application.skill_runtime import execute_skill_run_record

            run_id = (event.payload_json or {}).get("skill_run_id")
            if not isinstance(run_id, int):
                return {"event_id": event_id, "status": "invalid_payload"}
            run = await execute_skill_run_record(db, run_id)
            if run.target_type in {
                "REPORT_FRAGMENT",
                "REPORT_CHAPTER_COHERENCE",
                "REPORT_COHERENCE",
            } and (
                (run.context_snapshot or {}).get("report_generation")
            ):
                from app.application.report_generation import (
                    advance_case_report_generation,
                )

                await advance_case_report_generation(db, run.id)
            return {
                "event_id": event_id,
                "status": run.status.lower(),
                "skill_run_id": run.id,
            }

        return {
            "event_id": event_id,
            "status": "observed",
            "event_type": event.event_type,
        }


@celery_app.task(name="dispatch_workflow_outbox")
def dispatch_workflow_outbox():
    return asyncio.run(_run_with_engine_disposal(_dispatch_pending_events()))


@celery_app.task(name="consume_workflow_outbox_event")
def consume_workflow_outbox_event(event_id: int):
    return asyncio.run(
        _run_with_engine_disposal(_consume_outbox_event(event_id))
    )
