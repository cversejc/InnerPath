"""Real-model calendar smoke test using synthetic artifacts in an isolated database."""
import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from html import escape
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
from app.domains.service_requests.models import ServiceRequest
from app.domains.calendar.models import UserCalendar
from app.domains.calendar.query_service import serialize_calendar
from app.domains.calendar.schemas import CalendarRequestCreate
from app.domains.content.models import NarrativePlan
from app.domains.delivery.models import ReportVersion
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.runtime import DeepSeekGateway
from app.domains.workflow.models import ReportCase, WorkflowInstance, WorkflowVersion
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


async def seed_delivered_report(db, user, inputs, authored, plan_artifact, stage_outputs):
    """Freeze the archived synthetic report as a delivered ReportVersion fixture."""
    now = datetime.utcnow()
    profile = inputs["profile"]
    context = inputs["context"]
    application_snapshot = {"profile": profile, "context": context, "acceptance_fixture": True}

    workflow_version = WorkflowVersion(
        workflow_key="report.acceptance.fixture", name="合成报告验收夹具", version=1,
        status="PUBLISHED", definition_json={"fixture": True},
        created_at=now, published_at=now,
    )
    db.add(workflow_version)
    await db.flush()
    case = ReportCase(
        user_id=user.id,
        status="DELIVERED", application_snapshot=application_snapshot,
        application_submitted_at=now, created_at=now, updated_at=now, delivered_at=now,
    )
    db.add(case)
    await db.flush()
    workflow_instance = WorkflowInstance(
        report_case_id=case.id, workflow_version_id=workflow_version.id,
        status="COMPLETED", created_at=now, updated_at=now, completed_at=now,
    )
    db.add(workflow_instance)
    await db.flush()
    case.workflow_instance_id = workflow_instance.id

    plan_skill = AISkillVersion(
        skill_key="report.narrative_plan", name="合成报告主线技能夹具",
        category="AUTHORING", version=1, status="PUBLISHED",
        specification_json={"fixture": True}, created_at=now, published_at=now,
    )
    db.add(plan_skill)
    await db.flush()
    plan_run = SkillRun(
        skill_version_id=plan_skill.id, report_case_id=case.id,
        workflow_instance_id=workflow_instance.id, target_type="REPORT_CASE",
        target_key=str(case.id), run_type="INITIAL", status="COMPLETED",
        idempotency_key="calendar-acceptance-narrative-plan",
        runtime_instruction="Synthetic accepted report fixture",
        input_snapshot={}, context_snapshot={}, output_raw="Archived synthetic report plan",
        output_parsed=plan_artifact, selected_examples=[], selected_knowledge=[],
        model_trace={"fixture": True}, created_at=now, completed_at=now,
    )
    db.add(plan_run)
    await db.flush()

    plan = NarrativePlan(
        report_case_id=case.id, version_no=1, status="CONFIRMED",
        selected_skill_run_id=plan_run.id, selected_candidate_key="framework-v1-full",
        plan_json=plan_artifact.get("plan", {}), source_snapshot={"synthetic": True},
        created_at=now, confirmed_at=now,
    )
    db.add(plan)
    await db.flush()

    findings_by_key = {}
    analysis_fragments = []
    for output in stage_outputs:
        for finding in output.get("findings", []):
            findings_by_key[finding["finding_key"]] = finding
        analysis_fragments.extend(output.get("analysis_fragments", []))
    findings = list(findings_by_key.values())
    fragments = authored["fragments"]
    chapter_titles = {"identity": "你是谁", "challenge": "卡在哪", "direction": "往哪去"}
    structured_sections = [
        {
            "section_key": fragment.get("chapter") or "additional",
            "section_title": chapter_titles.get(fragment.get("chapter"), fragment.get("title") or "补充内容"),
            "fragment_key": fragment["fragment_key"],
            "title": fragment.get("title"),
            "content": fragment.get("content", ""),
            "revision_no": 1,
        }
        for fragment in fragments
    ]
    evidence = [{
        "evidence_key": "synthetic.reviewed_foundation",
        "source_type": "SYSTEM_CALCULATED",
        "source_ref": "framework-v1/full/foundation_data",
        "value": inputs["foundation_data"],
    }]
    semantics = {"findings": findings, "fragments": analysis_fragments, "evidence": evidence}
    narrative_plan = plan_artifact.get("plan", {})
    version = ReportVersion(
        report_case_id=case.id, version_no=1, workflow_version_id=workflow_version.id,
        narrative_plan_id=plan.id, fragment_snapshot=fragments,
        semantic_snapshot={"application_snapshot": application_snapshot,
                          "semantics": semantics, "narrative_plan": {"plan_json": plan_artifact}},
        structured_data={"title": "辰鉴·人生说明书", "narrative_plan": narrative_plan,
                        "structured_sections": structured_sections,
                        "source_fragment_ids": [], "workflow_version_id": workflow_version.id},
        rendered_html="<article class=\"report-version\">" + "".join(
            f"<section><h2>{escape(item['section_title'])}</h2><h3>{escape(item.get('title') or '')}</h3>"
            f"<p>{escape(item['content']).replace(chr(10), '<br>')}</p></section>"
            for item in structured_sections
        ) + "</article>",
        created_at=now, delivered_at=now,
    )
    db.add(version)
    await db.flush()

    birth_date = date(profile["birth_year"], profile["birth_month"], profile["birth_day"])
    service_request = ServiceRequest(
        user_id=case.user_id,
        service_type="report",
        status="delivered",
        request_payload={"profile": profile, "context": context},
        result_type="report",
        delivered_at=now,
    )
    db.add(service_request)
    await db.flush()
    report = Report(
        user_id=case.user_id, request_id=service_request.id, reviewed_at=now,
        birth_date=birth_date, birth_calendar_type=profile.get("calendar_type", "solar"),
        birth_place=profile.get("birth_place"), input_snapshot={
            "profile": profile, "context": context, "report_version": {"id": version.id},
            "acceptance_fixture": True,
        }, energy_profile={}, career_guidance={}, relationship_pattern={}, personal_growth={},
        summary=narrative_plan.get("core_theme"), content_payload={"structured_sections": structured_sections},
        status="completed",
    )
    db.add(report)
    await db.flush()
    service_request.result_id = report.id
    await db.commit()
    return report, case, version, findings


