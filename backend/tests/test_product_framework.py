"""Coverage is a content contract, not a count of section headings or source IDs."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.domains.content.product_framework import framework_snapshot, validate_framework
from app.domains.content.reasoning_contract import reasoning_snapshot, ANALYSIS_STRUCTURES, PATH_FIELDS
from app.domains.content.framework_coverage import (
    normalize_coverage, normalize_requirement_coverage, normalize_framework_review, report_coverage_issues,
)
from app.domains.content.action_contract import validate_growth_experiments
from app.domains.content.report_content_plan import build_report_content_plan, validate_report_content_plan
from app.domains.content.queries import load_case_semantic_model
from app.domains.content.evidence import create_evidence_item
from app.domains.content.findings import create_finding_revision
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.narrative import confirm_narrative_plan, semantic_source_snapshot
from app.domains.content.models import ContentFragmentRevision
from app.domains.workflow.definitions import default_workflow_definition
from app.domains.workflow.models import StepTask
from app.domains.workflow.service import create_report_case, create_workflow_draft, publish_workflow_version
from app.domains.skills.service import ensure_default_narrative_skill_versions, create_skill_run
from app.domains.skills.runtime import _validate_authoring_output, _validate_analysis_draft_output
from app.domains.skills.analysis_sop import stage_contract
from app.application.report_analysis import get_analysis_step_completion_gate
from app.application.skill_runtime import execute_skill_run_record, queue_allocated_fragment_skill_run
from app.application.report_quality import queue_case_quality_run, quality_state
from app.domains.quality.service import resolve_qa_issue
from tests.test_report_quality_delivery import quality_db, StubGateway


def coverage(content="可核对的内容", status="FULFILLED"):
    return {"status": status, "reason": "依据与边界已说明", "quote": content,
            "follow_up_questions": ["请提供一个具体事件"] if status == "DEFERRED" else []}


def semantic_fixture():
    findings = [dict(finding_key=k, semantic_role=r, claim=k, kind="FINDING", confidence="MEDIUM",
                     importance="HIGH", reportability="RECOMMENDED", evidence_refs=["q"],
                     relation_refs=[], structured_data={}) for k, r in [
        ("s1.foundation", "STRUCTURE"), ("persona", "PERSONA"), ("authority", "AUTHORITY_SUPEREGO"),
        ("shadow", "SHADOW"), ("energy", "ENERGY"), ("relation", "RELATIONSHIP"),
        ("direction", "SELF_DIRECTION"), ("stage", "CURRENT_STAGE"),
        *[(f"block.{i}", "BLOCK") for i in range(4)], *[(f"action.{i}", "ACTION") for i in range(3)]]]
    for index, action in enumerate(f for f in findings if f["semantic_role"] == "ACTION"):
        action["structured_data"] = {"block_refs": [f"block.{index}"] if index < 2 else ["block.2", "block.3"],
            "method": "CBT日常记录", "steps": ["观察一次低风险情境"], "frequency": "weekly",
            "duration_minutes": 5, "observation": "实际反馈", "stop_rule": "不适暂停"}
        action["structured_data"]["reasoning_path"] = {
            "resource_refs": ["s1.foundation"], "block_refs": list(action["structured_data"]["block_refs"]),
            "evidence_refs": ["q"], **{field: "测试推导" for field in PATH_FIELDS}, "tool": "CBT日常记录"}
    analyses = []
    for requirement in framework_snapshot()["analysis_requirements"]:
        key = requirement["fragment_key"]
        ref = "s1.foundation" if requirement["stage"] == "S1" else "authority" if key.endswith(("mapping", "authority")) else "direction" if requirement["stage"] == "S3" else "persona"
        analyses.append({"fragment_key": key, "title": key, "content": "可核对的内容", "revision_no": 1,
            "semantic_revision": 1, "source_snapshot": {"findings": [{"finding_key": ref}],
                "evidence": [{"evidence_key": "q"}], "framework_coverage": coverage()}})
        if key in ANALYSIS_STRUCTURES:
            details = {field: "测试推导" for field in ANALYSIS_STRUCTURES[key]}
            if "periods" in details:
                details["periods"] = [{"start_year": 2020, "end_year": 2029,
                    **{field: "测试阶段" for field in ("interaction", "theme", "capacity", "old_pattern")}}]
                analyses[-1]["source_snapshot"]["evidence"].append({"evidence_key": "calc"})
            analyses[-1]["source_snapshot"]["structured_analysis"] = {**coverage(), "details": details}
    return {"findings": findings, "analysis_fragments": analyses,
            "evidence": [{"evidence_key": "q", "source_type": "USER_PROVIDED"},
                {"evidence_key": "calc", "source_type": "SYSTEM_CALCULATED", "value": {
                    "bazi_facts": {"dayun": [{"start_year": 2020, "end_year": 2029}]}}}],
            "framework_contract": framework_snapshot(), "reasoning_contract": reasoning_snapshot()}


def authored_fixture(plan):
    return [{"fragment_key": s["fragment_key"], "title": s["fragment_key"], "content": "可核对的内容",
             "source_snapshot": {"requirement_coverage": [{"requirement_id": r["requirement_id"], **coverage()}
                for r in s.get("requirements", [])], "fragments": [{"fragment_key": k} for k in s.get("analysis_refs", [])],
                "findings": [{"finding_key": k} for k in s.get("finding_refs", [])]}} for s in plan["fragments"]]


def review_fixture(plan, contract, fragments):
    return [{"requirement_id": r["requirement_id"],
             "fragment_keys": [s["fragment_key"] for s in plan["fragments"]
                 if any(q["requirement_id"] == r["requirement_id"] for q in s.get("requirements", []))],
             **coverage()} for r in contract["report_requirements"]]


def test_malformed_model_coverage_and_action_references_raise_validation_errors():
    with pytest.raises(ValueError, match="framework_coverage_required"):
        normalize_coverage({**coverage(), "status": []}, "可核对的内容")
    with pytest.raises(ValueError, match="framework_requirement_coverage_incomplete"):
        normalize_requirement_coverage([{"requirement_id": []}], [], "可核对的内容")
    model = semantic_fixture()
    plan = build_report_content_plan(model, {})
    fragments = authored_fixture(plan)
    review = review_fixture(plan, model["framework_contract"], fragments)
    review[0]["fragment_keys"] = [{}]
    with pytest.raises(ValueError, match="framework_review_fragment_invalid"):
        normalize_framework_review(review, model["framework_contract"], plan, fragments)
    actions = [f for f in model["findings"] if f["semantic_role"] == "ACTION"]
    actions[0]["structured_data"]["block_refs"] = [{}]
    with pytest.raises(ValueError, match="report_analysis_experiment_invalid"):
        validate_growth_experiments(actions, model["findings"])


def test_version_freezes_all_38_analysis_and_16_report_duties():
    frozen = framework_snapshot()
    assert len(frozen["analysis_requirements"]) == 38
    assert len(frozen["report_requirements"]) == 16
    frozen["report_requirements"][0]["checks"] = []
    with pytest.raises(ValueError, match="version_invalid"):
        validate_framework(frozen)
    assert framework_snapshot()["report_requirements"][0]["checks"]


def test_all_analysis_ids_cannot_substitute_for_self_belief_or_core_report_content():
    semantic = semantic_fixture()
    plan = build_report_content_plan(semantic, {"must_include_findings": ["persona"]})
    assert not validate_report_content_plan(plan, semantic, {})
    self_spec = next(s for s in plan["fragments"] if s["fragment_key"] == "report.identity.self_perception")
    assert self_spec["required"] and "analysis.s2.authority" in self_spec["analysis_refs"]
    assert "authority" in self_spec["finding_refs"]
    plan["fragments"].remove(self_spec)
    assert any(i.get("requirement_id") == "R.self_belief" for i in validate_report_content_plan(plan, semantic, {}))


def test_must_include_is_enforced_even_if_planner_leaves_it_out():
    semantic = semantic_fixture()
    del semantic["framework_contract"]
    required = [dict(semantic["findings"][0], finding_key=f"required.{i}", semantic_role="CUSTOM_FACT",
                     importance="LOW", reportability="MUST_INCLUDE") for i in range(4)]
    semantic["findings"].extend(required)
    plan = build_report_content_plan(semantic, {"must_include_findings": ["persona"]})
    assert all(plan["coverage"][f["finding_key"]] for f in required)
    for spec in plan["fragments"]:
        spec["finding_refs"] = [key for key in spec["finding_refs"] if key != "required.0"]
    assert any(i["type"] == "CONTENT_PLAN_MUST_INCLUDE_UNASSIGNED" for i in validate_report_content_plan(plan, semantic, {"must_include_findings": ["persona"]}))


def test_wrong_action_role_zero_actions_and_unaddressed_blocks_are_rejected():
    semantic = semantic_fixture()
    validate_growth_experiments(semantic["findings"])
    with pytest.raises(ValueError, match="count_invalid"):
        validate_growth_experiments([])
    semantic["findings"][-1]["structured_data"]["block_refs"] = ["persona"]
    with pytest.raises(ValueError, match="experiment_invalid"):
        validate_growth_experiments(semantic["findings"])
    plan = build_report_content_plan(semantic, {})
    issues = validate_report_content_plan(plan, semantic, {})
    assert any(i["type"] == "report_analysis_experiment_invalid" for i in issues)
    assert any(i["type"] == "FRAMEWORK_BLOCK_ACTION_UNCOVERED" for i in issues)


def test_deferred_is_an_explicit_boundary_and_requires_a_question():
    assert normalize_coverage(coverage(status="DEFERRED"), "可核对的内容")["status"] == "DEFERRED"
    with pytest.raises(ValueError, match="follow_up_required"):
        normalize_coverage({**coverage(status="DEFERRED"), "follow_up_questions": []}, "可核对的内容")
    with pytest.raises(ValueError, match="core_cannot_be_omitted"):
        normalize_coverage(coverage(status="NOT_APPLICABLE"), "可核对的内容")
    with pytest.raises(ValueError, match="coverage_invalid"):
        normalize_coverage(coverage(), "完全不同的正文")


def test_body_source_ids_and_author_declarations_do_not_replace_independent_review():
    semantic = semantic_fixture()
    plan = build_report_content_plan(semantic, {})
    authored = authored_fixture(plan)
    assert report_coverage_issues(plan, authored) == []
    review = review_fixture(plan, semantic["framework_contract"], authored)
    review[0]["status"] = "MISSING"
    review[0]["reason"] = "未表达四层心灵结构"
    output = {"issues": [], "framework_review": review}
    _validate_authoring_output(output, {"context": {"qa_input": {"framework_contract": semantic["framework_contract"],
        "content_plan": plan, "report_fragments": authored}}}, "reports.validator")
    assert output["issues"][0]["severity"] == "BLOCK"
    # Removing one block from the QA evidence must not be treated as reviewing all blocks.
    blocks = next(r for r in review if r["requirement_id"] == "R.blocks")
    blocks["fragment_keys"] = blocks["fragment_keys"][:1]
    with pytest.raises(ValueError, match="review_fragment_invalid"):
        normalize_framework_review(review, semantic["framework_contract"], plan, authored)


def test_missing_declarations_or_changed_text_block_report_coverage():
    semantic = semantic_fixture()
    plan = build_report_content_plan(semantic, {})
    authored = authored_fixture(plan)
    authored[0]["source_snapshot"] = {"findings": [{"finding_key": "persona"}]}
    assert report_coverage_issues(plan, authored)
    authored = authored_fixture(plan)
    authored[0]["content"] = "文字发生了变化"
    assert report_coverage_issues(plan, authored)


def test_new_analysis_run_requires_content_status_not_just_all_topic_ids():
    semantic = semantic_fixture()
    context = {"analysis_context": {"step_key": "S2", "framework_contract": semantic["framework_contract"],
        "sop_contract": stage_contract("S2"), "evidence": [{"evidence_key": "q"}],
        "upstream_confirmed_findings": semantic["findings"]}}
    output = {"summary": "测试", "findings": [], "risk_flags": [], "analysis_fragments": [
        {"fragment_key": a["fragment_key"], "title": a["title"], "content": a["content"],
         "finding_refs": [r["finding_key"] for r in a["source_snapshot"]["findings"]],
         "evidence_refs": ["q"], "framework_coverage": coverage()}
        for a in semantic["analysis_fragments"] if a["fragment_key"].startswith("analysis.s2.")]}
    _validate_analysis_draft_output(output, context)
    output["analysis_fragments"][0].pop("framework_coverage")
    with pytest.raises(ValueError, match="coverage_required"):
        _validate_analysis_draft_output(output, context)


@pytest.mark.asyncio
async def test_new_case_enforces_framework_through_persistence_authoring_and_final_gate(quality_db):
    db = quality_db
    version = await create_workflow_draft(db, "report.production", "Framework", default_workflow_definition(), None)
    await publish_workflow_version(db, version.id, None)
    intake = {"profile": {}, "context": {}}
    case = await create_report_case(db, user_id=1, service_request_id=None, source_report_task_id=None,
        application_snapshot=intake, workflow_version=version)
    assert "framework_contract" not in intake
    assert case.application_snapshot["framework_contract"] == framework_snapshot()
    # Exercise the original framework/persistence gate; whole-node approval is
    # separately exercised by test_node_review with the new policy enabled.
    assert case.review_policy_version == "six-node-review-v1"
    case.review_policy_version = None
    await create_evidence_item(db, report_case_id=case.id, evidence_key="q", source_type="USER_PROVIDED", source_ref="questionnaire", value="synthetic test")
    await create_evidence_item(db, report_case_id=case.id, evidence_key="calc", source_type="SYSTEM_CALCULATED",
        source_ref="synthetic calculation", value={"bazi_facts": {"dayun": [{"start_year": 2020, "end_year": 2029}]}})
    steps = list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id).order_by(StepTask.sequence_no)))
    semantic = semantic_fixture()
    for finding in semantic["findings"]:
        await create_finding_revision(db, report_case_id=case.id, status="CONFIRMED", **finding)
    for analysis in semantic["analysis_fragments"]:
        step = next(s for s in steps if analysis["fragment_key"].startswith(f"analysis.{s.step_key.lower()}."))
        await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=analysis["fragment_key"],
            content=analysis["content"], title=analysis["title"], status="CONFIRMED", owner_step_task_id=step.id,
            finding_refs=[r["finding_key"] for r in analysis["source_snapshot"]["findings"]],
            evidence_refs=[r["evidence_key"] for r in analysis["source_snapshot"]["evidence"]],
            framework_coverage=coverage(), structured_analysis=analysis["source_snapshot"].get("structured_analysis"))
    for step in steps[:4]:
        step.status = "COMPLETED"
    steps[3].status = "IN_REVIEW"
    gate = await get_analysis_step_completion_gate(db, case_id=case.id, step_key="S4", actor=SimpleNamespace(id=1, role="admin"))
    assert gate["can_complete"]
    analysis_row = await db.scalar(select(ContentFragmentRevision).where(
        ContentFragmentRevision.report_case_id == case.id,
        ContentFragmentRevision.fragment_key == "analysis.s4.energy"))
    saved_snapshot = deepcopy(analysis_row.source_snapshot)
    analysis_row.source_snapshot = {**saved_snapshot, "framework_coverage": coverage(status="MISSING")}
    assert not (await get_analysis_step_completion_gate(db, case_id=case.id, step_key="S4", actor=SimpleNamespace(id=1, role="admin")))["can_complete"]
    analysis_row.source_snapshot = saved_snapshot
    steps[3].status, steps[4].status = "COMPLETED", "IN_REVIEW"
    model = await load_case_semantic_model(db, case.id)
    assert model["framework_contract"] == framework_snapshot()
    assert "relation_refs" in model["findings"][0]
    planner = (await ensure_default_narrative_skill_versions(db))[0]
    candidate, _ = await create_skill_run(db, skill_version_id=planner.id, report_case_id=case.id,
        idempotency_key="framework-plan", input_snapshot={}, context_snapshot={"semantic_source_snapshot": semantic_source_snapshot(model)}, target_type="NARRATIVE_CANDIDATES")
    candidate.status = "COMPLETED"
    candidate.output_parsed = {"candidates": [{"candidate_key": "c", "theme": "测试", "supporting_findings": ["persona"], "priority_blocks": []}]}
    plan = await confirm_narrative_plan(db, report_case_id=case.id, skill_run_id=candidate.id, candidate_key="c", overrides={}, actor_id=1)
    content_plan = plan.plan_json["content_plan"]
    assert content_plan["status"] == "READY", content_plan["validation_issues"]
    for spec in content_plan["fragments"]:
        output = {"status": "READY_FOR_REVIEW", "title": spec["fragment_key"], "content": "可核对的内容",
            "used_findings": spec["finding_refs"], "used_analysis_fragments": spec["analysis_refs"],
            "used_actions": spec["action_refs"], "transition_hint": "", "presentation_meta": {},
            "requirement_coverage": [{"requirement_id": r["requirement_id"], **coverage()} for r in spec.get("requirements", [])]}
        run, _ = await queue_allocated_fragment_skill_run(db, report_case=case, step=steps[4], plan=plan, semantic_model=model,
            allocation=spec, idempotency_key=spec["fragment_key"], continuity={})
        completed = await execute_skill_run_record(db, run.id, gateway=StubGateway(json.dumps(output, ensure_ascii=False)))
        assert completed.status == "COMPLETED", completed.error
        await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=spec["fragment_key"],
            fragment_type="REPORT", content=output["content"], status="CONFIRMED", edit_kind="STYLE")
    plan.plan_json = {**plan.plan_json, "generation": {"status": "READY_FOR_REVIEW"}}
    queued = await queue_case_quality_run(db, report_case=case, actor_id=1, idempotency_key="framework-qa")
    assert queued["status"] != "PROGRAMMATIC_BLOCKED", [(i.issue_type, i.message) for i in queued["issues"]]
    from app.domains.quality.scorecard import RUBRIC
    rows = list(await db.scalars(select(ContentFragmentRevision).where(ContentFragmentRevision.fragment_type == "REPORT")))
    fragments = [{"fragment_key": r.fragment_key, "content": r.content} for r in rows if r.is_current]
    review = review_fixture(content_plan, model["framework_contract"], fragments)
    review[0]["status"] = "MISSING"
    scorecard = {"dimensions": {k: {"score": v, "reason": "Synthetic", "fragment_keys": [fragments[0]["fragment_key"]]} for k, v in RUBRIC.items()}}
    qa = await execute_skill_run_record(db, queued["validator_run"].id,
        gateway=StubGateway(json.dumps({"issues": [], "scorecard": scorecard, "framework_review": review}, ensure_ascii=False)))
    assert qa.status == "COMPLETED", qa.error
    state = await quality_state(db, case)
    for issue in state.issues:
        if issue.status == "OPEN":
            await resolve_qa_issue(db, report_case_id=case.id, issue_id=issue.id, status="RESOLVED", resolution="仅关闭问题不能伪装为补齐", actor_id=1)
    assert not (await quality_state(db, case)).can_approve
    # Repair the missing content, creating a new revision and a new quality fingerprint.
    overview = next(r for r in rows if r.is_current and r.fragment_key == "report.overview.psychic_structure")
    overview_spec = next(s for s in content_plan["fragments"] if s["fragment_key"] == overview.fragment_key)
    revised_text = "向世界展示的我→眼中的自己→潜意识层面的自己→整合后的方向"
    await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=overview.fragment_key,
        fragment_type="REPORT", content=revised_text, status="CONFIRMED", requirement_coverage=[
            {"requirement_id": r["requirement_id"], **coverage(revised_text)} for r in overview_spec["requirements"]])
    assert not (await quality_state(db, case)).can_approve
    repaired = await queue_case_quality_run(db, report_case=case, actor_id=1, idempotency_key="framework-qa-repaired")
    assert repaired["status"] != "PROGRAMMATIC_BLOCKED"
    review = review_fixture(content_plan, model["framework_contract"], fragments)
    review[0].update(coverage(revised_text))
    rerun = await execute_skill_run_record(db, repaired["validator_run"].id,
        gateway=StubGateway(json.dumps({"issues": [], "scorecard": scorecard, "framework_review": review}, ensure_ascii=False)))
    assert rerun.status == "COMPLETED", rerun.error
    state = await quality_state(db, case)
    for issue in state.issues:
        if issue.status == "OPEN":
            assert issue.severity != "BLOCK"
            await resolve_qa_issue(db, report_case_id=case.id, issue_id=issue.id, status="ACCEPTED", resolution="合成用例中的来源复用提示", actor_id=1)
    assert (await quality_state(db, case)).can_approve
