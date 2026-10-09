"""Seed durable, synthetic consultant workbench and Skill Studio examples.

Run inside the development backend container after migrations:
    python -m tools.seed_consultant_demo

This command only creates missing demo records. It has no reset or cleanup mode.
"""

import asyncio
import json
import logging
from copy import deepcopy
from datetime import date, datetime
from app.core.time import utc_now_naive, shanghai_today
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.application.report_cases import (
    create_user_service_request,
    ensure_default_workflow_version,
)
from app.application.report_delivery import deliver_report_case
from app.application.report_quality import quality_state
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.domains.content.findings import current_finding, create_finding_revision
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    NarrativePlan,
)
from app.domains.content.narrative import (
    confirm_narrative_plan,
    get_current_narrative_plan,
    semantic_source_snapshot,
)
from app.domains.content.queries import load_case_semantic_model
from app.domains.quality.models import QAIssue
from app.domains.quality.programmatic import collect_programmatic_issues
from app.domains.quality.service import run_programmatic_qa
from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.schemas import ServiceRequestCreate
from app.domains.workflow.definitions import DEFAULT_WORKFLOW_KEY
from app.domains.skills.definitions import default_validator_skill_specification
from app.domains.skills.evaluation import (
    evaluate_regression_output,
    load_regression_dataset,
    regression_cases,
    specification_digest,
)
from app.domains.skills.models import AISkillVersion, SkillExample, SkillRun
from app.domains.skills.lifecycle import RETIRED_SKILL_KEYS
from app.domains.skills.service import (
    create_skill_draft,
    create_skill_run,
    ensure_default_narrative_skill_versions,
    ensure_default_validator_skill_version,
)
from app.domains.workflow.models import ReportCase, StepTask
from app.domains.workflow.service import complete_step, start_step
from app.models.user import User


ADMIN_PHONE = "19900000001"
CONSULTANT_PHONE = "19900000002"
CONSULTANT_NAME = "辰鉴演示咨询师"
DEMO_DRAFT_NAME = "报告语义质量审核 · 演示草稿"

REPORT_SCENARIOS = [
    {
        "key": "node-s1",
        "phone": "19900000101",
        "name": "演示用户 · S1 基础结构",
        "target_step": 1,
        "assigned": True,
        "challenge": "希望理解自己的工作节奏和长期优势。",
        "topics": ["career", "growth"],
    },
    {
        "key": "node-s2",
        "phone": "19900000102",
        "name": "演示用户 · S2 心理映射",
        "target_step": 2,
        "assigned": True,
        "challenge": "在稳定工作与新方向之间反复权衡。",
        "topics": ["career", "decision"],
    },
    {
        "key": "node-s3",
        "phone": "19900000103",
        "name": "演示用户 · S3 整合判断",
        "target_step": 3,
        "assigned": True,
        "challenge": "想把自我观察和现实选择连接起来。",
        "topics": ["growth", "career"],
    },
    {
        "key": "node-s4",
        "phone": "19900000104",
        "name": "演示用户 · S4 行动策略",
        "target_step": 4,
        "assigned": True,
        "challenge": "方向较多，希望确定一个可验证的小步骤。",
        "topics": ["decision", "growth"],
    },
    {
        "key": "node-s5",
        "phone": "19900000105",
        "name": "演示用户 · S5 报告撰写",
        "target_step": 5,
        "assigned": True,
        "challenge": "希望把已确认的判断组织成清晰、克制的报告。",
        "topics": ["career", "growth"],
    },
    {
        "key": "node-s6-blocked",
        "phone": "19900000106",
        "name": "演示用户 · S6 QA 阻断",
        "target_step": 6,
        "assigned": True,
        "qa_mode": "blocked",
        "challenge": "希望理解判断依据，并得到可以实践的建议。",
        "topics": ["decision", "growth"],
    },
    {
        "key": "node-s6-ready",
        "phone": "19900000107",
        "name": "演示用户 · S6 待最终审核",
        "target_step": 6,
        "assigned": True,
        "qa_mode": "ready",
        "challenge": "希望确认一份来源完整、行动具体的报告。",
        "topics": ["career", "decision"],
    },
    {
        "key": "history-delivered",
        "phone": "19900000108",
        "name": "演示用户 · 已交付报告",
        "target_step": 6,
        "assigned": True,
        "qa_mode": "delivered",
        "challenge": "希望回看已经完成的报告交付记录。",
        "topics": ["growth", "career"],
    },
    {
        "key": "report-intake",
        "phone": "19900000109",
        "name": "演示用户 · 待接单报告",
        "target_step": 1,
        "assigned": False,
        "activate_current": False,
        "challenge": "希望了解如何把近期的职业选择拆成几个小实验。",
        "topics": ["career", "decision"],
    },
]

CALENDAR_SCENARIOS = [
    {
        "key": "calendar-intake",
        "phone": "19900000110",
        "name": "演示用户 · 待接单日历",
        "status": "submitted",
        "assigned": False,
        "challenge": "为接下来一个月安排求职和休息的节奏。",
    },
    {
        "key": "calendar-needs-info",
        "phone": "19900000111",
        "name": "演示用户 · 待补充资料",
        "status": "needs_info",
        "assigned": True,
        "challenge": "为项目切换安排一个可复盘的 30 天行动计划。",
    },
]

