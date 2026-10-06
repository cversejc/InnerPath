"""Exercise persisted production and ownership with a deterministic model double."""
import json
from copy import deepcopy
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import JSON, ARRAY, create_engine, select, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.main import app  # imports the full table registry
from app.db.base import Base
from app.models.user import User
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest
from app.domains.calendar.models import CalendarEntry, CalendarRequest, UserCalendar, DecisionLog
from app.domains.calendar.schemas import CalendarRequestCreate
from app.domains.calendar.production import diversify_repeated_suitable, select_tone
from app.domains.calendar.temporal import calculate_temporal_facts
from app.domains.skills.models import SkillRun, AISkillVersion
from app.domains.skills.runtime import ModelCompletion
from app.domains.skills.examples import create_example_candidate, publish_skill_example, update_example_redaction
from app.application.calendar_production import (
    queue_calendar_from_report, execute_calendar_production, retry_calendar_production,
    recover_stalled_calendar_requests,
)
from app.application.report_cases import create_user_service_request, ensure_collaborative_workflow_version
from app.domains.service_requests.schemas import ServiceRequestCreate
from app.domains.service_requests.staff import accept_service_request, list_staff_service_requests, staff_can_access
from app.domains.workflow.models import StepTask
from app.domains.workflow.authorization import validate_step_actor, STEP_SPECIALTIES
from app.domains.workflow.service import create_report_case, start_step, complete_step
from tests.test_workflow_foundation import SyncSessionAdapter


@pytest.fixture
def chain_db(monkeypatch):
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                monkeypatch.setattr(column, "type", JSON())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield SyncSessionAdapter(session)
    engine.dispose()


async def seed_report(db):
    user = User(phone="13800009901", name="合成测试用户", gender="female", birth_year=1990,
                birth_month=5, birth_day=12, birth_hour=9, birth_minute=30, birth_time_precision="exact")
    other = User(phone="13800009902", name="其他用户", gender="female", birth_year=1990, birth_month=5, birth_day=12)
    db.add_all([user, other])
    await db.flush()
    source_request = ServiceRequest(
        user_id=user.id,
        service_type="report",
        status="delivered",
        request_payload={},
        result_type="report",
    )
    db.add(source_request)
    await db.flush()
    report = Report(user_id=user.id, request_id=source_request.id, reviewed_at=datetime.utcnow(),
                    birth_date=date(1990, 5, 12), energy_profile={}, career_guidance={},
                    relationship_pattern={}, personal_growth={}, summary="倾向在工作边界上反复思考，尝试小步验证。",
                    content_payload={"structured_sections": [{"fragment_key": "report.boundary", "content": "工作边界"}],
                        "mingli_foundation": {"bazi": {"day": "丁丑"}, "bazi_facts": {"dayun": [
                            {"pillar": "甲寅", "start_year": 2020, "end_year": 2029}]}}})
    db.add(report)
    await db.flush()
    source_request.result_id = report.id
    db.add(DecisionLog(user_id=user.id, log_date=date(2026, 9, 30), content="完成一次边界沟通"))
    await db.commit()
    data = CalendarRequestCreate(source_report_id=report.id, start_date=date(2026, 10, 4),
        end_date=date(2026, 11, 2), focus_topics=["career"], usage_scenario="daily", goal="明确工作边界",
        expected_outcomes=["action"])
    return user, other, report, data


class CalendarGateway:
    def __init__(self, *, reject=False, bad_source=False):
        self.reject, self.bad_source = reject, bad_source
        self.calls = 0

    async def complete(self, *, system_prompt, user_prompt, model_policy):
        self.calls += 1
        inputs = json.loads(user_prompt)
        facts = {f["entry_date"]: f for f in inputs["temporal_facts"].get("days", [])}
        if "calendar.temporal_analysis" in system_prompt:
            result = {"days": [{"entry_date": d, "primary_theme": "表达沟通", "secondary_theme": "关系边界",
                "psychological_theme": "在实际工作中练习清楚表达边界", "source_refs": ["invented" if self.bad_source else "report.boundary"],
                "dimensions": {key: {"score": 1, "reason": "已审核报告与时序的条件性支持"} for key in
                    ["useful_support", "flow", "interaction_stability", "pattern_regulation"]},
                "windows": [{"period": w["period"], "label": "小步验证", "suggestion": "安排短沟通"}
                            for w in facts[d]["windows"][:2]]} for d in inputs["requested_dates"]]}
        elif "calendar.monthly_tone" in system_prompt:
            result = {"monthly": {key: "先以小步行动验证边界，再按实际反馈调整节奏。" for key in
                ["direction", "growth_task", "resource", "old_pattern", "decision_principle", "rhythm_changes"]}}
        elif "calendar.daily_authoring" in system_prompt:
            analysis = {a["entry_date"]: a for a in inputs["temporal_analysis"]}
            def action_refs(day):
                return inputs["practice_schedule"].get(day, [])

            result = {"entries": [{"entry_date": d, "keyword": "边界、沟通",
                "summary": f"第{d[-2:]}天先记录一件需要澄清的小事，再选择一个轻量沟通动作，并为当天的真实反馈留出复盘空间。",
                "suitable": [f"记录{d}的实际沟通目标", "向相关同事确认一项具体安排"], "unsuitable": [],
                "energy_awareness": f"第{d[-2:]}日复盘时，我是否为表达边界留出了空间？", "tone_explanation": "综合四项条件支持小步推进，仍需核对现实反馈。",
                "windows": analysis[d]["windows"], "action_refs": action_refs(d)} for d in inputs["requested_dates"]]}
        else:
            result = {"approved": not self.reject, "issues": [], "patches": []}
        return ModelCompletion(json.dumps(result, ensure_ascii=False), {"provider": "test", "model": "deterministic"})


