import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.domains.workflow.models import StepTask, WorkflowOutbox
from app.tasks.celery_app import celery_app


logger = get_logger(__name__)


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

        return {
            "event_id": event_id,
            "status": "observed",
            "event_type": event.event_type,
        }


@celery_app.task(name="dispatch_workflow_outbox")
def dispatch_workflow_outbox():
    try:
        return asyncio.run(_dispatch_pending_events())
    finally:
        asyncio.run(engine.dispose())


@celery_app.task(name="consume_workflow_outbox_event")
def consume_workflow_outbox_event(event_id: int):
    try:
        return asyncio.run(_consume_outbox_event(event_id))
    finally:
        asyncio.run(engine.dispose())
