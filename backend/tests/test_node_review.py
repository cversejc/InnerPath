import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, func

from tests.test_calendar_production_chain import chain_db
from app.models.user import User
from app.domains.content.models import CaseEvidenceItem, ContentFragmentRevision, FindingRevision, NarrativePlan
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.workflow.models import ReportCase, WorkflowVersion, WorkflowInstance, StepTask
from app.domains.review.models import NodeReviewCommand, NodeApproval, POLICY_VERSION
from app.domains.review.schemas import ReviewPatch, ReviewCommandInput, ReviewCheckpointInput, ReviewVersion, RevisionInput, IssueResolution, IssueResolutionGroup
from app.domains.review.contracts import fingerprint, normalize_ai_issues, approval_blockers, program_issues, group_review_issues
from app.domains.skills.analysis_sop import stage_contract
from app.domains.skills.runtime import ModelCompletion
from app.application.node_review_workspace import node_snapshot, save_metadata, review_context, review_workspace
from app.application.node_review_commands import patch_review, queue_review_command, execute_review_command, apply_revision, approve_checkpoint, approve_review, resolve_review_issue, resolve_review_issues, sign_node
from app.application.node_review_automation import prepare_node
from app.application import report_delivery


async def seed_node(db, active="S2"):
    now = datetime.utcnow()
    actor = User(phone="19900000001", name="审核测试管理员", role="admin")
    db.add(actor)
    version = WorkflowVersion(workflow_key="report.production", name="Review test", version=1, status="PUBLISHED", definition_json={"steps":[]}, created_at=now)
    db.add(version)
    await db.flush()
    case = ReportCase(user_id=actor.id, status="ACTIVE", review_policy_version=POLICY_VERSION,
        application_snapshot={"profile":{"birth_year":2000,"birth_month":1,"birth_day":1,"birth_hour":12,"birth_place":"山东济南"}}, application_submitted_at=now, created_at=now, updated_at=now)
    db.add(case)
    await db.flush()
    instance = WorkflowInstance(report_case_id=case.id, workflow_version_id=version.id, status="RUNNING", created_at=now, updated_at=now)
    db.add(instance)
    await db.flush()
    case.workflow_instance_id = instance.id
    number = int(active[1:])
    steps = []
    for n in range(1,7):
        s = StepTask(workflow_instance_id=instance.id, step_key=f"S{n}", sequence_no=n, executor="HYBRID", status="COMPLETED" if n<number else "IN_REVIEW" if n==number else "PENDING", activation_no=1, config_snapshot={}, created_at=now, updated_at=now)
        db.add(s)
        steps.append(s)
    await db.flush()
    step = steps[number-1]
    for topic in (stage_contract(active) or {}).get("topics", []):
        db.add(ContentFragmentRevision(report_case_id=case.id, owner_step_task_id=step.id, fragment_key=topic["fragment_key"], title=topic["title"], content="真实用户提供的测试资料。这里保留待验证的解释与限制。", fragment_type="ANALYSIS", revision_no=1, semantic_revision=1, content_revision=1, source_snapshot={}, edit_kind="SEMANTIC", status="PROPOSED", is_current=True, created_at=now))
    await db.commit()
    async def refresh(value, **kwargs):
        db.session.refresh(value)
    db.refresh = refresh
    return case, step, actor, steps


class Gateway:
    def __init__(self, output, on_call=None):
        self.output, self.on_call, self.calls = output, on_call, 0

    async def complete(self, **kwargs):
        self.calls += 1
        if self.on_call:
            await self.on_call()
        return ModelCompletion(json.dumps(self.output, ensure_ascii=False), {"provider":"TEST_DOUBLE", "latency_ms":1})


@pytest.mark.parametrize("step_key", ["S1", "S2", "S3", "S4", "S5", "S6"])
def test_empty_node_reports_only_the_actionable_missing_output(step_key):
    issues = program_issues({"step_key": step_key, "fragments": []})

    assert [(issue["type"], issue["severity"]) for issue in issues] == [("node_output_required", "BLOCK")]


async def version(db, case, step):
    _, _, state = await review_context(db, case.id, step.step_key)
    return fingerprint(await node_snapshot(db, case, step, state))


async def approve_checkpoint_for_test(db, case, step, actor, checkpoint_key):
    return await approve_checkpoint(
        db,
        case.id,
        step.step_key,
        actor,
        ReviewCheckpointInput(
            fingerprint=await version(db, case, step),
            idempotency_key=f"checkpoint:{case.id}:{step.step_key}:{checkpoint_key}",
            checkpoint_key=checkpoint_key,
        ),
    )


async def add_test_finding(db, case, step, actor):
    finding = FindingRevision(
        report_case_id=case.id,
        finding_key=f"{step.step_key.lower()}.review.example",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        semantic_role="PATTERN",
        claim="用户在压力情境中倾向于延迟表达需要。",
        confidence="MEDIUM",
        importance="HIGH",
        reportability="RECOMMENDED",
        status="PROPOSED",
        evidence_refs=[],
        relation_refs=[],
        structured_data_json={},
        edit_kind="SEMANTIC",
        is_current=True,
        owner_step_task_id=step.id,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    )
    db.add(finding)
    await db.commit()
    return finding


@pytest.mark.asyncio
async def test_one_whole_node_signature_publishes_all_pending_content(chain_db):
    db = chain_db
    case, step, actor, steps = await seed_node(db)
    await add_test_finding(db, case, step, actor)
    command = await queue_review_command(db, case.id, "S2", actor, ReviewCommandInput(fingerprint=await version(db,case,step), idempotency_key="check-v1"), "CHECK")
    await execute_review_command(db, command.id, gateway=Gateway({"issues":[]}))
    assert command.status == "COMPLETED"
    assert command.output_json["issues"] == []
    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    await approve_review(db, case.id, "S2", actor, command.fingerprint)
    rows = list(await db.scalars(select(ContentFragmentRevision).where(ContentFragmentRevision.owner_step_task_id == step.id, ContentFragmentRevision.is_current.is_(True))))
    assert len(rows) == len(stage_contract("S2")["topics"])
    assert all(r.status == "CONFIRMED" for r in rows)
    assert await db.scalar(select(func.count(NodeApproval.id))) == 1
    assert step.status == "COMPLETED" and steps[2].status == "READY"
    replay = await approve_review(db, case.id, "S2", actor, command.fingerprint)
    assert replay.id == 1
    assert await db.scalar(select(func.count(NodeApproval.id))) == 1


