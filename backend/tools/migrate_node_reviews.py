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


async def main(apply):
    async with AsyncSessionLocal() as db:
        result = await migrate_reviews(db, apply=apply)
        print(json.dumps({"apply": apply, "cases": result}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args().apply))
