"""Print the impact inventory before applying; --apply is explicit and resumable."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # Register domain metadata consistently with the running app.
from app.db.session import AsyncSessionLocal
from app.application.node_review_migration import migrate_reviews


async def main(apply, case_ids, auto_prepare):
    async with AsyncSessionLocal() as db:
        result = await migrate_reviews(db, apply=apply, case_ids=case_ids, auto_prepare=auto_prepare)
        print(json.dumps({"apply": apply, "case_ids": case_ids, "auto_prepare": auto_prepare, "cases": result}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--case-id", action="append", type=int, dest="case_ids",
                        help="Only migrate this report case id; repeat the flag for multiple cases.")
    parser.add_argument("--no-auto-prepare", action="store_false", dest="auto_prepare",
                        help="Leave the first step READY without enqueuing automatic node preparation.")
    args = parser.parse_args()
    asyncio.run(main(args.apply, args.case_ids, args.auto_prepare))
