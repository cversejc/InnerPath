"""Consume workflow Outbox events without Celery.

Production dispatches Outbox events through Celery. Local review and
acceptance environments run the API with plain uvicorn, so this script
provides the same consume loop for them: poll pending events, execute the
registered handler, then reclaim runs left queued by a stopped worker.

Usage (from ``backend``):

    .venv\\Scripts\\python.exe tools\\run_outbox_worker.py
    .venv\\Scripts\\python.exe tools\\run_outbox_worker.py --once
"""

import argparse
import asyncio
import json
import time
from pathlib import Path
import sys

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.application.skill_run_recovery import recover_stalled_skill_runs  # noqa: E402
from app.core.time import utc_now_naive  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.domains.workflow.models import WorkflowOutbox  # noqa: E402
from app.tasks.workflow_tasks import _consume_outbox_event  # noqa: E402


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, default=str), flush=True)


async def recover_stalled() -> int:
    async with AsyncSessionLocal() as db:
        recovered = await recover_stalled_skill_runs(db)
        if recovered:
            await db.commit()
        return recovered


async def claim_next_event() -> int | None:
    async with AsyncSessionLocal() as db:
        event = await db.scalar(
            select(WorkflowOutbox)
            .where(WorkflowOutbox.status == "PENDING")
            .order_by(WorkflowOutbox.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return None
        event.status = "PUBLISHED"
        event.published_at = utc_now_naive()
        await db.commit()
        return event.id


async def process_pending(batch_size: int) -> int:
    processed = 0
    for _ in range(batch_size):
        event_id = await claim_next_event()
        if event_id is None:
            break
        started = time.monotonic()
        try:
            result = await _consume_outbox_event(event_id)
        except Exception as error:  # keep the loop alive; report and continue
            result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        emit(
            {
                "event_id": event_id,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "result": result,
            }
        )
        processed += 1
    return processed


async def run(interval_seconds: float, batch_size: int, once: bool) -> None:
    emit({"worker": "workflow-outbox", "state": "started", "interval": interval_seconds})
    while True:
        try:
            recovered = await recover_stalled()
            if recovered:
                emit({"worker": "workflow-outbox", "recovered_runs": recovered})
            processed = await process_pending(batch_size)
            if once:
                emit({"worker": "workflow-outbox", "state": "stopped", "processed": processed})
                return
        except Exception as error:
            emit({"worker": "workflow-outbox", "error": f"{type(error).__name__}: {error}"})
            if once:
                raise
        await asyncio.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between polls")
    parser.add_argument("--batch", type=int, default=25, help="events per poll")
    parser.add_argument("--once", action="store_true", help="process one batch and exit")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.interval, args.batch, args.once))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