@pytest.mark.asyncio
async def test_semantic_fragment_edit_rebinds_coverage_and_updates_title(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    fragment = await db.scalar(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == case.id,
        ContentFragmentRevision.owner_step_task_id == step.id,
        ContentFragmentRevision.is_current.is_(True),
    ).order_by(ContentFragmentRevision.fragment_key))
    fragment.content = "重点围绕用户的具体经历，确认当前现实处境。"
    fragment.source_snapshot = {
        "framework_coverage": {"status": "COVERED", "reason": "包含现实情境", "quote": "用户的具体经历"},
        "structured_analysis": {"status": "COVERED", "reason": "保留现实核对", "quote": "用户的具体经历", "follow_up_questions": [], "details": {}},
        "requirement_coverage": [{"requirement_id": "reality", "status": "COVERED", "quote": "当前现实处境"}],
    }
    await db.commit()
    before = await version(db, case, step)

    await patch_review(db, case.id, step.step_key, actor, ReviewPatch(
        fingerprint=before,
        changes=[{
            "kind": "fragment",
            "key": fragment.fragment_key,
            "title": "修订后的内容标题",
            "content": "重点聚焦当事人的现实经验，并核对当下的生活处境。",
        }],
    ))

    current = await db.scalar(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == case.id,
        ContentFragmentRevision.fragment_key == fragment.fragment_key,
        ContentFragmentRevision.is_current.is_(True),
    ))
    assert current.title == "修订后的内容标题"
    assert current.status == "PROPOSED"
    assert current.edit_kind == "SEMANTIC"
    assert current.source_snapshot["framework_coverage"]["quote"] in current.content
    assert current.source_snapshot["structured_analysis"]["quote"] in current.content
    assert current.source_snapshot["requirement_coverage"][0]["quote"] in current.content


@pytest.mark.asyncio
async def test_semantic_review_repairs_coverage_quote_from_earlier_revision(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    original = await db.scalar(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == case.id,
        ContentFragmentRevision.owner_step_task_id == step.id,
        ContentFragmentRevision.is_current.is_(True),
    ).order_by(ContentFragmentRevision.fragment_key))
    original.content = "重点依据用户的真实经历，相关假设需要确认。"
    original.source_snapshot = {
        "framework_coverage": {"status": "COVERED", "reason": "包含真实情境", "quote": "用户的真实经历"},
        "structured_analysis": {"status": "COVERED", "reason": "保留现实核对", "quote": "用户的真实经历", "follow_up_questions": [], "details": {}},
    }
    await db.flush()
    original.is_current = False
    current = ContentFragmentRevision(
        report_case_id=case.id,
        owner_step_task_id=step.id,
        fragment_key=original.fragment_key,
        title=original.title,
        content="重点依据当事人的现实经验，相关假设需要确认。",
        fragment_type=original.fragment_type,
        revision_no=2,
        semantic_revision=1,
        content_revision=2,
        source_snapshot=original.source_snapshot,
        edit_kind="STYLE",
        status="PROPOSED",
        is_current=True,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    )
    db.add(current)
    await db.commit()
    before = await version(db, case, step)

    await patch_review(db, case.id, step.step_key, actor, ReviewPatch(
        fingerprint=before,
        changes=[{
            "kind": "fragment",
            "key": current.fragment_key,
            "title": current.title,
            "content": current.content,
        }],
    ))

    repaired = await db.scalar(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == case.id,
        ContentFragmentRevision.fragment_key == current.fragment_key,
        ContentFragmentRevision.is_current.is_(True),
    ))
    assert repaired.revision_no == 3
    assert repaired.semantic_revision == 2
    assert repaired.source_snapshot["framework_coverage"]["quote"] in repaired.content
    assert repaired.source_snapshot["structured_analysis"]["quote"] in repaired.content


async def dummy_run(db, case, step, actor, target="NARRATIVE_CANDIDATES", status="COMPLETED"):
    skill=AISkillVersion(skill_key="review.fixture",name="fixture",category="AUTHORING",version=1,status="DRAFT",specification_json={},created_at=datetime.utcnow())
    db.add(skill)
    await db.flush()
    run=SkillRun(skill_version_id=skill.id,report_case_id=case.id,step_task_id=step.id,target_type=target,run_type="INITIAL",status=status,idempotency_key="fixture-run",input_snapshot={},context_snapshot={},created_at=datetime.utcnow())
    db.add(run)
    await db.flush()
    return run


