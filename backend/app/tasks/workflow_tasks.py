import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.logging_config import get_logger
from app.core.time import utc_now_naive
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
        from app.application.calendar_production import recover_stalled_calendar_requests
        from app.application.skill_run_recovery import recover_stalled_skill_runs

        await recover_stalled_calendar_requests(db)
        await recover_stalled_skill_runs(db)
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
                    "consume_calendar_outbox_event" if event.event_type == "calendar.generation.requested" else "consume_workflow_outbox_event",
                    args=[event.id],
                    task_id=f"workflow-outbox-{event.id}",
                )
                event.status = "PUBLISHED"
                event.published_at = utc_now_naive()
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

        if event.event_type == "calendar.generation.requested":
            from app.application.calendar_production import execute_calendar_production
            payload = event.payload_json or {}
            return await execute_calendar_production(db, payload["calendar_request_id"], payload.get("attempt", 1))

        if event.event_type == "workflow.step.ready":
            payload = event.payload_json or {}
            step = await db.get(StepTask, payload.get("step_task_id"))
            if (
                step is None
                or step.status != "READY"
                or step.activation_no != payload.get("activation_no")
            ):
                return {"event_id": event_id, "status": "stale"}
            from app.application.node_review_automation import prepare_node
            from app.domains.workflow.models import ReportCase
            case = await db.get(ReportCase, payload.get("report_case_id"))
            if not case or case.review_policy_version != "six-node-review-v1":
                return {"event_id": event_id, "status": "ready", "step_key": step.step_key}
            result = await prepare_node(db, payload.get("report_case_id"), step.id, step.activation_no)
            return {"event_id": event_id, "status": result, "step_key": step.step_key}

        if event.event_type == "report.node.command":
            from app.application.node_review_commands import execute_review_command
            command = await execute_review_command(db, (event.payload_json or {}).get("command_id"))
            return {"event_id": event_id, "status": command.status.lower() if command else "missing"}

        if event.event_type == "report.node.prepare":
            from app.application.node_review_automation import prepare_node
            payload = event.payload_json or {}
            result = await prepare_node(db, payload["report_case_id"], payload["step_task_id"], payload["activation_no"], retry_key=payload.get("retry_key"))
            return {"event_id": event_id, "status": result}

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
            from app.application.node_review_automation import continue_node_run
            try:
                await continue_node_run(db, run)
            except ValueError as error:
                step_id = run.step_task_id
                await db.rollback()
                failed_step = await db.get(StepTask, step_id) if step_id else None
                if failed_step:
                    failed_step.last_error = str(error)
                    await db.commit()
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


@celery_app.task(name="consume_calendar_outbox_event", time_limit=2400, soft_time_limit=2340)
def consume_calendar_outbox_event(event_id: int):
    return asyncio.run(_run_with_engine_disposal(_consume_outbox_event(event_id)))
