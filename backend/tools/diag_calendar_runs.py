"""Read-only diagnostic for a stuck calendar production request.

Run inside the backend container with database access, for example:

    python diag_calendar_runs.py --request-id 2
    python diag_calendar_runs.py --request-id 2 --run-id 41 --run-id 43

Without --run-id every skill run of the request is listed with its input
snapshot summary, error and output shape. With --run-id the daily entries of
the selected runs are printed for a closer look at the model output.
"""

import argparse
import asyncio
import json

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domains.skills.models import SkillRun


def brief(value, limit=400):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


async def main(request_id: int, focus: set[int]):
    async with AsyncSessionLocal() as db:
        runs = (
            await db.scalars(
                select(SkillRun)
                .where(
                    SkillRun.target_type == "CALENDAR_PRODUCTION",
                    SkillRun.target_key == str(request_id),
                )
                .order_by(SkillRun.id)
            )
        ).all()
        if focus:
            for run in runs:
                if run.id not in focus:
                    continue
                print("=" * 72)
                print(f"id={run.id} key={run.idempotency_key} status={run.status} error={brief(run.error)}")
                entries = (run.output_parsed or {}).get("entries")
                if not isinstance(entries, list):
                    print("output_parsed=" + brief(run.output_parsed, 4000))
                    continue
                for entry in entries:
                    print(json.dumps({
                        "entry_date": entry.get("entry_date"),
                        "keyword": entry.get("keyword"),
                        "suitable": entry.get("suitable"),
                        "unsuitable": entry.get("unsuitable"),
                        "action_refs": entry.get("action_refs"),
                    }, ensure_ascii=False))
            return
        print(f"runs={len(runs)}")
        for run in runs:
            snapshot = run.input_snapshot or {}
            print("-" * 72)
            print(f"id={run.id} key={run.idempotency_key} status={run.status}")
            print(f"dates={snapshot.get('requested_dates')}")
            print(f"error={brief(run.error)}")
            instruction = run.runtime_instruction or ""
            print(f"instruction={brief(instruction, 260)}")
            scheduled = snapshot.get("scheduled_practice_by_date")
            if scheduled:
                print("scheduled_practice_by_date=" + brief(scheduled, 1200))
            rhythm = ((snapshot.get("source_report") or {}).get("practice_rhythm") or {})
            if rhythm.get("actions"):
                print("actions=" + brief([
                    {k: a.get(k) for k in ("action_id", "frequency", "duration_minutes")}
                    for a in rhythm["actions"]
                ], 900))
            entries = (run.output_parsed or {}).get("entries") if isinstance(run.output_parsed, dict) else None
            if entries:
                print("entries=" + brief([
                    {"entry_date": e.get("entry_date"), "action_refs": e.get("action_refs")}
                    for e in entries
                ], 1600))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List calendar production skill runs for one request."
    )
    parser.add_argument("--request-id", type=int, required=True)
    parser.add_argument(
        "--run-id",
        type=int,
        action="append",
        dest="run_ids",
        default=[],
        help="Print the daily entries of this run; repeat for multiple runs.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.request_id, set(args.run_ids)))