FINDING_DEFINITIONS = [
    {
        "key": "foundation.balance",
        "owner_step": 1,
        "role": "CAREER_PATTERN",
        "claim": "用户倾向在建立稳定结构后，再逐步扩大探索范围。",
    },
    {
        "key": "finding.stability-autonomy",
        "owner_step": 2,
        "role": "MOTIVATION_PATTERN",
        "claim": "自主空间和可预期的协作边界，都是用户评估工作环境时在意的条件。",
    },
    {
        "key": "finding.small-step",
        "owner_step": 3,
        "role": "INTEGRATED_INSIGHT",
        "claim": "把选择缩小为短周期实验，有助于同时保留安全感和行动主动性。",
    },
    {
        "key": "finding.demo.action",
        "owner_step": 4,
        "role": "ACTION_STRATEGY",
        "claim": "先访谈一位从业者并完成一个小样本任务，再决定是否扩大投入。",
    },
]

REQUIRED_REPORT_SECTIONS = [
    {
        "key": "report.identity",
        "title": "你是谁",
        "content": "你会先建立清晰的工作结构，再逐步尝试新的方法。稳定感可以成为探索的起点。",
        "finding_key": "foundation.balance",
    },
    {
        "key": "report.challenge",
        "title": "卡在哪",
        "content": "当前的难点不是缺少方向，而是如何在保留自主空间的同时控制尝试成本。",
        "finding_key": "finding.stability-autonomy",
    },
    {
        "key": "report.direction",
        "title": "往哪去",
        "content": "本周选择一个可逆的小实验：完成一次行业访谈，并记录事实、感受和下一步问题。",
        "finding_key": "finding.small-step",
    },
]

SKILL_EXAMPLE_CONTENT = {
    "report.narrative_plan": {
        "fragment": "report.identity",
        "case_key": "node-s5",
        "input": {"confirmed_findings": ["finding.stability-autonomy", "finding.small-step"]},
        "expected": {"supporting_findings": ["finding.stability-autonomy", "finding.small-step"]},
        "teaching": ["只引用已确认的 Finding", "清楚说明取舍与弱化内容"],
        "anti": ["在叙事候选中新增专业判断"],
    },
    "report.fragment_authoring": {
        "fragment": "report.direction",
        "case_key": "node-s5",
        "input": {"fragment_request": {"fragment_key": "report.direction"}},
        "expected": {"used_findings": ["finding.small-step"], "used_actions": ["行业访谈"]},
        "teaching": ["保留来源标识", "建议使用低成本、可复盘动作"],
        "anti": ["写作时引入未确认的结论"],
    },
    "report.final_validator": {
        "fragment": "report.direction",
        "case_key": "node-s6-blocked",
        "input": {"qa_input": {"required_sections": ["identity", "challenge", "direction"]}},
        "expected": {"issues": []},
        "teaching": ["问题必须定位到片段和证据", "无问题时返回空 issues"],
        "anti": ["把表达偏好误报为阻断问题"],
    },
}


def _now() -> datetime:
    return utc_now_naive()


def _require_local_database() -> None:
    database = make_url(settings.DATABASE_URL)
    if (
        settings.ENVIRONMENT.lower() not in {"dev", "development", "local"}
        or database.host != "postgres"
        or database.database != "innerpath"
    ):
        raise RuntimeError("Demo seeding is restricted to the local innerpath development database")


async def _required_staff(db, phone: str, role: str) -> User:
    user = await db.scalar(select(User).where(User.phone == phone))
    if user is None or user.role != role or not user.is_active:
        raise RuntimeError(f"Create an active {role} demo account for {phone} before seeding")
    return user


async def _demo_user(db, phone: str, name: str) -> User:
    user = await db.scalar(select(User).where(User.phone == phone))
    if user is not None:
        if user.name != name or user.role != "user":
            raise RuntimeError(f"Demo phone collision for {phone}; no account was changed")
        return user
    user = User(phone=phone, name=name, role="user", is_active=True)
    db.add(user)
    await db.flush()
    return user


def _profile(user: User, ordinal: int) -> dict:
    return {
        "name": user.name,
        "gender": "female" if ordinal % 2 else "male",
        "birth_year": 1991 + ordinal % 8,
        "birth_month": 2 + ordinal % 10,
        "birth_day": 8 + ordinal % 18,
        "birth_hour": 8 + ordinal % 8,
        "birth_minute": 20,
        "birth_place": "杭州",
        "calendar_type": "solar",
        "time_accuracy": "exact",
    }


def _request_context(scenario: dict) -> dict:
    return {
        "focus_topics": scenario.get("topics", ["career"]),
        "current_challenge": scenario["challenge"],
        "expected_outcomes": ["理解选择依据", "得到可执行的下一步"],
        "issue_duration": "最近一个季度",
        "impact_level": "有一定影响",
        "decision_status": "正在整理选项",
        "decision_description": scenario["challenge"],
        "decision_style": "先收集信息，再小步验证",
    }


