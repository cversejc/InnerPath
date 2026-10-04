"""Real-model calendar smoke test using synthetic artifacts in an isolated database."""
import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import date, timedelta
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, JSON, ARRAY, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from app.main import app  # register models without starting the app
from app.db.base import Base
from app.models.user import User
from app.domains.reports.models import Report
from app.domains.calendar.models import UserCalendar
from app.domains.calendar.query_service import serialize_calendar
from app.domains.calendar.schemas import CalendarRequestCreate
from app.domains.skills.models import SkillRun
from app.domains.skills.runtime import DeepSeekGateway
from app.application.calendar_production import queue_calendar_from_report, execute_calendar_production


class IsolatedSession:
    def __init__(self, session):
        self.session = session

    def add(self, row):
        self.session.add(row)

    @asynccontextmanager
    async def begin_nested(self):
        with self.session.begin_nested():
            yield

    async def scalar(self, query):
        return self.session.scalar(query)

    async def scalars(self, query):
        return self.session.scalars(query)

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, model, key):
        return self.session.get(model, key)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def refresh(self, row):
        self.session.refresh(row)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


class CapturingGateway:
    def __init__(self, output):
        self.output, self.index = output, 0

    async def complete(self, **kwargs):
        self.index += 1
        save(self.output / f"call-{self.index}.input.json", kwargs)
        print(f"model call {self.index} started", flush=True)
        result = await DeepSeekGateway().complete(**kwargs)
        save(self.output / f"call-{self.index}.output.json", {"raw": result.content, "trace": result.trace})
        print(f"model call {self.index} completed", flush=True)
        return result


async def run(source, output):
    output.mkdir(parents=True, exist_ok=True)
    if (output / "summary.json").exists():
        raise ValueError("Use a new output directory to preserve previous logs")
    read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
    inputs, authored = read("input.json"), read("S5-report.json")
    assert "合成" in inputs["profile"]["name"]
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                column.type = JSON()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        db = IsolatedSession(session)
        p = inputs["profile"]
        user = User(phone="19900009001", **{key: p[key] for key in
            ["name", "gender", "birth_year", "birth_month", "birth_day", "birth_hour", "birth_minute", "birth_time_precision"]})
        db.add(user)
        await db.flush()
        report = Report(user_id=user.id, birth_date=date(p["birth_year"], p["birth_month"], p["birth_day"]),
            energy_profile={}, career_guidance={}, relationship_pattern={}, personal_growth={},
            input_snapshot={"profile": p, "context": inputs["context"]},
            summary="在答应与透支之间，练习保留一点选择空间。", content_payload={
                "structured_sections": authored["fragments"], "mingli_foundation": inputs["foundation_data"]})
        db.add(report)
        await db.commit()
        start = date(2026, 10, 4)
        request = await queue_calendar_from_report(db, user, CalendarRequestCreate(source_report_id=report.id,
            start_date=start, end_date=start + timedelta(days=29), focus_topics=["career", "relationships"],
            usage_scenario="daily", goal="减少临时答应任务后的透支，练习协商边界", expected_outcomes=["小步行动", "复盘问题"]))
        result = await execute_calendar_production(db, request.id, 1, gateway=CapturingGateway(output))
        calendar = await db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == request.id))
        if calendar:
            save(output / "calendar.json", await serialize_calendar(db, calendar, include_internal=False))
        runs = list(await db.scalars(select(SkillRun).order_by(SkillRun.id)))
        save(output / "runs.json", [{"id": r.id, "skill_version_id": r.skill_version_id, "status": r.status,
            "input_snapshot": r.input_snapshot, "output_parsed": r.output_parsed, "error": r.error,
            "runtime_instruction": r.runtime_instruction, "normalizations": (r.context_snapshot or {}).get("normalizations", []),
            "model_trace": r.model_trace} for r in runs])
        save(output / "request-snapshot.json", request.input_snapshot)
        save(output / "summary.json", {**result, "synthetic": True, "database": "isolated-memory",
            "source": str(source), "generation": request.input_snapshot["generation"],
            "calendar_skill_bindings": request.input_snapshot["calendar_skill_bindings"]})
        print(json.dumps(result), flush=True)
        if result["status"] != "fulfilled":
            raise RuntimeError(request.input_snapshot["generation"].get("error_code"))
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-model", action="store_true", required=True)
    parser.add_argument("--source", type=Path, default=Path("../docs/acceptance/framework-v1/full"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.source.resolve(), args.output.resolve()))