@pytest.mark.asyncio
async def test_queued_calendar_pins_versions_publishes_30_days_and_preserves_logs(chain_db):
    db = chain_db
    user, other, report, data = await seed_report(db)
    request = await queue_calendar_from_report(db, user, data)
    assert (await queue_calendar_from_report(db, user, data)).id == request.id
    assert request.input_snapshot["available_minutes_per_day"] == 30
    assert request.input_snapshot["decision_feedback"][0]["content"] == "完成一次边界沟通"
    pins = deepcopy(request.input_snapshot["calendar_skill_bindings"])
    old = await db.get(AISkillVersion, pins["calendar.daily_authoring"]["id"])
    db.add(AISkillVersion(skill_key=old.skill_key, name=old.name, category=old.category, version=old.version + 1,
        status="PUBLISHED", specification_json=deepcopy(old.specification_json), created_by=user.id,
        published_by=user.id, created_at=datetime.utcnow(), published_at=datetime.utcnow()))
    await db.commit()
    gateway = CalendarGateway()
    assert (await execute_calendar_production(db, request.id, 1, gateway=gateway))["status"] == "fulfilled"
    assert gateway.calls == 8
    assert request.input_snapshot["calendar_skill_bindings"] == pins
    assert (await execute_calendar_production(db, request.id, 1, gateway=gateway))["status"] == "stale"
    assert gateway.calls == 8
    calendar = await db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == request.id))
    entries = list(await db.scalars(select(CalendarEntry).where(CalendarEntry.calendar_id == calendar.id)))
    assert len(entries) == 30 and all(e.tone == "green" for e in entries)
    assert set(calendar.meta_payload["daily_details"]) == {e.entry_date.isoformat() for e in entries}
    runs = list(await db.scalars(select(SkillRun).where(SkillRun.target_type == "CALENDAR_PRODUCTION")))
    assert len(runs) == 8 and all(r.status == "COMPLETED" and r.output_raw and r.model_trace for r in runs)
    assert all(r.skill_version_id in {p["id"] for p in pins.values()} for r in runs)
    example = await create_example_candidate(db, report_case_id=None, skill_run=runs[0], example_type="POSITIVE",
        scenario_tags=["boundary"], teaching_points=["基于报告写小步行动"], expected_output=None, created_by=user.id)
    assert example.status == "CANDIDATE" and example.source_skill_run_id == runs[0].id
    assert "phone" not in example.input_context["profile"]
    with pytest.raises(ValueError):
        await publish_skill_example(db, example.id, reviewed_by=user.id)
    await update_example_redaction(db, example_id=example.id, target_fragment_key=None,
        scenario_tags=["career"], applicability_json={"focus_topics": ["career"]},
        input_context={"scenario": "合成工作边界练习"}, expected_output={"method": "依据报告安排小步行动"},
        teaching_points=["保持来源引用，不复制其他人的事实"], anti_patterns=["不凭日期预测事件"],
        quality_score=.9, confirmed_deidentified=True)
    await publish_skill_example(db, example.id, reviewed_by=user.id)
    await db.commit()
    newer_request = await queue_calendar_from_report(db, user, data)
    assert newer_request.input_snapshot["calendar_examples"]["calendar.temporal_analysis"][0]["example_id"] == example.id
    assert request.input_snapshot["calendar_examples"]["calendar.temporal_analysis"] == []
    with pytest.raises(ValueError, match="source_report_not_delivered"):
        await queue_calendar_from_report(db, other, data.model_copy(update={"profile_version": None}))


@pytest.mark.asyncio
async def test_rejected_calibration_never_publishes_and_retry_keeps_snapshot(chain_db):
    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    pins = deepcopy(request.input_snapshot["calendar_skill_bindings"])
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=CalendarGateway(reject=True)))["status"] == "failed"
    assert await chain_db.scalar(select(func.count(UserCalendar.id))) == 0
    failed = await chain_db.scalar(select(SkillRun).where(SkillRun.status == "FAILED"))
    assert failed.output_parsed["approved"] is False and failed.output_raw
    user.name = "更新后的姓名"
    await retry_calendar_production(chain_db, user, request.id)
    assert request.input_snapshot["profile"]["name"] == "合成测试用户"
    assert request.input_snapshot["calendar_skill_bindings"] == pins
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=CalendarGateway()))["status"] == "stale"
    assert (await execute_calendar_production(chain_db, request.id, 2, gateway=CalendarGateway()))["status"] == "fulfilled"
    assert await chain_db.scalar(select(func.count(UserCalendar.id))) == 1
    assert await chain_db.scalar(select(func.count(SkillRun.id))) == 16


@pytest.mark.asyncio
async def test_review_feedback_triggers_rewrite_and_independent_rerun(chain_db):
    class ReviewGateway(CalendarGateway):
        def __init__(self):
            super().__init__()
            self.reviews = 0

        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            if "30天整体校准" in kwargs["system_prompt"]:
                self.reviews += 1
                if self.reviews == 1:
                    return ModelCompletion(json.dumps({"approved": False, "patches": [{"entry_date": "2026-10-04", "summary": "未采用的短修订"}], "issues": [
                        {"code": "REPEATED_ADVICE", "severity": "MAJOR", "entry_date": "2026-10-04", "field_path": "suitable.1",
                         "observed_text": "向相关同事确认一项具体安排", "message": "需要区分行动情境"}]}), {})
            return result

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    gateway = ReviewGateway()
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=gateway))["status"] == "fulfilled"
    assert gateway.reviews == 2 and gateway.calls == 12
    logs = list(await chain_db.scalars(select(SkillRun)))
    assert len(logs) == 12 and sum(r.status == "FAILED" for r in logs) == 1
    assert len(request.input_snapshot["production_trace"]["skill_run_ids"]) == 12
    assert request.input_snapshot["generation"]["completed_runs"] == 12


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_approval", [False, True])
async def test_monthly_review_rewrites_monthly_and_cannot_be_fixed_by_daily_patch(chain_db, initial_approval):
    wrong, corrected = "10月4日为黄色校准日。", "10月4日为绿色推进日，仍需核对现实反馈。"

    class MonthlyReviewGateway(CalendarGateway):
        def __init__(self):
            super().__init__()
            self.monthly_calls = self.daily_calls = self.reviews = 0

        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            inputs = json.loads(kwargs["user_prompt"])
            output = json.loads(result.content)
            if "calendar.monthly_tone" in kwargs["system_prompt"]:
                self.monthly_calls += 1
                if self.monthly_calls == 2:
                    assert inputs["previous_monthly"]["rhythm_changes"] == wrong
                    assert inputs["quality_feedback"][0]["field_path"] == "monthly.rhythm_changes"
                output["monthly"]["rhythm_changes"] = wrong if self.monthly_calls == 1 else corrected
            elif "calendar.daily_authoring" in kwargs["system_prompt"]:
                self.daily_calls += 1
            elif "30天整体校准" in kwargs["system_prompt"]:
                self.reviews += 1
                if self.reviews == 1:
                    output = {"approved": initial_approval,
                        "patches": [inputs["calendar_review_days"][0]] if initial_approval else [],
                        "issues": [{"code": "MONTHLY_COLOR_MISMATCH", "severity": "MAJOR",
                            "entry_date": "2026-10-04", "field_path": "monthly.rhythm_changes",
                            "observed_text": wrong, "message": "固定色块为绿色，需修正月度文案。"}]}
                else:
                    assert inputs["monthly"]["rhythm_changes"] == corrected
            return ModelCompletion(json.dumps(output, ensure_ascii=False), {})

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    gateway = MonthlyReviewGateway()
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=gateway))["status"] == "fulfilled"
    assert (gateway.monthly_calls, gateway.daily_calls, gateway.reviews, gateway.calls) == (2, 3, 2, 10)
    calendar = await chain_db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == request.id))
    assert calendar.meta_payload["monthly"]["rhythm_changes"] == corrected
    assert request.input_snapshot["generation"]["completed_runs"] == 10