def _service_request_data(user: User, scenario: dict, service_type: str) -> ServiceRequestCreate:
    data = {
        "service_type": service_type,
        "profile": _profile(user, int(scenario["phone"][-2:])),
        "profile_version": int(user.profile_version or 1),
        "context": _request_context(scenario),
        "selected_topics": scenario.get("topics", ["career"]),
        "additional_info": f"【演示】{scenario['challenge']}",
        "idempotency_key": f"innerpath-demo-v1:{scenario['key']}",
    }
    if service_type == "calendar":
        data["calendar_goal"] = scenario["challenge"]
        data["start_date"] = shanghai_today()
    if service_type == "report":
        # The consultant demo walks the retained standard workflow: findings,
        # evidence and node hand-off only exist there.
        data["workflow_key"] = DEFAULT_WORKFLOW_KEY
    return ServiceRequestCreate.model_validate(data)


async def _ensure_request(db, user: User, scenario: dict, service_type: str, consultant: User | None):
    key = f"innerpath-demo-v1:{scenario['key']}"
    request = await db.scalar(
        select(ServiceRequest).where(
            ServiceRequest.user_id == user.id,
            ServiceRequest.idempotency_key == key,
        )
    )
    created = request is None
    case = None
    if request is None:
        request, case = await create_user_service_request(
            db,
            user,
            _service_request_data(user, scenario, service_type),
        )
    elif service_type == "report":
        case = await db.scalar(
            select(ReportCase).where(ReportCase.service_request_id == request.id)
        )
        if case is None:
            raise RuntimeError(f"Demo report request {scenario['key']} has no ReportCase")

    if scenario.get("assigned") and consultant and not request.assigned_consultant_id and request.status == "submitted":
        request.assigned_consultant_id = consultant.id
        request.accepted_at = _now()
        request.status = "accepted"
        request.updated_by = consultant.id
    if service_type == "calendar" and scenario.get("status") == "needs_info" and created:
        request.status = "needs_info"
        request.needs_info_reason = "【演示】请补充希望开始执行计划的具体日期。"
        request.needs_info_at = _now()
    await db.commit()
    return request, case, created


async def _workflow_tasks(db, case: ReportCase) -> list[StepTask]:
    rows = await db.scalars(
        select(StepTask)
        .where(StepTask.workflow_instance_id == case.workflow_instance_id)
        .order_by(StepTask.sequence_no)
    )
    return list(rows.all())


async def _initialize_workflow_position(
    db,
    case: ReportCase,
    scenario: dict,
    consultant: User,
    *,
    created: bool,
) -> None:
    tasks = await _workflow_tasks(db, case)
    if not tasks:
        raise RuntimeError(f"ReportCase {case.id} has no step tasks")
    untouched = tasks[0].status == "READY" and all(
        task.status == "PENDING" for task in tasks[1:]
    )
    if not created and not untouched:
        return

    if scenario.get("assigned"):
        for task in tasks:
            if task.assignee_id is None:
                task.assignee_id = consultant.id

    target_step = int(scenario["target_step"])
    activate_current = scenario.get("activate_current", True)
    for task in tasks:
        if task.sequence_no < target_step:
            if task.status == "READY":
                await start_step(db, case.id, task.step_key)
            if task.status == "IN_REVIEW":
                await complete_step(
                    db,
                    case.id,
                    task.step_key,
                    result_json={
                        "demo_fixture": True,
                        "review_summary": f"演示数据已完成 {task.step_key} 节点的人工确认。",
                    },
                )
        elif task.sequence_no == target_step:
            if activate_current and task.status == "READY":
                await start_step(db, case.id, task.step_key)
            break


async def _active_evidence_key(db, case_id: int) -> str:
    evidence = await db.scalar(
        select(CaseEvidenceItem)
        .where(
            CaseEvidenceItem.report_case_id == case_id,
            CaseEvidenceItem.status == "ACTIVE",
            CaseEvidenceItem.evidence_key == "input.context.current_challenge",
        )
    )
    if evidence is None:
        raise RuntimeError(f"ReportCase {case_id} is missing application Evidence")
    return evidence.evidence_key