async def seed_s5_report_readiness(db, case, step, actor, *, current_coherence):
    run = await dummy_run(db, case, step, actor)
    plan = NarrativePlan(
        report_case_id=case.id,
        version_no=1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=run.id,
        selected_candidate_key="mainline",
        source_snapshot={},
        plan_json={
            "core_theme": "围绕用户现实问题组织报告",
            "narrative_arc": ["现状", "调整方向"],
            "content_plan": {"fragments": [{"fragment_key": "report.body", "sequence_no": 1, "chapter": "overview", "required": True}]},
        },
        confirmed_by=actor.id,
        confirmed_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(plan)
    await db.flush()
    fragment = ContentFragmentRevision(
        report_case_id=case.id,
        owner_step_task_id=step.id,
        fragment_key="report.body",
        title="报告正文",
        content="这是一段完整、可追溯并保留适用边界的报告内容。",
        fragment_type="REPORT",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        source_narrative_plan_id=plan.id,
        source_snapshot={},
        edit_kind="SEMANTIC",
        status="PROPOSED",
        is_current=True,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    )
    db.add(fragment)
    await db.flush()

    from app.application.report_generation import _coherence_fingerprint, _fragment_snapshot

    coherence_fingerprint = _coherence_fingerprint(plan, _fragment_snapshot(plan, [fragment]))
    plan.plan_json = {
        **plan.plan_json,
        "generation": {
            "status": "READY_FOR_REVIEW",
            "coherence": {
                "status": "PASSED",
                "skill_run_id": 99,
                "fingerprint": coherence_fingerprint if current_coherence else "0" * 64,
            },
        },
    }
    await db.commit()
    return fragment


@pytest.mark.asyncio
async def test_s5_report_confirmation_requires_current_full_coherence(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db, "S5")
    await seed_s5_report_readiness(db, case, step, actor, current_coherence=False)
    await approve_checkpoint_for_test(db, case, step, actor, "narrative")

    with pytest.raises(ValueError, match="node_report_coherence_required"):
        await approve_checkpoint_for_test(db, case, step, actor, "report")


@pytest.mark.asyncio
async def test_s5_mainline_confirmation_records_its_checkpoint_once(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db, "S5")
    await seed_s5_report_readiness(db, case, step, actor, current_coherence=True)
    from app.application.node_review_commands import record_automatic_checkpoint

    first = await record_automatic_checkpoint(db, case, step, actor, "narrative", "narrative_plan_confirmation")
    replay = await record_automatic_checkpoint(db, case, step, actor, "narrative", "narrative_plan_confirmation")
    workspace = await review_workspace(db, case.id, "S5", actor)

    assert replay.id == first.id
    assert workspace["checkpoints"]["narrative"]["current"] is True
    assert workspace["checkpoints"]["narrative"]["approved_by"] == actor.id
    assert workspace["checkpoints"]["narrative"]["approved_at"]


@pytest.mark.asyncio
async def test_s5_report_edit_invalidates_its_coherence_bound_checkpoint(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db, "S5")
    fragment = await seed_s5_report_readiness(db, case, step, actor, current_coherence=True)
    await approve_checkpoint_for_test(db, case, step, actor, "narrative")
    await approve_checkpoint_for_test(db, case, step, actor, "report")
    before = await review_workspace(db, case.id, "S5", actor)
    assert before["checkpoints"]["report"]["current"] is True

    fragment.content = "正文修订后，原有全文连贯性检查不再适用于当前版本。"
    fragment.content_revision += 1
    await db.commit()
    after = await review_workspace(db, case.id, "S5", actor)

    assert after["snapshot"]["report_generation"]["coherence"]["status"] == "STALE"
    assert after["checkpoints"]["report"]["current"] is False
    assert after["checkpoints"]["report"]["stale"] is True
    assert any(issue["type"] == "report_coherence_required" for issue in after["issues"])
    with pytest.raises(ValueError, match="node_report_coherence_required"):
        await approve_checkpoint(
            db,
            case.id,
            "S5",
            actor,
            ReviewCheckpointInput(
                fingerprint=await version(db, case, step),
                idempotency_key=f"checkpoint:{case.id}:S5:report-after-edit",
                checkpoint_key="report",
            ),
        )


@pytest.mark.asyncio
async def test_mainline_edit_preserves_manual_body_and_invalidates_check(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db,"S5")
    run=await dummy_run(db,case,step,actor)
    plan=NarrativePlan(report_case_id=case.id,version_no=1,is_current=True,status="PROPOSED",selected_skill_run_id=run.id,selected_candidate_key="a",source_snapshot={},plan_json={"core_theme":"旧主线","narrative_arc":["旧安排"],"content_plan":{"fragments":[{"fragment_key":"body","sequence_no":1,"required":True}]}},created_at=datetime.utcnow())
    db.add(plan)
    await db.flush()
    db.add(ContentFragmentRevision(report_case_id=case.id,owner_step_task_id=step.id,fragment_key="body",title="人工正文",content="人工已经修改的正文，待与主线一起重检。",fragment_type="REPORT",revision_no=1,semantic_revision=1,content_revision=1,source_narrative_plan_id=plan.id,source_snapshot={},edit_kind="SEMANTIC",status="PROPOSED",is_current=True,created_by=actor.id,created_at=datetime.utcnow()))
    await db.commit()
    before=await version(db,case,step)
    await patch_review(db,case.id,"S5",actor,ReviewPatch(fingerprint=before,narrative={"core_theme":"新的完整主线","narrative_arc":["说明现状","提出实验"],"fragment_order":["body"]}))
    current=await db.scalar(select(NarrativePlan).where(NarrativePlan.is_current.is_(True)))
    body=await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.is_current.is_(True)))
    assert current.version_no==2 and current.confirmed_by is None
    assert body.content=="人工已经修改的正文，待与主线一起重检。"
    assert body.source_narrative_plan_id==current.id and body.created_by==actor.id
    assert await version(db,case,step)!=before


@pytest.mark.asyncio
async def test_migration_waits_for_running_jobs_then_archives_pending_and_preserves_waiting(chain_db):
    from copy import deepcopy
    from app.application.node_review_migration import migrate_reviews
    db=chain_db
    case,step,actor,steps=await seed_node(db)
    case.review_policy_version=None
    case.status="BLOCKED"
    case.application_snapshot={**case.application_snapshot,"skill_bindings":{"retained":"frozen"}}
    snapshot=deepcopy(case.application_snapshot)
    steps[0].result_json={"legacy":"signed"}
    run=await dummy_run(db,case,step,actor,target="REPORT_ANALYSIS_DRAFT",status="RUNNING")
    await db.commit()
    inventory=await migrate_reviews(db,apply=True)
    assert inventory[0]["migration_status"]=="WAITING_FOR_RUNNING_TASKS"
    assert case.review_policy_version is None and run.status=="RUNNING"
    run.status="PENDING"
    await db.commit()
    inventory=await migrate_reviews(db,apply=True)
    assert inventory[0]["migration_status"]=="MIGRATED"
    assert case.application_snapshot==snapshot and case.status=="BLOCKED"
    assert run.status=="FAILED" and run.context_snapshot["node_archived"]=="legacy_policy"
    assert steps[0].status=="IN_REVIEW" and steps[1].status=="PENDING"
    assert steps[0].result_json=={"legacy":"signed"}
    assert await migrate_reviews(db,apply=True)==[]