def audit_published_schedule(snapshot, calendar):
    source_report = (snapshot or {}).get("source_report") or {}
    rhythm = source_report.get("practice_rhythm") or {}
    actions = {row.get("action_id"): row for row in rhythm.get("actions", []) if isinstance(row, dict)}
    schedule = ((snapshot or {}).get("production_trace") or {}).get("practice_schedule") or {}
    if isinstance(calendar, dict):
        calendar_meta = calendar.get("meta_payload") or {}
    else:
        calendar_meta = calendar.meta_payload or {}
    details = calendar_meta.get("daily_details") or {}
    mismatches, over_budget = [], []
    placements = {}
    daily_minutes = {}
    available_minutes = (snapshot or {}).get("available_minutes_per_day", 30)
    for day, expected in schedule.items():
        expected = list(expected or [])
        actual = list((details.get(day) or {}).get("action_refs") or [])
        if expected != actual:
            mismatches.append({"entry_date": day, "expected": expected, "actual": actual})
        minutes = 0
        for action_id in expected:
            placements[action_id] = placements.get(action_id, 0) + 1
            minutes += (actions.get(action_id) or {}).get("duration_minutes", 0)
        daily_minutes[day] = minutes
        if minutes > available_minutes:
            over_budget.append({"entry_date": day, "minutes": minutes})

    unavailable = calendar_meta.get("practice_rhythm", {}).get("unavailable_actions", [])
    unavailable_ids = {row.get("action_id") for row in unavailable if isinstance(row, dict)}
    report_action_ids = set(actions)
    unaccounted = sorted(report_action_ids - set(placements) - unavailable_ids)
    return {
        "report_action_count": len(report_action_ids),
        "scheduled_action_ids": sorted(placements),
        "action_placement_counts": placements,
        "unavailable_actions": unavailable,
        "unaccounted_action_ids": unaccounted,
        "scheduled_days": len(schedule),
        "matching_reference_days": len(schedule) - len(mismatches),
        "reference_mismatches": mismatches,
        "available_minutes_per_day": available_minutes,
        "max_daily_minutes": max(daily_minutes.values(), default=0),
        "over_budget_days": over_budget,
    }