async def _ensure_findings(db, case: ReportCase, stage: int, tasks: list[StepTask], evidence_key: str, actor_id: int) -> list[str]:
    confirmed_keys = []
    for definition in FINDING_DEFINITIONS:
        if stage < definition["owner_step"] + 1:
            continue
        finding = await current_finding(db, case.id, definition["key"])
        if finding is None:
            owner = next(task for task in tasks if task.step_key == f"S{definition['owner_step']}")
            finding = await create_finding_revision(
                db,
                report_case_id=case.id,
                finding_key=definition["key"],
                claim=definition["claim"],
                semantic_role=definition["role"],
                confidence="MEDIUM",
                importance="HIGH",
                reportability="RECOMMENDED",
                status="CONFIRMED",
                evidence_refs=[evidence_key],
                owner_step_task_id=owner.id,
                created_by=actor_id,
            )
        if finding.status == "CONFIRMED":
            confirmed_keys.append(finding.finding_key)

    pending_by_stage = {
        2: ("finding.demo.psychology", "MOTIVATION_PATTERN", "用户更容易在边界清楚且保留自主空间的环境中投入。", 2),
        3: ("finding.demo.integration", "INTEGRATED_INSIGHT", "先验证一个具体假设，再决定是否改变更大的安排。", 3),
        4: ("finding.demo.action", "ACTION_STRATEGY", "先安排一项低成本访谈，并在一周后回顾新信息。", 4),
    }
    pending = pending_by_stage.get(stage)
    if pending:
        key, role, claim, owner_no = pending
        if await current_finding(db, case.id, key) is None:
            owner = next(task for task in tasks if task.step_key == f"S{owner_no}")
            await create_finding_revision(
                db,
                report_case_id=case.id,
                finding_key=key,
                claim=claim,
                semantic_role=role,
                confidence="MEDIUM",
                importance="MEDIUM",
                reportability="OPTIONAL",
                status="PROPOSED",
                evidence_refs=[evidence_key],
                owner_step_task_id=owner.id,
                created_by=actor_id,
            )
    return confirmed_keys


async def _ensure_analysis_fragment(db, case: ReportCase, tasks: list[StepTask], evidence_key: str, actor_id: int) -> None:
    existing = await db.scalar(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case.id,
            ContentFragmentRevision.fragment_key == "analysis.decision-pattern",
            ContentFragmentRevision.is_current.is_(True),
        )
    )
    if existing:
        return
    owner = next(task for task in tasks if task.step_key == "S4")
    await create_content_fragment_revision(
        db,
        report_case_id=case.id,
        fragment_key="analysis.decision-pattern",
        fragment_type="ANALYSIS",
        title="决策模式整理",
        content="将选择拆成信息收集、低成本验证和阶段复盘，减少一次决定承载的压力。",
        status="CONFIRMED",
        finding_refs=["finding.stability-autonomy", "finding.small-step"],
        evidence_refs=[evidence_key],
        owner_step_task_id=owner.id,
        created_by=actor_id,
    )


def _skill_output(skill_key: str) -> dict:
    if skill_key == "report.narrative_plan":
        return {
            "candidates": [
                {
                    "candidate_key": "steady-experiment",
                    "theme": "用小步验证，在稳定与探索间建立主动节奏",
                    "rationale": "先呈现稳定与自主的共同条件，再落到一项可逆实验。",
                    "supporting_findings": ["finding.stability-autonomy", "finding.small-step"],
                    "deemphasized_findings": [],
                    "priority_blocks": [{"title": "选择节奏", "finding_refs": ["finding.small-step"]}],
                    "narrative_arc": [{"stage": "recognize", "purpose": "呈现已确认的选择偏好"}],
                },
                {
                    "candidate_key": "conditions-first",
                    "theme": "先识别适合自己的条件，再安排尝试",
                    "rationale": "从工作环境的判断条件切入，再连接到行动步骤。",
                    "supporting_findings": ["finding.stability-autonomy"],
                    "deemphasized_findings": ["finding.small-step"],
                    "priority_blocks": [{"title": "工作条件", "finding_refs": ["finding.stability-autonomy"]}],
                    "narrative_arc": [{"stage": "recognize", "purpose": "梳理环境条件"}],
                },
            ]
        }
    if skill_key == "report.fragment_authoring":
        return {
            "status": "COMPLETED",
            "title": "先做一项小范围验证",
            "content": "本周可以完成一次从业者访谈，并记录新的事实、仍待确认的问题和下一步。",
            "used_findings": ["finding.small-step"],
            "used_analysis_fragments": ["analysis.decision-pattern"],
            "used_actions": ["完成一次从业者访谈"],
            "transition_hint": "从观察转向一个可复盘的实验。",
            "presentation_meta": {"tone": "克制具体", "demo_fixture": True},
        }
    if skill_key == "report.final_validator":
        return {"issues": []}
    return {
        "basic_info": {"name": "演示用户", "source": "申请快照"},
        "energy_profile": {"type": "稳步探索", "description": "先搭建结构，再扩大尝试。"},
        "career_guidance": {"suitable_paths": ["短周期项目", "结构化协作"], "summary": "先通过小样本任务检验方向。"},
        "relationship_pattern": {"summary": "提前说明需要的协作边界。"},
        "personal_growth": {"action_plan": [{"area": "方向验证", "action": "完成一次行业访谈", "timeline": "本周"}]},
        "summary": "使用小步验证连接稳定与探索。",
        "ai_generated_content": "【静态演示输出】所有判断与建议均需由咨询师审核。",
    }