@pytest.mark.asyncio
async def test_format_repair_preserves_both_raw_outputs(chain_db):
    class RepairGateway(CalendarGateway):
        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            if self.calls == 5:
                parsed = json.loads(result.content)
                parsed["entries"][0]["windows"][0].pop("label")
                return ModelCompletion(json.dumps(parsed, ensure_ascii=False), {})
            return result

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=RepairGateway()))["status"] == "fulfilled"
    failed = await chain_db.scalar(select(SkillRun).where(SkillRun.status == "FAILED"))
    assert failed.output_raw and failed.error == "calendar_windows_invalid"
    assert len(request.input_snapshot["production_trace"]["skill_run_ids"]) == 9
    repaired = await chain_db.scalar(select(SkillRun).where(SkillRun.idempotency_key.like("%:repair")))
    assert repaired.runtime_instruction and repaired.input_snapshot["previous_output"]


@pytest.mark.asyncio
async def test_duplicate_daily_awareness_is_repaired_before_calibration(chain_db):
    class DuplicateAwarenessGateway(CalendarGateway):
        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            if self.calls == 5:
                output = json.loads(result.content)
                output["entries"][1]["energy_awareness"] = output["entries"][0]["energy_awareness"]
                return ModelCompletion(json.dumps(output, ensure_ascii=False), {})
            return result

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    gateway = DuplicateAwarenessGateway()
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=gateway))["status"] == "fulfilled"
    runs = list(await chain_db.scalars(select(SkillRun).order_by(SkillRun.id)))
    failed = next(run for run in runs if run.status == "FAILED")
    repaired = next(run for run in runs if run.runtime_instruction)
    assert failed.error.startswith("calendar_energy_awareness_repeated:")
    assert "不可只替换日期" in repaired.runtime_instruction
    assert repaired.input_snapshot["previous_output"]["entries"][0]["energy_awareness"] == repaired.input_snapshot["previous_output"]["entries"][1]["energy_awareness"]
    assert len({detail["energy_awareness"] for detail in (
        await chain_db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == request.id))
    ).meta_payload["daily_details"].values()}) == 30
    assert gateway.calls == 9


def test_repeated_suitable_normalization_deduplicates_existing_observation_points():
    repeated = "收到请求时先停顿，再决定是否答应；记录执行前最明显的阻力；记录执行前最明显的阻力。"
    rows = [
        {"entry_date": "2026-10-04", "keyword": "停顿、边界", "suitable": [repeated]},
        {"entry_date": "2026-10-05", "keyword": "协商、反馈", "suitable": [repeated]},
    ]

    changes = diversify_repeated_suitable(rows)

    assert len(changes) == 2
    assert rows[0]["suitable"][0].count("记录执行前最明显的阻力") == 1
    assert rows[1]["suitable"][0].count("记录执行前最明显的阻力") == 1
    assert rows[1]["suitable"][0].endswith("记录执行前最明显的阻力。")


@pytest.mark.asyncio
async def test_short_summary_uses_existing_action_and_records_transformation(chain_db):
    class ShortSummary(CalendarGateway):
        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            if self.calls == 5:
                parsed = json.loads(result.content)
                parsed["entries"][0]["summary"] = "今天先把工作边界说清楚。"
                return ModelCompletion(json.dumps(parsed, ensure_ascii=False), {})
            if "30天整体校准" in kwargs["system_prompt"]:
                reviewed = json.loads(kwargs["user_prompt"])["calendar_review_days"][0]
                assert 30 <= len(reviewed["summary"]) <= 60
            return result

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=ShortSummary()))["status"] == "fulfilled"
    run = await chain_db.scalar(select(SkillRun).where(SkillRun.idempotency_key.like("%daily_authoring:0")))
    assert json.loads(run.output_raw)["entries"][0]["summary"] == "今天先把工作边界说清楚。"
    change = run.context_snapshot["normalizations"][0]
    assert change["before"] != change["after"] == run.output_parsed["entries"][0]["summary"]
    assert change["rule"] == "append_existing_suitable_action"