@pytest.mark.asyncio
async def test_failed_final_validator_releases_review_command_for_retry(chain_db):
    from app.application.node_review_automation import continue_node_run
    db=chain_db
    case,step,actor,_=await seed_node(db,"S6")
    run=await dummy_run(db,case,step,actor,target="REPORT_QA",status="FAILED")
    run.error="provider_unavailable"
    command=NodeReviewCommand(report_case_id=case.id,step_task_id=step.id,kind="CHECK",idempotency_key="failed-final",activation_no=1,fingerprint=await version(db,case,step),policy_version=POLICY_VERSION,status="RUNNING",input_json={},output_json={"validator_run_id":run.id},requested_by=actor.id,created_at=datetime.utcnow())
    db.add(command)
    await db.commit()
    await continue_node_run(db,run)
    assert command.status=="FAILED" and command.completed_at is not None
    assert command.error=="provider_unavailable"


@pytest.mark.asyncio
async def test_edit_invalidates_old_check_and_ai_revision_cannot_overwrite_human_edit(chain_db):
    db=chain_db
    case, step, actor, _ = await seed_node(db)
    old = await version(db,case,step)
    check = await queue_review_command(db,case.id,"S2",actor,ReviewCommandInput(fingerprint=old,idempotency_key="check"),"CHECK")
    await execute_review_command(db,check.id,gateway=Gateway({"issues":[]}))
    key=stage_contract("S2")["topics"][0]["fragment_key"]
    checked_version=await version(db,case,step)
    revision=await queue_review_command(db,case.id,"S2",actor,RevisionInput(fingerprint=checked_version,idempotency_key="revision",targets=[key],instruction="局部调整措辞"),"REVISION")
    await execute_review_command(db,revision.id,gateway=Gateway({"changes":[{"key":key,"content":"AI建议文本。","reason":"表达调整"}]}))
    original=await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.fragment_key==key,ContentFragmentRevision.is_current.is_(True)))
    assert original.content != "AI建议文本。"
    await patch_review(db,case.id,"S2",actor,ReviewPatch(fingerprint=checked_version,changes=[{"key":key,"content":"保留人工修改。"}]))
    with pytest.raises(ValueError,match="version_conflict"):
        await approve_review(db,case.id,"S2",actor,old)
    await db.rollback()
    with pytest.raises(ValueError,match="revision_stale"):
        await apply_revision(db,case.id,"S2",revision.id,actor,await version(db,case,step))
    await db.rollback()
    current=await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.fragment_key==key,ContentFragmentRevision.is_current.is_(True)))
    assert current.content=="保留人工修改。"