async def _ensure_run(
    db,
    *,
    version: AISkillVersion,
    idempotency_key: str,
    output: dict,
    input_snapshot: dict,
    context_snapshot: dict,
    target_type: str = "DEBUG",
    target_key: str | None = None,
    run_type: str = "INITIAL",
    report_case: ReportCase | None = None,
    task: StepTask | None = None,
    error: str | None = None,
) -> SkillRun:
    run, created = await create_skill_run(
        db,
        skill_version_id=version.id,
        idempotency_key=idempotency_key,
        input_snapshot=input_snapshot,
        context_snapshot=context_snapshot,
        run_type=run_type,
        target_type=target_type,
        target_key=target_key,
        report_case_id=report_case.id if report_case else None,
        workflow_instance_id=report_case.workflow_instance_id if report_case else None,
        step_task_id=task.id if task else None,
    )
    if created or run.status in {"PENDING", "RUNNING"}:
        now = _now()
        run.status = "FAILED" if error else "COMPLETED"
        run.started_at = run.started_at or now
        run.completed_at = now
        run.output_parsed = output
        run.output_raw = json.dumps(output, ensure_ascii=False, indent=2)
        run.context_snapshot = context_snapshot
        run.model_trace = {
            "provider": "demo-fixture",
            "model": "deterministic-static-output",
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0,
            "finish_reason": "seeded_example",
        }
        run.error = error
    return run


async def _ensure_case_run(
    db,
    *,
    scenario: dict,
    case: ReportCase,
    task: StepTask,
    version: AISkillVersion,
    target_type: str,
    target_key: str,
    output: dict,
    context_snapshot: dict,
    run_type: str = "INITIAL",
) -> SkillRun:
    return await _ensure_run(
        db,
        version=version,
        idempotency_key=f"innerpath-demo-run:{scenario['key']}:{version.skill_key}:{target_key}",
        output=output,
        input_snapshot={
            "profile": {"name": scenario["name"]},
            "context": {"current_challenge": scenario["challenge"], "demo_fixture": True},
        },
        context_snapshot={"demo_fixture": True, **context_snapshot},
        target_type=target_type,
        target_key=target_key,
        run_type=run_type,
        report_case=case,
        task=task,
    )


async def _ensure_narrative_plan(db, scenario: dict, case: ReportCase, tasks: list[StepTask], findings: list[str], skill_versions: dict[str, AISkillVersion], actor_id: int, seed_runs: list[SkillRun]) -> NarrativePlan:
    current = await get_current_narrative_plan(db, case.id)
    if current:
        return current
    semantic_model = await load_case_semantic_model(db, case.id)
    source_snapshot = semantic_source_snapshot(semantic_model)
    candidate_output = _skill_output("report.narrative_plan")
    allowed = set(findings)
    for candidate in candidate_output["candidates"]:
        candidate["supporting_findings"] = [key for key in candidate["supporting_findings"] if key in allowed]
        candidate["deemphasized_findings"] = [key for key in candidate["deemphasized_findings"] if key in allowed]
        for block in candidate["priority_blocks"]:
            block["finding_refs"] = [key for key in block["finding_refs"] if key in allowed]
    candidate_task = next(task for task in tasks if task.step_key == "S5")
    run = await _ensure_case_run(
        db,
        scenario=scenario,
        case=case,
        task=candidate_task,
        version=skill_versions["report.narrative_plan"],
        target_type="NARRATIVE_CANDIDATES",
        target_key="narrative-plan",
        output=candidate_output,
        context_snapshot={"semantic_source_snapshot": source_snapshot},
    )
    seed_runs.append(run)
    first_candidate = candidate_output["candidates"][0]
    plan = await confirm_narrative_plan(
        db,
        report_case_id=case.id,
        skill_run_id=run.id,
        candidate_key=first_candidate["candidate_key"],
        overrides={},
        actor_id=actor_id,
    )
    return plan


async def _ensure_report_fragment(
    db,
    *,
    scenario: dict,
    case: ReportCase,
    tasks: list[StepTask],
    definition: dict,
    status: str,
    plan: NarrativePlan,
    finding_keys: list[str],
    evidence_key: str,
    skill_versions: dict[str, AISkillVersion],
    seed_runs: list[SkillRun],
    actor_id: int,
) -> ContentFragmentRevision:
    existing = await db.scalar(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case.id,
            ContentFragmentRevision.fragment_key == definition["key"],
            ContentFragmentRevision.is_current.is_(True),
        )
    )
    if existing:
        return existing
    step = next(task for task in tasks if task.step_key == "S5")
    used_findings = [definition["finding_key"]] if definition["finding_key"] in finding_keys else finding_keys[:1]
    output = _skill_output("report.fragment_authoring")
    output["used_findings"] = used_findings
    run = await _ensure_case_run(
        db,
        scenario=scenario,
        case=case,
        task=step,
        version=skill_versions["report.fragment_authoring"],
        target_type="REPORT_FRAGMENT",
        target_key=definition["key"],
        output=output,
        context_snapshot={"fragment_key": definition["key"], "narrative_plan_id": plan.id},
        run_type="INITIAL",
    )
    seed_runs.append(run)
    return await create_content_fragment_revision(
        db,
        report_case_id=case.id,
        fragment_key=definition["key"],
        fragment_type="REPORT",
        title=definition["title"],
        content=definition["content"],
        status=status,
        finding_refs=used_findings,
        evidence_refs=[evidence_key],
        owner_step_task_id=step.id,
        source_skill_run_id=run.id,
        source_narrative_plan_id=plan.id,
        created_by=actor_id,
    )