@pytest.mark.asyncio
@pytest.mark.parametrize("correct_review", [True, False])
async def test_calibration_requires_quotes_from_actual_user_prose(chain_db, correct_review):
    class UngroundedReview(CalendarGateway):
        async def complete(self, **kwargs):
            result = await super().complete(**kwargs)
            if "30天整体校准" in kwargs["system_prompt"]:
                if self.calls == 8 or not correct_review:
                    return ModelCompletion(json.dumps({"approved": False, "patches": [], "issues": [{
                        "severity": "BLOCK", "code": "MISREAD_FACT", "entry_date": "2026-10-04",
                        "field_path": "facts.month_pillar", "observed_text": "未存在的文案", "message": "没有实际文案佐证"}]}), {})
                assert "calendar_calibration_evidence_invalid" in kwargs["system_prompt"]
            return result

    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    result = await execute_calendar_production(chain_db, request.id, 1, gateway=UngroundedReview())
    assert result["status"] == ("fulfilled" if correct_review else "failed")
    assert await chain_db.scalar(select(func.count(UserCalendar.id))) == (1 if correct_review else 0)
    failed = await chain_db.scalar(select(SkillRun).where(SkillRun.status == "FAILED"))
    assert failed.output_raw and failed.error == "calendar_calibration_evidence_invalid"


@pytest.mark.asyncio
async def test_invented_sources_and_stalled_worker_do_not_publish(chain_db):
    user, _, _, data = await seed_report(chain_db)
    request = await queue_calendar_from_report(chain_db, user, data)
    assert (await execute_calendar_production(chain_db, request.id, 1, gateway=CalendarGateway(bad_source=True)))["status"] == "failed"
    assert await chain_db.scalar(select(func.count(UserCalendar.id))) == 0
    await retry_calendar_production(chain_db, user, request.id)
    from app.domains.skills.service import create_skill_run
    orphan, _ = await create_skill_run(chain_db,
        skill_version_id=request.input_snapshot["calendar_skill_bindings"]["calendar.temporal_analysis"]["id"],
        idempotency_key="orphaned-calendar-run", input_snapshot={}, context_snapshot={},
        target_type="CALENDAR_PRODUCTION", target_key=str(request.id))
    orphan.status = "RUNNING"
    request.status, request.updated_at = "generating", datetime.utcnow() - timedelta(hours=1)
    await chain_db.commit()
    assert await recover_stalled_calendar_requests(chain_db) == 1
    assert request.status == "failed"
    assert orphan.status == "FAILED" and orphan.error == "calendar_worker_interrupted" and orphan.completed_at


@pytest.mark.asyncio
async def test_two_specialties_accept_and_hand_off_sequential_steps(chain_db):
    db = chain_db
    user, _, _, _ = await seed_report(db)
    mingli = User(phone="13800009903", name="命理", role="consultant", consultant_type="mingli")
    psychology = User(phone="13800009904", name="心理", role="consultant", consultant_type="psychology")
    competing = User(phone="13800009905", name="另一命理", role="consultant", consultant_type="mingli")
    db.add_all([mingli, psychology, competing])
    await db.flush()
    request, case = await create_user_service_request(db, user, ServiceRequestCreate(service_type="report",
        profile={"gender": "female", "birth_year": 1990, "birth_month": 5, "birth_day": 12},
        context={"current_challenge": "测试工作边界", "focus_topics": ["career"],
                 "expected_outcomes": ["明确下一步"]}, idempotency_key="chain-request-1"))
    expected_specialties = {
        "S1": "mingli", "S2": "mingli", "S3": "mingli",
        "S4": "psychology", "S5": "psychology", "S6": "psychology",
    }
    assert STEP_SPECIALTIES == expected_specialties
    assert case.application_snapshot["collaboration_contract"]["version"] == "professional-handoff-v2"
    assert case.application_snapshot["collaboration_contract"]["step_specialties"] == expected_specialties
    await accept_service_request(db, request.id, mingli)
    assert any(r.id == request.id for r, _ in await list_staff_service_requests(db, psychology, scope="available"))
    await accept_service_request(db, request.id, psychology)
    with pytest.raises(ValueError, match="already_taken"):
        await accept_service_request(db, request.id, competing)
    assert staff_can_access(request, mingli) and staff_can_access(request, psychology)
    steps = list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id).order_by(StepTask.sequence_no)))
    for step in steps:
        actor = mingli if STEP_SPECIALTIES[step.step_key] == "mingli" else psychology
        wrong = psychology if actor == mingli else mingli
        assert step.required_capability == actor.consultant_type and step.assignee_id == actor.id
        validate_step_actor(step, actor)
        with pytest.raises(ValueError, match="step_specialty_required"):
            validate_step_actor(step, wrong)
    await start_step(db, case.id, "S1")
    await complete_step(db, case.id, "S1", result_json={"professional_review": "test fixture"})
    assert steps[1].status == "READY" and steps[1].assignee_id == mingli.id
    assert not any(r.id == request.id for r, _ in await list_staff_service_requests(db, competing, scope="available"))


@pytest.mark.asyncio
async def test_stale_collaboration_contract_is_versioned_for_new_cases(chain_db):
    db = chain_db
    user, _, _, _ = await seed_report(db)
    previous = await ensure_collaborative_workflow_version(db)

    # Simulate a database whose latest published collaboration version predates
    # the diagram: S2 was psychology-owned in professional-handoff-v1.
    stale_definition = deepcopy(previous.definition_json)
    stale_definition["collaboration_contract"] = {
        "version": "professional-handoff-v1",
        "step_specialties": {
            "S1": "mingli", "S2": "psychology", "S3": "mingli",
            "S4": "psychology", "S5": "psychology", "S6": "psychology",
        },
    }
    for step in stale_definition["steps"]:
        step["required_capability"] = stale_definition["collaboration_contract"]["step_specialties"][step["step_key"]]
    previous.definition_json = stale_definition
    await db.commit()

    current = await ensure_collaborative_workflow_version(db)
    assert current.id != previous.id
    assert previous.definition_json["collaboration_contract"]["step_specialties"]["S2"] == "psychology"
    assert current.definition_json["collaboration_contract"]["version"] == "professional-handoff-v2"
    assert current.definition_json["collaboration_contract"]["step_specialties"]["S2"] == "mingli"

    old_case = await create_report_case(
        db,
        user_id=user.id,
        service_request_id=None,
        source_report_task_id="legacy-case",
        application_snapshot={},
        workflow_version=previous,
    )
    new_case = await create_report_case(
        db,
        user_id=user.id,
        service_request_id=None,
        source_report_task_id="new-case",
        application_snapshot={},
        workflow_version=current,
    )
    old_s2 = await db.scalar(select(StepTask).where(
        StepTask.workflow_instance_id == old_case.workflow_instance_id,
        StepTask.step_key == "S2",
    ))
    new_s2 = await db.scalar(select(StepTask).where(
        StepTask.workflow_instance_id == new_case.workflow_instance_id,
        StepTask.step_key == "S2",
    ))
    assert old_s2.required_capability == "psychology"
    assert new_s2.required_capability == "mingli"