@pytest.mark.asyncio
async def test_command_retry_and_in_flight_stale_write_are_guarded(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    value=await version(db,case,step)
    payload=ReviewCommandInput(fingerprint=value,idempotency_key="same-command")
    command=await queue_review_command(db,case.id,"S2",actor,payload,"CHECK")
    replay=await queue_review_command(db,case.id,"S2",actor,payload,"CHECK")
    assert replay.id==command.id
    async def edit_during_model():
        await patch_review(db,case.id,"S2",actor,ReviewPatch(fingerprint=command.fingerprint,changes=[{"key":stage_contract("S2")["topics"][0]["fragment_key"],"content":"模型运行期间的人工新稿。"}]))
    gateway=Gateway({"issues":[]},edit_during_model)
    await execute_review_command(db,command.id,gateway=gateway)
    assert command.status=="STALE" and "archived_output" in command.output_json
    await execute_review_command(db,command.id,gateway=gateway)
    assert gateway.calls==1


@pytest.mark.asyncio
async def test_major_reason_can_be_retained_but_minor_needs_no_processing(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    await add_test_finding(db, case, step, actor)
    key=stage_contract("S2")["topics"][0]["fragment_key"]
    output={"issues":[{"severity":s,"type":s,"target_key":key,"quote":"测试资料","message":"请核对表达依据"} for s in ("MAJOR","MINOR")]}
    command=await queue_review_command(db,case.id,"S2",actor,ReviewCommandInput(fingerprint=await version(db,case,step),idempotency_key="major"),"CHECK")
    await execute_review_command(db,command.id,gateway=Gateway(output))
    assert len(approval_blockers(command.output_json["issues"]))==1
    issue=next(i for i in command.output_json["issues"] if i["severity"]=="MAJOR")
    await resolve_review_issue(db,case.id,"S2",actor,IssueResolution(fingerprint=command.fingerprint,check_id=command.id,issue_id=issue["id"],resolution="RETAINED",reason="原始自述与正文吻合，保留并说明条件"))
    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    await approve_review(db,case.id,"S2",actor,command.fingerprint)
    assert step.status=="COMPLETED"


@pytest.mark.asyncio
async def test_content_edit_invalidates_only_its_review_checkpoint(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    await add_test_finding(db, case, step, actor)

    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    before=await review_workspace(db, case.id, "S2", actor)
    assert before["checkpoints"]["findings"]["current"] is True
    assert before["checkpoints"]["findings"]["approved_by"] == actor.id
    assert before["checkpoints"]["findings"]["approved_at"]
    assert before["checkpoints"]["analysis"]["current"] is True

    fragment_key=stage_contract("S2")["topics"][0]["fragment_key"]
    await patch_review(db,case.id,"S2",actor,ReviewPatch(
        fingerprint=await version(db,case,step),
        changes=[{"key":fragment_key,"content":"修订后的分析内容，来源仍可追溯。"}],
    ))
    after=await review_workspace(db, case.id, "S2", actor)
    assert after["checkpoints"]["findings"]["current"] is True
    assert after["checkpoints"]["analysis"]["current"] is False
    assert after["checkpoints"]["analysis"]["stale"] is True


def test_hallucinated_quotes_are_rejected_and_same_root_merged():
    snapshot={"fragments":[{"fragment_key":"a","content":"真实原文和另外一句"}],"findings":[],"evidence":[]}
    output={"issues":[{"target_key":"a","quote":q,"severity":"MAJOR","root_key":"same","message":"依据"} for q in ("真实原文","另外一句","编造摘录")]}
    accepted,rejected=normalize_ai_issues(output,snapshot)
    assert len(accepted)==1 and len(accepted[0]["related_quotes"])==2 and len(rejected)==1

def test_structured_analysis_fields_are_quotable_by_the_checker():
    snapshot={"fragments":[{"fragment_key":"a","content":"正文一句。","source_snapshot":{"structured_analysis":{"summary":"结构化摘要内容"}}}],"findings":[],"evidence":[]}
    output={"issues":[{"target_key":"a","quote":"结构化摘要内容","severity":"MAJOR","message":"依据该结构化字段"}]}
    accepted,rejected=normalize_ai_issues(output,snapshot)
    assert len(accepted)==1 and accepted[0]["severity"]=="MAJOR" and not rejected


@pytest.mark.asyncio
async def test_partially_unlocatable_check_quotes_keep_the_run_with_a_minor_note(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    fragment_key=stage_contract("S2")["topics"][0]["fragment_key"]
    output={"issues":[
        {"target_key":fragment_key,"quote":"真实用户提供的测试资料","severity":"MAJOR","message":"需要核对来源"},
        {"target_key":fragment_key,"quote":"并不存在于成果中的摘录","severity":"MAJOR","message":"无法定位"},
    ]}
    command=await queue_review_command(db,case.id,"S2",actor,ReviewCommandInput(fingerprint=await version(db,case,step),idempotency_key="partial-quotes"),"CHECK")

    await execute_review_command(db,command.id,gateway=Gateway(output))

    assert command.status=="COMPLETED"
    assert [issue["quote"] for issue in command.output_json["issues"] if issue.get("quote")]==["真实用户提供的测试资料"]
    assert len(command.output_json["rejected_issues"])==1
    note=[issue for issue in command.output_json["issues"] if issue["type"]=="node_check_quote_rejected"]
    assert len(note)==1 and note[0]["severity"]=="MINOR" and "1 条" in note[0]["message"]


@pytest.mark.asyncio
async def test_wholly_unlocatable_check_output_fails_and_keeps_rejected_issues(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    output={"issues":[{"target_key":"missing.key","quote":"编造摘录","severity":"MAJOR","message":"无法定位"}]}
    command=await queue_review_command(db,case.id,"S2",actor,ReviewCommandInput(fingerprint=await version(db,case,step),idempotency_key="all-quotes-rejected"),"CHECK")

    await execute_review_command(db,command.id,gateway=Gateway(output))

    assert command.status=="FAILED" and command.error=="node_check_source_invalid"
    assert command.output_json=={"rejected_issues":output["issues"]}


@pytest.mark.asyncio
async def test_unassigned_node_waits_and_wrong_specialty_cannot_edit(chain_db):
    db=chain_db
    case,step,actor,_=await seed_node(db)
    step.status="READY"
    await db.commit()
    assert await prepare_node(db,case.id,step.id,step.activation_no)=="waiting_for_assignment"
    step.status="IN_REVIEW"
    step.required_capability="mingli"
    step.assignee_id=actor.id
    wrong=SimpleNamespace(id=actor.id,role="consultant",is_active=True,consultant_type="psychology")
    # Case access is independently authorized; the domain specialty rule still rejects.
    from app.domains.workflow.authorization import validate_step_actor
    with pytest.raises(ValueError,match="specialty_required"):
        validate_step_actor(step,wrong)


@pytest.mark.asyncio
async def test_final_signoff_binds_the_latest_quality_run_without_a_second_check(chain_db, monkeypatch):
    db = chain_db
    case, step, actor, steps = await seed_node(db, "S6")
    now = datetime.utcnow()
    db.add(ContentFragmentRevision(
        report_case_id=case.id,
        owner_step_task_id=step.id,
        fragment_key="report.final",
        title="最终报告正文",
        content="这是一份用于验证最终签核绑定的完整报告正文。",
        fragment_type="REPORT",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        source_snapshot={},
        edit_kind="SEMANTIC",
        status="PROPOSED",
        is_current=True,
        created_by=actor.id,
        created_at=now,
    ))
    await db.commit()
    value = await version(db, case, step)
    prior_check = NodeReviewCommand(
        report_case_id=case.id,
        step_task_id=step.id,
        kind="CHECK",
        idempotency_key="final-quality-run-before-signoff",
        activation_no=step.activation_no,
        fingerprint=value,
        policy_version=POLICY_VERSION,
        status="COMPLETED",
        input_json={},
        output_json={"validator_run_id": 41, "qa_fingerprint": "older-qa", "issues": []},
        requested_by=actor.id,
        created_at=now,
        completed_at=now,
    )
    db.add(prior_check)
    await db.commit()
    from app.application import report_quality

    final_quality_snapshot = {"quality_status": "COMPLETED", "qa_fingerprint_current": "current-qa"}
    final_quality = SimpleNamespace(
        can_approve=True,
        latest_validator_run={"id": 42, "status": "COMPLETED", "current": True},
        qa_fingerprint_current="current-qa",
        model_dump=lambda mode="python": final_quality_snapshot,
    )
    monkeypatch.setattr(report_quality, "quality_state", AsyncMock(return_value=final_quality))
    await approve_checkpoint_for_test(db, case, step, actor, "report")
    _, _, state = await review_context(db, case.id, "S6", actor)

    approval = await sign_node(db, case, step, state, actor, value)
    bound_check = await db.get(NodeReviewCommand, approval.check_command_id)

    assert bound_check.id != prior_check.id
    assert bound_check.status == "COMPLETED"
    assert bound_check.output_json["validator_run_id"] == 42
    assert bound_check.output_json["qa_fingerprint"] == "current-qa"
    assert approval.manifest_json["final_quality"] == final_quality_snapshot


@pytest.mark.asyncio
async def test_s6_quality_issue_resolution_invalidates_final_report_checkpoint(chain_db, monkeypatch):
    db = chain_db
    case, step, actor, _ = await seed_node(db, "S6")
    db.add(ContentFragmentRevision(
        report_case_id=case.id,
        owner_step_task_id=step.id,
        fragment_key="report.final",
        title="最终报告正文",
        content="用于验证最终稿确认会绑定质量问题处理状态。",
        fragment_type="REPORT",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        source_snapshot={},
        edit_kind="SEMANTIC",
        status="PROPOSED",
        is_current=True,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    ))
    await db.commit()
    from app.application import report_quality

    open_issue_snapshot = {
        "quality_status": "COMPLETED",
        "qa_fingerprint_current": "same-report-version",
        "can_approve": True,
        "blocking_count": 0,
        "open_count": 0,
        "latest_validator_run": {"id": 52, "status": "COMPLETED", "current": True},
        "issues": [{"id": 9, "status": "OPEN", "resolution": None}],
    }

    def quality_result(snapshot):
        return SimpleNamespace(
            can_approve=True,
            quality_status=snapshot["quality_status"],
            latest_validator_run=snapshot["latest_validator_run"],
            qa_fingerprint_current=snapshot["qa_fingerprint_current"],
            blocking_count=snapshot["blocking_count"],
            open_count=snapshot["open_count"],
            issues=[],
            model_dump=lambda mode="python": snapshot,
        )

    current = quality_result(open_issue_snapshot)
    quality_state_mock = AsyncMock(return_value=current)
    monkeypatch.setattr(report_quality, "quality_state", quality_state_mock)
    await approve_checkpoint_for_test(db, case, step, actor, "report")
    before = await review_workspace(db, case.id, "S6", actor)
    assert before["checkpoints"]["report"]["current"] is True

    resolved_issue_snapshot = {
        **open_issue_snapshot,
        "issues": [{"id": 9, "status": "ACCEPTED", "resolution": "已核实并记录处理理由"}],
    }
    quality_state_mock.return_value = quality_result(resolved_issue_snapshot)
    after = await review_workspace(db, case.id, "S6", actor)

    assert after["fingerprint"] == before["fingerprint"]
    assert after["checkpoints"]["report"]["current"] is False
    assert after["checkpoints"]["report"]["stale"] is True


@pytest.mark.asyncio
async def test_final_delivery_failure_rolls_back_signature_and_workflow(chain_db,monkeypatch):
    db=chain_db
    case,step,actor,steps=await seed_node(db,"S6")
    db.add(ContentFragmentRevision(
        report_case_id=case.id,
        owner_step_task_id=step.id,
        fragment_key="report.final",
        title="最终报告正文",
        content="这是一份用于验证交付回滚的完整报告正文。",
        fragment_type="REPORT",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        source_snapshot={},
        edit_kind="SEMANTIC",
        status="PROPOSED",
        is_current=True,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    ))
    await db.commit()
    value=await version(db,case,step)
    command=NodeReviewCommand(report_case_id=case.id,step_task_id=step.id,kind="CHECK",idempotency_key="final",activation_no=step.activation_no,fingerprint=value,policy_version=POLICY_VERSION,status="COMPLETED",input_json={},output_json={"issues":[]},requested_by=actor.id,created_at=datetime.utcnow())
    db.add(command)
    await db.commit()
    from app.application import report_quality
    monkeypatch.setattr(report_quality,"case_can_be_delivered",AsyncMock(return_value=True))
    final_quality_snapshot={"quality_status":"COMPLETED","qa_fingerprint_current":"checked"}
    monkeypatch.setattr(report_quality,"quality_state",AsyncMock(return_value=SimpleNamespace(
        can_approve=True,
        latest_validator_run={"id":42,"status":"COMPLETED","current":True},
        qa_fingerprint_current="checked",
        model_dump=lambda mode="python": final_quality_snapshot,
    )))
    monkeypatch.setattr(report_delivery,"case_can_be_delivered",AsyncMock(return_value=True))
    monkeypatch.setattr(report_delivery,"latest_validator_run",AsyncMock(return_value=SimpleNamespace(id=42,status="COMPLETED",context_snapshot={"qa_fingerprint":"checked"})))
    monkeypatch.setattr(report_delivery,"deliver_report_case",AsyncMock(side_effect=ValueError("delivery_failed")))
    await approve_checkpoint_for_test(db, case, step, actor, "report")
    with pytest.raises(ValueError,match="delivery_failed"):
        await report_delivery.approve_and_deliver(db,case.id,actor,value)
    assert (await db.get(StepTask,step.id)).status=="IN_REVIEW"
    assert (await db.get(ReportCase,case.id)).status=="ACTIVE"
    assert await db.scalar(select(func.count(NodeApproval.id)))==0


@pytest.mark.asyncio
async def test_mutually_referencing_candidates_break_the_cycle_instead_of_failing(chain_db):
    from app.application.report_analysis import apply_analysis_run_candidates
    db=chain_db
    case,step,actor,_=await seed_node(db,"S3")
    run=await dummy_run(db,case,step,actor,target="REPORT_ANALYSIS_DRAFT")
    run.workflow_instance_id=case.workflow_instance_id
    run.target_key="S3"
    run.context_snapshot={"analysis_activation_no":step.activation_no}
    run.input_snapshot={"analysis_context":{"evidence":[],"upstream_confirmed_findings":[]}}
    run.output_parsed={"findings":[
        {"finding_key":"S3.F01","claim":"一端是先答应与承担。","kind":"FINDING","semantic_role":"PATTERN","confidence":"MEDIUM","importance":"HIGH","reportability":"RECOMMENDED","evidence_refs":[],"relation_refs":[{"finding_key":"S3.F02","relation":"CONTRASTS_WITH"}],"structured_data":{}},
        {"finding_key":"S3.F02","claim":"另一端是设限与休息。","kind":"FINDING","semantic_role":"PATTERN","confidence":"MEDIUM","importance":"HIGH","reportability":"RECOMMENDED","evidence_refs":[],"relation_refs":[{"finding_key":"S3.F01","relation":"CONTRASTS_WITH"}],"structured_data":{}},
    ],"analysis_fragments":[]}
    await db.commit()

    result=await apply_analysis_run_candidates(db,case_id=case.id,step_key="S3",run_id=run.id,actor=actor)

    rows=list(await db.scalars(select(FindingRevision).where(FindingRevision.is_current.is_(True),FindingRevision.finding_key.in_(["S3.F01","S3.F02"]))))
    assert result["finding_count"]==2
    assert result["pruned_relation_count"]==1
    assert len(rows)==2
    assert sum(1 for row in rows if row.relation_refs)==1

    replay=await apply_analysis_run_candidates(db,case_id=case.id,step_key="S3",run_id=run.id,actor=actor)
    assert replay["finding_count"]==0 and replay["existing_finding_count"]==2


def test_same_type_review_issues_group_into_one_action():
    issues = [
        {"id": "a", "severity": "MAJOR", "type": "事实不一致", "status": "OPEN", "target_key": "x"},
        {"id": "b", "severity": "MAJOR", "type": "事实不一致", "status": "OPEN", "target_key": "y"},
        {"id": "c", "severity": "BLOCK", "type": "事实不一致", "status": "OPEN", "target_key": "z"},
        {"id": "d", "severity": "MINOR", "type": "表达不确定性", "status": "OPEN", "target_key": "w"},
        {"id": "e", "severity": "MAJOR", "type": "事实不一致", "status": "RETAINED", "target_key": "v"},
    ]
    assert group_review_issues(issues) == [{
        "group_key": "MAJOR:事实不一致",
        "type": "事实不一致",
        "severity": "MAJOR",
        "issue_ids": ["a", "b"],
        "target_keys": ["x", "y"],
        "count": 2,
    }]
    assert group_review_issues([]) == []


@pytest.mark.asyncio
async def test_same_type_check_issues_resolve_once_and_keep_per_issue_records(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    await add_test_finding(db, case, step, actor)
    keys = [topic["fragment_key"] for topic in stage_contract("S2")["topics"][:3]]
    output = {"issues": [
        {"severity": "MAJOR", "type": "事实不一致", "target_key": key, "quote": "待验证的解释", "message": "正文未标注假设与限制。"}
        for key in keys
    ]}
    command = await queue_review_command(db, case.id, "S2", actor, ReviewCommandInput(fingerprint=await version(db, case, step), idempotency_key="group-check"), "CHECK")
    await execute_review_command(db, command.id, gateway=Gateway(output))
    issues = [issue for issue in command.output_json["issues"] if issue["severity"] == "MAJOR"]
    assert len(issues) == 3

    workspace = await review_workspace(db, case.id, "S2", actor)
    group = next(row for row in workspace["issue_groups"] if row["type"] == "事实不一致")
    assert group["count"] == 3
    assert sorted(group["issue_ids"]) == sorted(issue["id"] for issue in issues)

    reason = "统一核对：三处结论均改为条件式表达并保留，未新增事实。"
    await resolve_review_issues(db, case.id, "S2", actor, IssueResolutionGroup(
        fingerprint=command.fingerprint, check_id=command.id, issue_ids=group["issue_ids"], resolution="RETAINED", reason=reason))

    resolved = [issue for issue in command.output_json["issues"] if issue["id"] in group["issue_ids"]]
    assert len(resolved) == 3
    assert all(issue["status"] == "RETAINED" for issue in resolved)
    assert all(issue["resolution"] == reason for issue in resolved)
    assert all(issue["resolved_by"] == actor.id and issue["resolved_at"] for issue in resolved)
    assert (await review_workspace(db, case.id, "S2", actor))["issue_groups"] == []

    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    await approve_review(db, case.id, "S2", actor, command.fingerprint)
    assert step.status == "COMPLETED"


@pytest.mark.asyncio
async def test_grouped_resolution_rejects_blocking_and_unknown_issues(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    await add_test_finding(db, case, step, actor)
    key = stage_contract("S2")["topics"][0]["fragment_key"]
    output = {"issues": [
        {"severity": "MAJOR", "type": "事实不一致", "target_key": key, "quote": "待验证的解释", "message": "未标注假设。"},
        {"severity": "BLOCK", "type": "覆盖不足", "target_key": key, "quote": "测试资料", "message": "缺少覆盖。"},
    ]}
    command = await queue_review_command(db, case.id, "S2", actor, ReviewCommandInput(fingerprint=await version(db, case, step), idempotency_key="group-block"), "CHECK")
    await execute_review_command(db, command.id, gateway=Gateway(output))
    issues = command.output_json["issues"]
    blocking = next(issue for issue in issues if issue["severity"] == "BLOCK")
    major = next(issue for issue in issues if issue["severity"] == "MAJOR")

    with pytest.raises(ValueError, match="node_issue_resolution_invalid"):
        await resolve_review_issues(db, case.id, "S2", actor, IssueResolutionGroup(
            fingerprint=command.fingerprint, check_id=command.id, issue_ids=[blocking["id"], major["id"]], resolution="RETAINED", reason="整体保留"))

    with pytest.raises(ValueError, match="node_issue_resolution_invalid"):
        await resolve_review_issues(db, case.id, "S2", actor, IssueResolutionGroup(
            fingerprint=command.fingerprint, check_id=command.id, issue_ids=["missing-id"], resolution="RETAINED", reason="整体保留"))

    assert all(issue["status"] == "OPEN" for issue in command.output_json["issues"])

@pytest.mark.asyncio
async def test_completed_node_keeps_its_completed_check_after_later_changes(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    await add_test_finding(db, case, step, actor)
    command = await queue_review_command(db, case.id, "S2", actor, ReviewCommandInput(fingerprint=await version(db, case, step), idempotency_key="history"), "CHECK")
    await execute_review_command(db, command.id, gateway=Gateway({"issues": []}))
    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    await approve_review(db, case.id, "S2", actor, command.fingerprint)
    assert step.status == "COMPLETED"

    profile = {**((case.application_snapshot or {}).get("profile") or {}), "name": "后续节点更新后的资料"}
    case.application_snapshot = {**(case.application_snapshot or {}), "profile": profile}
    await db.commit()

    workspace = await review_workspace(db, case.id, "S2", actor)
    assert workspace["check"] is not None and workspace["check"]["id"] == command.id
    assert workspace["check_historical"] is True
    assert [issue["id"] for issue in workspace["issues"]] == [issue["id"] for issue in command.output_json["issues"]]
    assert workspace["can_approve"] is False

def test_self_withdrawn_check_notes_are_recorded_but_not_pending():
    snapshot={"fragments":[{"fragment_key":"a","content":"已声明为假设的内容。"}],"findings":[],"evidence":[]}
    output={"issues":[
        {"target_key":"a","quote":"已声明为假设的内容。","severity":"MAJOR","root_key":"real","message":"与资料中的口径不一致，需要核对。"},
        {"target_key":"a","quote":"已声明为假设的内容。","severity":"MAJOR","root_key":"real-2","message":"覆盖缺少一条来源，需要补充。"},
        {"target_key":"a","quote":"已声明为假设的内容。","severity":"MAJOR","root_key":"withdrawn","message":"该段已声明为假设，符合要求，无问题。此条为误报，撤回。"},
        {"target_key":"a","quote":"已声明为假设的内容。","severity":"MINOR","root_key":"kept","message":"该表述并非误报，建议补充来源。"},
    ]}
    accepted,rejected=normalize_ai_issues(output,snapshot)
    assert not rejected
    by_message={issue["message"]:issue for issue in accepted}
    withdrawn=by_message["该段已声明为假设，符合要求，无问题。此条为误报，撤回。"]
    assert withdrawn["status"]=="WITHDRAWN" and withdrawn["withdrawn_reason"]==withdrawn["message"]
    assert by_message["该表述并非误报，建议补充来源。"]["status"]=="OPEN"
    real_ids={by_message["与资料中的口径不一致，需要核对。"]["id"], by_message["覆盖缺少一条来源，需要补充。"]["id"]}
    assert {issue["id"] for issue in approval_blockers(accepted)}==real_ids
    groups=group_review_issues(accepted)
    assert [group["count"] for group in groups]==[2]
    assert set(groups[0]["issue_ids"])==real_ids and withdrawn["id"] not in groups[0]["issue_ids"]


@pytest.mark.asyncio
async def test_self_withdrawn_ai_issue_does_not_require_manual_handling(chain_db):
    db = chain_db
    case, step, actor, _ = await seed_node(db)
    await add_test_finding(db, case, step, actor)
    keys = [topic["fragment_key"] for topic in stage_contract("S2")["topics"][:3]]
    output = {"issues": [
        {"severity": "MAJOR", "type": "事实不一致", "target_key": keys[0], "quote": "待验证的解释", "message": "正文未标注假设与限制。"},
        {"severity": "MAJOR", "type": "事实不一致", "target_key": keys[1], "quote": "待验证的解释", "message": "覆盖说明与来源不一致。"},
        {"severity": "MAJOR", "type": "表达不确定性", "target_key": keys[2], "quote": "待验证的解释", "message": "该段已声明为假设，符合要求，无问题。此条为误报，撤回。"},
    ]}
    command = await queue_review_command(db, case.id, "S2", actor, ReviewCommandInput(fingerprint=await version(db, case, step), idempotency_key="self-withdrawn"), "CHECK")
    await execute_review_command(db, command.id, gateway=Gateway(output))
    issues = {issue["type"]: issue for issue in command.output_json["issues"] if issue["source"] == "AI"}
    assert issues["表达不确定性"]["status"] == "WITHDRAWN"
    assert issues["事实不一致"]["status"] == "OPEN"

    workspace = await review_workspace(db, case.id, "S2", actor)
    assert [issue["type"] for issue in workspace["issues"] if issue["status"] == "WITHDRAWN"] == ["表达不确定性"]
    assert [group["type"] for group in workspace["issue_groups"]] == ["事实不一致"]
    assert workspace["can_approve"] is False

    group = workspace["issue_groups"][0]
    await resolve_review_issues(db, case.id, "S2", actor, IssueResolutionGroup(
        fingerprint=command.fingerprint, check_id=command.id, issue_ids=group["issue_ids"], resolution="RETAINED", reason="统一核对：已标注条件式表达并保留。"))
    await approve_checkpoint_for_test(db, case, step, actor, "findings")
    await approve_checkpoint_for_test(db, case, step, actor, "analysis")
    await approve_review(db, case.id, "S2", actor, command.fingerprint)
    assert step.status == "COMPLETED"