def _example_definition(
    skill_key: str,
    example_type: str,
    source_case_id: int,
    source_run_id: int,
    admin_id: int,
) -> SkillExample:
    content = SKILL_EXAMPLE_CONTENT[skill_key]
    is_candidate = example_type == "POSITIVE"
    suffix = "positive" if is_candidate else "contrast"
    return SkillExample(
        skill_key=skill_key,
        target_fragment_key=content["fragment"],
        example_key=f"demo-{skill_key.replace('.', '-')}-{suffix}",
        version_no=1,
        status="CANDIDATE" if is_candidate else "PUBLISHED",
        example_type=example_type,
        scenario_tags=["演示", skill_key.split(".")[-1], "脱敏"],
        applicability_json={"demo_fixture": True, "focus_topics": ["career", "growth"]},
        input_context=content["input"],
        expected_output=content["expected"],
        teaching_points=content["teaching"],
        anti_patterns=content["anti"],
        quality_score=0.92 if is_candidate else 0.88,
        source_case_id=source_case_id,
        source_skill_run_id=source_run_id,
        deidentified=True,
        created_by=admin_id,
        reviewed_by=None if is_candidate else admin_id,
        created_at=_now(),
        published_at=None if is_candidate else _now(),
    )


def _set_path(value, path: list, item) -> None:
    current = value
    for index, segment in enumerate(path[:-1]):
        next_container = [] if isinstance(path[index + 1], int) else {}
        if isinstance(segment, int):
            while len(current) <= segment:
                current.append(deepcopy(next_container))
            if not isinstance(current[segment], (dict, list)):
                current[segment] = deepcopy(next_container)
            current = current[segment]
        else:
            if not isinstance(current.get(segment), (dict, list)):
                current[segment] = deepcopy(next_container)
            current = current[segment]
    final = path[-1]
    if isinstance(final, int):
        while len(current) <= final:
            current.append({})
        current[final] = item
    else:
        current[final] = item


def _regression_output(expectation: dict) -> dict:
    output = {
        "demo_fixture": True,
        "status": "COMPLETED",
        "title": "静态回归示例",
        "content": "只使用输入中已确认的材料。",
        "used_findings": [],
    }
    for item in expectation.get("path_equals", []):
        _set_path(output, item["path"], item["value"])
    for item in expectation.get("minimum_array_length", []):
        path = item["path"]
        _set_path(output, path, [{} for _ in range(item["value"])])
    for field in expectation.get("required_fields", []):
        output.setdefault(field, [] if field == "used_findings" else "演示内容")
    if "allowed_finding_refs" in expectation:
        output["finding_refs"] = expectation["allowed_finding_refs"]
    return output


async def _ensure_evaluations(db, versions: list[AISkillVersion], example_refs: dict[str, list[dict]]) -> int:
    dataset_version = load_regression_dataset()["version"]
    created_or_found = 0
    for version in versions:
        cases = regression_cases(skill_key=version.skill_key)
        if not cases:
            continue
        digest = specification_digest(version.specification_json)
        batch_id = uuid5(
            NAMESPACE_URL,
            f"innerpath-demo-evaluation-v1:{version.id}:{digest}",
        ).hex
        for case in cases:
            expectation = case.get("expectation") or {}
            output = _regression_output(expectation)
            result = evaluate_regression_output(output, expectation)
            if not result["passed"]:
                raise RuntimeError(f"Static regression example did not satisfy {case['case_key']}")
            context = {
                "demo_fixture": True,
                "evaluation": {
                    "batch_id": batch_id,
                    "dataset_version": dataset_version,
                    "specification_sha256": digest,
                    "case_key": case["case_key"],
                    "title": case["title"],
                    "expectation": expectation,
                    "result": result,
                },
            }
            run, created = await create_skill_run(
                db,
                skill_version_id=version.id,
                idempotency_key=f"demo-evaluation:{batch_id}:{case['case_key']}",
                input_snapshot=case.get("input_data") or {},
                context_snapshot=context,
                run_type="EVALUATION",
                target_type="REGRESSION",
                target_key=case["case_key"],
                selected_examples=example_refs.get(version.skill_key, []),
            )
            if created or run.status in {"PENDING", "RUNNING"}:
                now = _now()
                run.status = "COMPLETED"
                run.started_at = run.started_at or now
                run.completed_at = now
                run.output_parsed = output
                run.output_raw = json.dumps(output, ensure_ascii=False, indent=2)
                run.model_trace = {
                    "provider": "demo-fixture",
                    "model": "deterministic-regression",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": 0,
                    "finish_reason": "offline_evaluation",
                }
                run.context_snapshot = context
                run.selected_examples = example_refs.get(version.skill_key, [])
            created_or_found += 1
    return created_or_found