def test_temporal_engine_and_weighted_colors_keep_missing_data_honest():
    facts = calculate_temporal_facts(date(2026, 10, 4), {})
    assert len(facts["days"]) == 30 and facts["limitations"]
    assert facts["days"][0]["windows"][0]["period"] == "06:00–07:00"
    assert facts["days"][-1]["windows"][-1]["period"] == "23:00–24:00"
    crossing = facts["days"][4]
    transition = next(t for t in crossing["solar_term_transitions"] if t["before"]["month_pillar"] != t["after"]["month_pillar"])
    assert crossing["reference_time"] == "12:00:00"
    assert transition["before"]["month_pillar"] == crossing["month_pillar"] == "丁酉"
    assert transition["after"]["month_pillar"] == "戊戌"
    weights = {k: .25 for k in ["useful_support", "flow", "interaction_stability", "pattern_regulation"]}
    for score, tone in [(1, "green"), (.3, "blue"), (-.3, "yellow"), (-1, "red")]:
        dimensions = {k: {"score": score, "reason": "综合依据"} for k in weights}
        assert select_tone(dimensions, weights)[0] == tone
        assert select_tone(dimensions, weights, degraded=True)[0] == "yellow"


@pytest.mark.asyncio
async def test_public_endpoints_return_queue_progress_and_only_owner_calendar(chain_db):
    import httpx
    from app.db.session import get_db
    from app.dependencies import get_current_active_user

    user, other, report, data = await seed_report(chain_db)
    actor = user

    async def database():
        yield chain_db

    async def current_user():
        return actor

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_active_user] = current_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            submitted = await client.post("/api/v1/calendar/requests", json=data.model_dump(mode="json"))
            assert submitted.status_code == 202, submitted.text
            assert submitted.json()["status"] == "queued"
            assert submitted.json()["available_minutes_per_day"] == 30
            request_id = submitted.json()["id"]
            assert (await execute_calendar_production(chain_db, request_id, 1, gateway=CalendarGateway()))["status"] == "fulfilled"
            progress = (await client.get("/api/v1/calendar/requests")).json()["items"][0]
            assert progress["completed_runs"] == 8 and progress["calendar_id"]
            assert progress["available_minutes_per_day"] == 30
            calendars = await client.get("/api/v1/calendar/me")
            assert calendars.status_code == 200 and len(calendars.json()["items"][0]["entries"]) == 30
            actor = other
            assert (await client.get("/api/v1/calendar/me")).json()["items"] == []
            assert (await client.post("/api/v1/calendar/requests", json=data.model_dump(mode="json"))).status_code == 422
            assert (await client.post(f"/api/v1/calendar/requests/{request_id}/retry")).status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delivered_version_is_calendar_source_and_links_logs_to_case(chain_db, monkeypatch):
    """Exercise the user-to-consultant-to-report-to-calendar API chain.

    The analysis assets and completed QA run are a synthetic, pre-reviewed
    professional fixture; the HTTP workflow, final attestation, delivery,
    customer report read, calendar request, and calendar production are real.
    """
    from unittest.mock import AsyncMock
    import httpx
    from app.application import report_delivery
    from app.domains.content.models import CaseEvidenceItem, FindingRevision, NarrativePlan, ContentFragmentRevision
    from app.domains.service_requests.models import ServiceRequest
    from app.domains.workflow.models import WorkflowInstance
    from app.domains.skills.service import create_skill_run
    from app.domains.calendar.context import calendar_model_context
    from app.db.session import get_db
    from app.dependencies import get_current_active_user

    db = chain_db
    user, other, _, data = await seed_report(db)
    mingli = User(phone="13800009911", name="合成命理", role="consultant", consultant_type="mingli")
    psychology = User(phone="13800009912", name="合成心理", role="consultant", consultant_type="psychology")
    admin = User(phone="13800009913", name="合成管理员", role="admin")
    db.add_all([mingli, psychology, admin])
    await db.flush()
    actor = user

    async def database():
        yield db

    async def current_user():
        return actor

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_active_user] = current_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            submitted = await client.post("/api/v1/service-requests", json={
                "service_type": "report",
                "profile": {"gender": "female", "birth_year": 1990, "birth_month": 5, "birth_day": 12},
                "context": {"current_challenge": "测试边界", "focus_topics": ["career"],
                            "expected_outcomes": ["明确下一步"]},
                "idempotency_key": "delivered-chain-http",
            })
            assert submitted.status_code == 201, submitted.text
            request_id = submitted.json()["id"]
            from app.domains.workflow.models import ReportCase
            request = await db.get(ServiceRequest, request_id)
            case = await db.scalar(select(ReportCase).where(ReportCase.service_request_id == request_id))
            assert request is not None and case is not None

            actor = mingli
            accepted_mingli = await client.post(f"/api/v1/staff/service-requests/{request_id}/accept")
            assert accepted_mingli.status_code == 200, accepted_mingli.text
            actor = psychology
            accepted_psychology = await client.post(f"/api/v1/staff/service-requests/{request_id}/accept")
            assert accepted_psychology.status_code == 200, accepted_psychology.text
            assert accepted_psychology.json()["assigned_mingli_consultant_id"] == mingli.id
            assert accepted_psychology.json()["assigned_psychology_consultant_id"] == psychology.id

            skill_id = case.application_snapshot["skill_bindings"]["report.narrative_plan"]["id"]
            source_run, _ = await create_skill_run(db, skill_version_id=skill_id,
                idempotency_key="delivered-fixture", input_snapshot={}, context_snapshot={}, report_case_id=case.id)
            source_run.status = "COMPLETED"
            now = datetime.utcnow()
            foundation = {"bazi": {"day": "丁丑"}, "bazi_facts": {"dayun": [
                {"pillar": "甲寅", "start_year": 2020, "end_year": 2029}]}}
            db.add(CaseEvidenceItem(report_case_id=case.id, evidence_key="reviewed.chart", source_type="SYSTEM_CALCULATED",
                source_ref="reviewed-fixture", value_json=foundation, status="ACTIVE", created_at=now))
            db.add(FindingRevision(report_case_id=case.id, finding_key="finding.boundary", revision_no=1,
                semantic_revision=1, content_revision=1, semantic_role="RESOURCE", claim="小步验证工作边界",
                confidence="MEDIUM", importance="MEDIUM", reportability="RECOMMENDED", status="CONFIRMED",
                evidence_refs=["reviewed.chart"], structured_data_json={"action_experiment": "先协商一项具体分工"}, created_at=now))
            db.add(FindingRevision(report_case_id=case.id, finding_key="finding.block", revision_no=1,
                semantic_revision=1, content_revision=1, semantic_role="BLOCK", claim="表达边界前反复准备",
                confidence="MEDIUM", importance="HIGH", reportability="MUST_INCLUDE", status="CONFIRMED",
                evidence_refs=["reviewed.chart"], structured_data_json={}, created_at=now))
            db.add(FindingRevision(report_case_id=case.id, finding_key="zz.action.boundary", revision_no=1,
                semantic_revision=1, content_revision=1, semantic_role="ACTION", claim="每周做一次低风险边界沟通",
                confidence="MEDIUM", importance="MEDIUM", reportability="RECOMMENDED", status="CONFIRMED",
                evidence_refs=["reviewed.chart"], structured_data_json={
                    "frequency": "weekly", "duration_minutes": 15,
                    "steps": ["写下一句边界表达", "选择一次低风险沟通"], "method": "小步沟通",
                    "observation": "记录对方实际回应", "stop_rule": "感到不安全时暂停",
                    "block_refs": ["finding.block"], "reasoning_path": {
                        "resource_refs": ["finding.boundary"], "regulation_function": "降低准备成本",
                        "capacity": "清晰表达", "reality_gap": "表达前容易反复准备",
                        "integration_task": "兼顾关系与边界", "tool": "小步沟通",
                        "rationale": "从低风险情境开始",
                    },
                }, created_at=now))
            plan = NarrativePlan(report_case_id=case.id, version_no=1, status="CONFIRMED",
                selected_skill_run_id=source_run.id, selected_candidate_key="fixture", plan_json={"core_theme": "已签核的边界主题"},
                source_snapshot={}, created_at=now, confirmed_at=now)
            db.add(plan)
            await db.flush()
            db.add(ContentFragmentRevision(report_case_id=case.id, fragment_key="report.boundary", revision_no=1,
                semantic_revision=1, content_revision=1, fragment_type="REPORT", title="工作边界", content="先协商一项具体分工。",
                status="CONFIRMED", source_snapshot={}, source_narrative_plan_id=plan.id, source_skill_run_id=source_run.id,
                created_at=now))
            steps = list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id)))
            for step in steps:
                if step.step_key == "S6":
                    step.status = "IN_REVIEW"
                    step.started_at = now
                else:
                    step.status = "COMPLETED"
                    step.completed_at = now
            instance = await db.get(WorkflowInstance, case.workflow_instance_id)
            instance.status, case.status = "RUNNING", "ACTIVE"
            validator_id = case.application_snapshot["skill_bindings"]["report.final_validator"]["id"]
            validator, _ = await create_skill_run(db, skill_version_id=validator_id,
                idempotency_key="delivered-qa-fixture", input_snapshot={}, context_snapshot={"qa_fingerprint": "fixture-approved"},
                run_type="VALIDATE", target_type="REPORT_QA", target_key="report.final", report_case_id=case.id,
                workflow_instance_id=case.workflow_instance_id)
            validator.status, validator.output_raw, validator.output_parsed = "COMPLETED", "{}", {"approved": True}
            validator.completed_at = now
            await db.commit()

            monkeypatch.setattr(report_delivery, "case_can_be_delivered", AsyncMock(return_value=True))
            monkeypatch.setattr(report_delivery, "delivery_quality_snapshot", AsyncMock(return_value={"can_approve": True}))
            actor = mingli
            denied = await client.post(f"/api/v1/report-cases/{case.id}/final-gate/approve", json={"attested": True})
            assert denied.status_code == 403 and denied.json()["detail"] == "step_specialty_required"
            actor = psychology
            approved = await client.post(f"/api/v1/report-cases/{case.id}/final-gate/approve", json={
                "attested": True, "note": "合成测试：已完成心理侧最终复核",
            })
            assert approved.status_code == 200 and approved.json()["status"] == "COMPLETED"
            delivered_response = await client.post(f"/api/v1/report-cases/{case.id}/deliver")
            assert delivered_response.status_code == 200, delivered_response.text
            version = delivered_response.json()
            assert version["structured_data"]["structured_sections"][0]["fragment_key"] == "report.boundary"
            delivered = await db.get(Report, request.result_id)
            assert case.status == "DELIVERED" and request.status == "delivered"
            assert version["id"] == delivered.input_snapshot["report_version"]["id"]

            actor = user
            user_report = await client.get(f"/api/v1/reports/{delivered.id}")
            assert user_report.status_code == 200 and user_report.json()["id"] == delivered.id
            assert user_report.json()["content_payload"]["structured_sections"][0]["content"] == "先协商一项具体分工。"

            actor = admin
            admin_case = await client.get(f"/api/v1/report-cases/{case.id}")
            assert admin_case.status_code == 200 and admin_case.json()["id"] == case.id
            admin_report = await client.get(f"/api/v1/reports/{delivered.id}")
            assert admin_report.status_code == 200 and admin_report.json()["id"] == delivered.id

            # The mutable user-facing projection must never overwrite the signed snapshot.
            delivered.summary = "后来改写的投影"
            delivered.content_payload = {"structured_sections": [{"fragment_key": "changed", "content": "changed"}]}
            await db.commit()
            calendar_data = data.model_copy(update={"source_report_id": delivered.id})
            actor = user
            calendar_response = await client.post("/api/v1/calendar/requests", json=calendar_data.model_dump(mode="json"))
            assert calendar_response.status_code == 202, calendar_response.text
            calendar_request_id = calendar_response.json()["id"]
            assert calendar_response.json()["status"] == "queued"
            calendar_request = await db.get(CalendarRequest, calendar_request_id)
            source = calendar_request.input_snapshot["source_report"]
            assert source["summary"] == "已签核的边界主题"
            assert source["reviewed_foundation"] == foundation and source["report_version_id"] == version["id"]
            assert source["practice_rhythm"]["report_version_id"] == version["id"]
            assert [action["action_id"] for action in source["practice_rhythm"]["actions"]] == ["zz.action.boundary"]
            projected = calendar_model_context(calendar_request.input_snapshot,
                calculate_temporal_facts(calendar_data.start_date, foundation))
            assert any(f["structured_data"].get("action_experiment")
                for f in projected["source_report"]["confirmed_semantics"]["findings"])
            assert (await execute_calendar_production(db, calendar_request.id, 1, gateway=CalendarGateway()))["status"] == "fulfilled"
            progress = (await client.get("/api/v1/calendar/requests")).json()["items"][0]
            assert progress["id"] == calendar_request.id and progress["completed_runs"] == 8
            calendars = await client.get("/api/v1/calendar/me")
            assert calendars.status_code == 200 and len(calendars.json()["items"][0]["entries"]) == 30
            calendar = await db.scalar(select(UserCalendar).where(UserCalendar.calendar_request_id == calendar_request.id))
            assert calendar.meta_payload["source_report_version_id"] == version["id"]
            assert calendar.meta_payload["practice_rhythm"]["report_version_id"] == version["id"]
            assert sum(details["action_refs"] == ["zz.action.boundary"]
                for details in calendar.meta_payload["daily_details"].values()) == 5
            runs = list(await db.scalars(select(SkillRun).where(SkillRun.target_type == "CALENDAR_PRODUCTION")))
            assert len(runs) == 8 and all(run.report_case_id == case.id for run in runs)
            actor = admin
            admin_requests = await client.get(
                "/api/v1/admin/calendar-requests", params={"user_id": user.id}
            )
            assert admin_requests.status_code == 200
            assert any(item["id"] == calendar_request.id for item in admin_requests.json()["items"])
            admin_calendars = await client.get(
                f"/api/v1/admin/users/{user.id}/calendars"
            )
            assert admin_calendars.status_code == 200
            assert any(item["id"] == calendar.id for item in admin_calendars.json()["items"])
            actor = other
            assert (await client.get(f"/api/v1/reports/{delivered.id}")).status_code == 404
            assert (await client.get("/api/v1/calendar/me")).json()["items"] == []
            assert (await client.post("/api/v1/calendar/requests",
                json=calendar_data.model_dump(mode="json"))).status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_http_application_dual_acceptance_and_step_permissions(chain_db):
    import httpx
    from app.db.session import get_db
    from app.dependencies import get_current_active_user
    from app.domains.content.models import CaseEvidenceItem
    from app.domains.service_requests.models import ServiceRequest
    from app.domains.skills.service import create_skill_run
    from app.domains.workflow.models import ReportCase, WorkflowInstance

    user, other, _, _ = await seed_report(chain_db)
    mingli = User(phone="13800009921", name="命理接口测试", role="consultant", consultant_type="mingli")
    psychology = User(phone="13800009922", name="心理接口测试", role="consultant", consultant_type="psychology")
    chain_db.add_all([mingli, psychology])
    await chain_db.commit()
    actor = user

    async def database():
        yield chain_db

    async def current_user():
        return actor

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_active_user] = current_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            submitted = await client.post("/api/v1/service-requests", json={"service_type": "report",
                "profile": {"gender": "female", "birth_year": 1990, "birth_month": 5, "birth_day": 12},
                "context": {"current_challenge": "工作边界", "focus_topics": ["career"],
                            "expected_outcomes": ["明确下一步"]}, "idempotency_key": "http-chain"})
            assert submitted.status_code == 201, submitted.text
            request_id = submitted.json()["id"]
            case = await chain_db.scalar(select(ReportCase).where(ReportCase.service_request_id == request_id))
            actor = mingli
            assert (await client.post(f"/api/v1/staff/service-requests/{request_id}/accept")).status_code == 200
            actor = psychology
            available = (await client.get("/api/v1/staff/service-requests?scope=available")).json()
            assert any(item["id"] == request_id for item in available["items"])
            accepted = await client.post(f"/api/v1/staff/service-requests/{request_id}/accept")
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["assigned_mingli_consultant_id"] == mingli.id
            assert accepted.json()["assigned_psychology_consultant_id"] == psychology.id
            denied = await client.post(f"/api/v1/report-cases/{case.id}/steps/S1/start")
            assert denied.status_code == 403 and denied.json()["detail"] == "step_specialty_required"
            assert (await client.get(f"/api/v1/staff/service-requests/{request_id}")).status_code == 200
            actor = mingli
            started = await client.post(f"/api/v1/report-cases/{case.id}/steps/S1/start")
            assert started.status_code == 200 and started.json()["status"] == "IN_REVIEW"

            step = await chain_db.scalar(select(StepTask).where(
                StepTask.workflow_instance_id == case.workflow_instance_id,
                StepTask.step_key == "S1",
            ))
            original_activation = step.activation_no
            pending_run, _ = await create_skill_run(
                chain_db,
                skill_version_id=case.application_snapshot["skill_bindings"]["report.s1_foundation_analysis"]["id"],
                idempotency_key="pending-before-report-follow-up",
                input_snapshot={},
                context_snapshot={},
                run_type="INITIAL",
                target_type="REPORT_ANALYSIS_DRAFT",
                target_key="S1",
                report_case_id=case.id,
                workflow_instance_id=case.workflow_instance_id,
                step_task_id=step.id,
            )
            await chain_db.commit()
            blocked_info_request = await client.post(
                f"/api/v1/report-cases/{case.id}/steps/S1/request-info",
                json={"reason": "等待中的技能任务必须先完成"},
            )
            assert blocked_info_request.status_code == 409
            assert blocked_info_request.json()["detail"] == "report_case_skill_run_in_progress"
            still_active_request = await chain_db.get(ServiceRequest, request_id)
            assert still_active_request.status == "accepted" and case.status == "ACTIVE"
            pending_run.status = "FAILED"
            await chain_db.commit()

            original_snapshot = deepcopy(case.application_snapshot)
            question = "最近的工作边界冲突具体发生在什么情境？"
            requested_info = await client.post(
                f"/api/v1/report-cases/{case.id}/steps/S1/request-info",
                json={"reason": question},
            )
            assert requested_info.status_code == 200, requested_info.text
            assert requested_info.json()["status"] == "needs_info"
            request = await chain_db.get(ServiceRequest, request_id)
            instance = await chain_db.get(WorkflowInstance, case.workflow_instance_id)
            step = await chain_db.scalar(select(StepTask).where(
                StepTask.workflow_instance_id == case.workflow_instance_id,
                StepTask.step_key == "S1",
            ))
            assert request.needs_info_reason == question
            assert case.status == "BLOCKED" and instance.status == "SUSPENDED"
            assert step.status == "IN_REVIEW"

            blocked_action = await client.post(f"/api/v1/report-cases/{case.id}/steps/S1/start")
            assert blocked_action.status_code == 409
            assert blocked_action.json()["detail"] == "report_case_waiting_for_user_info"
            blocked_skill = await client.post(
                f"/api/v1/report-cases/{case.id}/steps/S1/analysis-drafts",
                json={"idempotency_key": "blocked-report-analysis"},
            )
            assert blocked_skill.status_code == 409
            assert blocked_skill.json()["detail"] == "report_case_waiting_for_user_info"
            actor = other
            denied_supplement = await client.post(
                f"/api/v1/report-cases/{case.id}/supplements",
                json={"response_key": "other-user-reply-1", "answer": "无权查看的回复"},
            )
            assert denied_supplement.status_code == 404

            actor = user
            answer = "冲突主要发生在临时增加工作任务时，我通常会先答应再感到压力。"
            supplement_payload = {"response_key": "report-user-reply-001", "answer": answer}
            supplemented = await client.post(
                f"/api/v1/report-cases/{case.id}/supplements", json=supplement_payload
            )
            assert supplemented.status_code == 200, supplemented.text
            supplement = supplemented.json()
            assert supplement["status"] == "accepted"
            assert supplement["step_key"] == "S1"
            assert supplement["evidence_key"] == "user.follow_up.001"
            assert case.application_snapshot == original_snapshot
            assert case.status == "ACTIVE" and instance.status == "RUNNING"
            assert step.status == "IN_REVIEW"
            assert step.activation_no == original_activation + 1
            evidence = await chain_db.scalar(select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == case.id,
                CaseEvidenceItem.evidence_key == supplement["evidence_key"],
            ))
            assert evidence.source_type == "USER_PROVIDED"
            assert evidence.value_json == {"question": question, "answer": answer, "step_key": "S1"}
            assert request.request_payload["report_case_supplements"][0]["evidence_key"] == evidence.evidence_key

            duplicate = await client.post(
                f"/api/v1/report-cases/{case.id}/supplements", json=supplement_payload
            )
            assert duplicate.status_code == 200
            assert duplicate.json()["evidence_key"] == evidence.evidence_key
            assert await chain_db.scalar(select(func.count(CaseEvidenceItem.id)).where(
                CaseEvidenceItem.report_case_id == case.id,
                CaseEvidenceItem.evidence_key == evidence.evidence_key,
            )) == 1
            conflicting_retry = await client.post(
                f"/api/v1/report-cases/{case.id}/supplements",
                json={"response_key": "report-user-reply-001", "answer": "不同答案"},
            )
            assert conflicting_retry.status_code == 409
            assert conflicting_retry.json()["detail"] == "report_case_supplement_idempotency_conflict"

            actor = mingli
            second_question = "你提到先答应，之后通常会如何影响休息或关系？"
            requested_again = await client.post(
                f"/api/v1/report-cases/{case.id}/steps/S1/request-info",
                json={"reason": second_question},
            )
            assert requested_again.status_code == 200, requested_again.text
            actor = user
            second_answer = "那周会减少休息时间，也会担心拒绝后影响合作。"
            second_supplement = await client.post(
                f"/api/v1/report-cases/{case.id}/supplements",
                json={"response_key": "report-user-reply-002", "answer": second_answer},
            )
            assert second_supplement.status_code == 200, second_supplement.text
            assert second_supplement.json()["evidence_key"] == "user.follow_up.002"
            assert step.activation_no == original_activation + 2
            assert len(request.request_payload["report_case_supplements"]) == 2
            second_evidence = await chain_db.scalar(select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == case.id,
                CaseEvidenceItem.evidence_key == "user.follow_up.002",
            ))
            assert second_evidence.value_json == {
                "question": second_question,
                "answer": second_answer,
                "step_key": "S1",
            }

            actor = mingli
            resumed_case = await client.get(f"/api/v1/report-cases/{case.id}")
            assert resumed_case.status_code == 200
            resumed_step = next(item for item in resumed_case.json()["workflow_instance"]["steps"]
                                if item["step_key"] == "S1")
            assert resumed_step["status"] == "IN_REVIEW"
            report_content = await client.get(f"/api/v1/report-cases/{case.id}/content")
            assert report_content.status_code == 200
            assert any(item["evidence_key"] == evidence.evidence_key for item in report_content.json()["evidence"])
    finally:
        app.dependency_overrides.clear()