async def run(source, output):
    source_dir = source
    output.mkdir(parents=True, exist_ok=True)
    if (output / "summary.json").exists():
        raise ValueError("Use a new output directory to preserve previous logs")
    read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
    inputs, authored = read("input.json"), read("S5-report.json")
    plan_artifact = read("S5-plan.json")
    stage_outputs = [read(f"S{stage}.json")["output"] for stage in range(1, 5)]
    assert "合成" in inputs["profile"]["name"]
    assert any(row.get("semantic_role") == "ACTION" for output in stage_outputs
               for row in output.get("findings", [])), "Synthetic source must contain reviewed report actions"
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                column.type = JSON()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        db = IsolatedSession(session)
        p = inputs["profile"]
        user_fields = ["name", "gender", "birth_year", "birth_month", "birth_day", "birth_hour",
                       "birth_minute", "birth_time_precision", "birth_place", "calendar_type",
                       "current_residence", "occupation_status", "mbti", "preferred_content_depth"]
        user = User(phone="19900009001", **{key: p[key] for key in user_fields if key in p})
        db.add(user)
        await db.flush()
        report, case, version, findings = await seed_delivered_report(
            db, user, inputs, authored, plan_artifact, stage_outputs
        )
        start = date(2026, 10, 4)
        available_minutes = inputs["context"].get("available_minutes_per_day", 30)
        if not isinstance(available_minutes, int) or isinstance(available_minutes, bool):
            available_minutes = 30
        request = await queue_calendar_from_report(db, user, CalendarRequestCreate(source_report_id=report.id,
            start_date=start, end_date=start + timedelta(days=29), focus_topics=["career", "relationships"],
            usage_scenario="daily", goal="减少临时答应任务后的透支，练习协商边界",
            expected_outcomes=["小步行动", "复盘问题"], available_minutes_per_day=available_minutes))
        source = request.input_snapshot["source_report"]
        practice_rhythm = source["practice_rhythm"]
        if source.get("report_version_id") != version.id or not practice_rhythm["actions"]:
            raise AssertionError("Calendar acceptance must consume a frozen ReportVersion with scheduled actions")
        result = await execute_calendar_production(db, request.id, 1, gateway=CapturingGateway(output))
        calendar = await db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == request.id))
        schedule_audit = audit_published_schedule(request.input_snapshot, calendar) if calendar else None
        if calendar:
            if calendar.meta_payload.get("source_report_version_id") != version.id:
                raise AssertionError("Published calendar lost its source ReportVersion")
            if calendar.meta_payload.get("practice_rhythm", {}).get("report_version_id") != version.id:
                raise AssertionError("Published practice rhythm lost its source ReportVersion")
            if (schedule_audit["reference_mismatches"] or schedule_audit["over_budget_days"]
                    or schedule_audit["unaccounted_action_ids"]):
                raise AssertionError("Published calendar failed ReportVersion schedule audit")
            save(output / "calendar.json", await serialize_calendar(db, calendar, include_internal=False))
            save(output / "schedule-audit.json", schedule_audit)
        runs = list(await db.scalars(select(SkillRun).order_by(SkillRun.id)))
        save(output / "runs.json", [{"id": r.id, "skill_version_id": r.skill_version_id, "status": r.status,
            "input_snapshot": r.input_snapshot, "output_parsed": r.output_parsed, "error": r.error,
            "runtime_instruction": r.runtime_instruction, "normalizations": (r.context_snapshot or {}).get("normalizations", []),
            "model_trace": r.model_trace} for r in runs])
        save(output / "request-snapshot.json", request.input_snapshot)
        production_trace = request.input_snapshot.get("production_trace") or {}
        save(output / "summary.json", {**result, "synthetic": True, "database": "isolated-memory",
            "source": str(source_dir), "generation": request.input_snapshot["generation"],
            "calendar_skill_bindings": request.input_snapshot["calendar_skill_bindings"],
            "fixture_report": {"report_case_id": case.id, "report_id": report.id,
                "report_version_id": version.id, "frozen": True,
                "finding_count": len(findings), "action_ids": [row["action_id"] for row in practice_rhythm["actions"]],
                "unavailable_before_scheduling": practice_rhythm["unavailable_actions"]},
            "practice_schedule_audit": schedule_audit,
            "practice_schedule": production_trace.get("practice_schedule", {}),
            "available_minutes_per_day": available_minutes})
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