async def seed() -> None:
    _require_local_database()
    async with AsyncSessionLocal() as db:
        admin = await _required_staff(db, ADMIN_PHONE, "admin")
        consultant = await _required_staff(db, CONSULTANT_PHONE, "consultant")
        await ensure_default_workflow_version(db)
        await ensure_default_narrative_skill_versions(db)
        await ensure_default_validator_skill_version(db)

        client_users = {}
        for index, scenario in enumerate(REPORT_SCENARIOS + CALENDAR_SCENARIOS, start=1):
            client_users[scenario["key"]] = await _demo_user(
                db, scenario["phone"], scenario["name"]
            )
        await db.commit()

        requests = {}
        cases = {}
        request_created = {}
        for scenario in REPORT_SCENARIOS:
            request, case, created = await _ensure_request(
                db, client_users[scenario["key"]], scenario, "report", consultant
            )
            await _initialize_workflow_position(
                db, case, scenario, consultant, created=created
            )
            await db.commit()
            requests[scenario["key"]] = request
            cases[scenario["key"]] = case
            request_created[scenario["key"]] = created

        for scenario in CALENDAR_SCENARIOS:
            request, _, _ = await _ensure_request(
                db, client_users[scenario["key"]], scenario, "calendar", consultant
            )
            if scenario.get("assigned") and request.assigned_consultant_id is None:
                request.assigned_consultant_id = consultant.id
                request.accepted_at = _now()
                request.updated_by = consultant.id
                await db.commit()
            requests[scenario["key"]] = request

        validator_draft = await db.scalar(
            select(AISkillVersion).where(
                AISkillVersion.skill_key == "report.final_validator",
                AISkillVersion.name == DEMO_DRAFT_NAME,
            )
        )
        if validator_draft is None:
            specification = default_validator_skill_specification()
            specification["identity"]["name"] = DEMO_DRAFT_NAME
            specification["identity"]["description"] = "可编辑的演示草稿，用于体验保存、离线评估与发布门禁。"
            specification["instructions"]["methodology"].append(
                "演示评估只验证结构和引用约束，不调用外部模型。"
            )
            validator_draft = await create_skill_draft(
                db,
                skill_key="report.final_validator",
                name=DEMO_DRAFT_NAME,
                category="VALIDATOR",
                specification=specification,
                created_by=admin.id,
            )
        await db.commit()

        versions = list(
            (
                await db.scalars(
                    select(AISkillVersion)
                    .where(AISkillVersion.status.in_({"PUBLISHED", "DRAFT"}),
                           AISkillVersion.skill_key.notin_(RETIRED_SKILL_KEYS))
                    .order_by(AISkillVersion.skill_key, AISkillVersion.version.desc())
                )
            ).all()
        )
        skill_versions = {}
        for version in versions:
            skill_versions.setdefault(version.skill_key, version)
        required_skills = {
            "report.narrative_plan",
            "report.fragment_authoring",
            "report.final_validator",
        }
        missing = required_skills - set(skill_versions)
        if missing:
            raise RuntimeError(f"Missing published Skill definitions: {sorted(missing)}")

        seed_runs: list[SkillRun] = []
        source_runs: dict[str, SkillRun] = {}
        for version in versions:
            run = await _ensure_run(
                db,
                version=version,
                idempotency_key=f"innerpath-demo-studio-run:{version.id}",
                output=_skill_output(version.skill_key),
                input_snapshot={
                    "profile": {"name": "演示用户"},
                    "context": {"focus_topics": ["career", "growth"], "demo_fixture": True},
                },
                context_snapshot={"demo_fixture": True, "run_label": "Skill Studio 静态试运行"},
                target_type="DEBUG",
                target_key=f"demo.{version.skill_key}",
            )
            seed_runs.append(run)
            source_runs.setdefault(version.skill_key, run)

        case_source_runs: dict[str, SkillRun] = {}
        for scenario in REPORT_SCENARIOS:
            key = scenario["key"]
            case = cases[key]
            tasks = await _workflow_tasks(db, case)
            stage = int(scenario["target_step"])
            evidence_key = await _active_evidence_key(db, case.id)
            finding_keys = await _ensure_findings(
                db, case, stage, tasks, evidence_key, consultant.id
            )
            if stage >= 5:
                await _ensure_analysis_fragment(db, case, tasks, evidence_key, consultant.id)

            if stage >= 5:
                plan = await _ensure_narrative_plan(
                    db,
                    scenario,
                    case,
                    tasks,
                    finding_keys,
                    skill_versions,
                    consultant.id,
                    seed_runs,
                )
                case_source_runs.setdefault("report.narrative_plan", seed_runs[-1])
                statuses = (
                    {"report.identity": "PROPOSED"}
                    if stage == 5
                    else {
                        "report.identity": "CONFIRMED",
                        "report.challenge": "CONFIRMED",
                        "report.direction": "PROPOSED"
                        if scenario.get("qa_mode") == "blocked"
                        else "CONFIRMED",
                    }
                )
                for definition in REQUIRED_REPORT_SECTIONS:
                    fragment_status = statuses.get(definition["key"])
                    if fragment_status is None:
                        continue
                    fragment = await _ensure_report_fragment(
                        db,
                        scenario=scenario,
                        case=case,
                        tasks=tasks,
                        definition=definition,
                        status=fragment_status,
                        plan=plan,
                        finding_keys=finding_keys,
                        evidence_key=evidence_key,
                        skill_versions=skill_versions,
                        seed_runs=seed_runs,
                        actor_id=consultant.id,
                    )
                    if fragment.source_skill_run_id:
                        run = await db.get(SkillRun, fragment.source_skill_run_id)
                        if run:
                            case_source_runs.setdefault("report.fragment_authoring", run)

            if scenario.get("qa_mode") == "blocked":
                existing_open_block = await db.scalar(
                    select(QAIssue.id).where(
                        QAIssue.report_case_id == case.id,
                        QAIssue.source_type == "PROGRAMMATIC",
                        QAIssue.status == "OPEN",
                        QAIssue.severity == "BLOCK",
                    )
                )
                if existing_open_block is None:
                    issues, _, _ = await run_programmatic_qa(
                        db, case, actor_id=admin.id
                    )
                    if not any(issue.severity == "BLOCK" for issue in issues):
                        raise RuntimeError("The blocked QA demo case did not produce a BLOCK issue")

            if scenario.get("qa_mode") in {"ready", "delivered"}:
                issues, fingerprint, _ = await collect_programmatic_issues(db, case)
                if any(issue["severity"] == "BLOCK" for issue in issues):
                    raise RuntimeError(
                        f"The ready QA demo case {key} has unexpected programmatic blocks: "
                        + ", ".join(issue["issue_type"] for issue in issues)
                    )
                validator_run = await db.scalar(
                    select(SkillRun).where(
                        SkillRun.idempotency_key == f"innerpath-demo-qa:{key}"
                    )
                )
                if validator_run is None:
                    final_task = next(task for task in tasks if task.step_key == "S6")
                    validator_run = await _ensure_case_run(
                        db,
                        scenario=scenario,
                        case=case,
                        task=final_task,
                        version=skill_versions["report.final_validator"],
                        target_type="REPORT_QA",
                        target_key="report.final",
                        output={"issues": []},
                        context_snapshot={"qa_fingerprint": fingerprint, "demo_fixture": True},
                        run_type="VALIDATE",
                    )
                    validator_run.idempotency_key = f"innerpath-demo-qa:{key}"
                seed_runs.append(validator_run)
                case_source_runs.setdefault("report.final_validator", validator_run)

            if scenario.get("qa_mode") == "delivered" and request_created[key]:
                state = await quality_state(db, case)
                if not state.can_approve:
                    raise RuntimeError("The delivered history demo is not quality-approved")
                await complete_step(
                    db,
                    case.id,
                    "S6",
                    result_json={"final_gate_approved": True, "demo_fixture": True},
                    final_gate_verified=True,
                )
                await db.flush()
                await deliver_report_case(db, report_case=case, actor=admin)

            await db.commit()

        example_case_keys = {
            "report.narrative_plan": "node-s5",
            "report.fragment_authoring": "node-s5",
            "report.final_validator": "node-s6-ready",
        }
        example_refs: dict[str, list[dict]] = {}
        example_source_runs = {**source_runs, **case_source_runs}
        for skill_key, content in SKILL_EXAMPLE_CONTENT.items():
            case = cases[content["case_key"]]
            source_run = example_source_runs.get(skill_key) or source_runs[skill_key]
            definitions = [
                ("POSITIVE", "CANDIDATE"),
                ("CONTRASTIVE", "PUBLISHED"),
            ]
            for example_type, status in definitions:
                suffix = "positive" if status == "CANDIDATE" else "contrast"
                example_key = f"demo-{skill_key.replace('.', '-')}-{suffix}"
                existing = await db.scalar(
                    select(SkillExample).where(
                        SkillExample.example_key == example_key,
                        SkillExample.version_no == 1,
                    )
                )
                if existing is None:
                    row = _example_definition(
                        skill_key, example_type, case.id, source_run.id, admin.id
                    )
                    if status == "PUBLISHED":
                        row.reviewed_by = admin.id
                    db.add(row)
                    await db.flush()
                    existing = row
                if existing.status == "PUBLISHED":
                    example_refs.setdefault(skill_key, []).append(
                        {
                            "example_id": existing.id,
                            "example_key": existing.example_key,
                            "version_no": existing.version_no,
                            "status": existing.status,
                        }
                    )

        for run in seed_runs:
            if not run.selected_examples:
                skill = await db.get(AISkillVersion, run.skill_version_id)
                if skill:
                    run.selected_examples = example_refs.get(skill.skill_key, [])

        evaluation_count = await _ensure_evaluations(db, versions, example_refs)
        await db.commit()

        request_counts = {
            "report_cases": len(cases),
            "report_requests": len(REPORT_SCENARIOS),
            "calendar_requests": len(CALENDAR_SCENARIOS),
            "skill_versions": len(versions),
            "examples": len(example_refs) * 2,
            "evaluation_runs": evaluation_count,
        }
        print(json.dumps(request_counts, ensure_ascii=False))


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(seed())
