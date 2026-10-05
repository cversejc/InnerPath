from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.domains.content.reasoning_contract import (
    ANALYSIS_STRUCTURES, normalize_structured_analysis, reasoning_issues,
    validate_action_reasoning, validate_timeline_source,
)
from app.domains.content.report_content_plan import build_report_content_plan, validate_report_content_plan
from app.domains.content.framework_coverage import report_coverage_issues
from app.domains.skills.bindings import resolve_case_skill, PRODUCTION_KEYS
from app.domains.skills.definitions import default_narrative_skill_specifications
from app.domains.skills.runtime import execute_skill, ModelCompletion, SkillExecutionError, _validate_authoring_output
from app.domains.skills.service import create_skill_draft, publish_skill_version, create_skill_run
from app.domains.workflow.service import create_report_case, create_workflow_draft, publish_workflow_version
from app.domains.workflow.definitions import default_workflow_definition
from tests.test_product_framework import semantic_fixture, authored_fixture, coverage
from tests.test_report_quality_delivery import quality_db


@pytest.mark.asyncio
async def test_truncated_model_response_is_never_accepted_even_if_json_looks_complete():
    class TruncatedGateway:
        async def complete(self, **kwargs):
            return ModelCompletion(content='{}', trace={"finish_reason": "length"})
    spec = default_narrative_skill_specifications()[0]
    skill = SimpleNamespace(id=1, version=1, skill_key=spec["identity"]["skill_key"], specification_json=spec)
    with pytest.raises(SkillExecutionError, match="skill_output_truncated") as error:
        await execute_skill(skill_version=skill, input_data={"profile": {},
            "context": {"semantic_model": semantic_fixture()}}, gateway=TruncatedGateway())
    assert error.value.model_trace["output_validation"] == "failed"


@pytest.mark.asyncio
async def test_case_and_workflow_keep_all_skill_versions_after_new_publication(quality_db):
    db = quality_db
    workflow = await create_workflow_draft(db, "report.production", "Frozen", default_workflow_definition(), None)
    await publish_workflow_version(db, workflow.id, None)
    first = await create_report_case(db, user_id=1, service_request_id=None, source_report_task_id=None,
        application_snapshot={}, workflow_version=workflow)
    assert PRODUCTION_KEYS.issubset(first.application_snapshot["skill_bindings"])
    for key in sorted(PRODUCTION_KEYS):
        original = await resolve_case_skill(db, first, key)
        spec = deepcopy(original.specification_json)
        spec["instructions"]["objective"] += " Updated acceptance version."
        published = await create_skill_draft(db, skill_key=key, name=original.name,
            category=original.category, specification=spec, created_by=1)
        await publish_skill_version(db, published.id, published_by=1)
        assert (await resolve_case_skill(db, first, key)).id == original.id
        with pytest.raises(ValueError, match="case_skill_version_mismatch"):
            await create_skill_run(db, skill_version_id=published.id, report_case_id=first.id,
                idempotency_key=f"wrong-{key}", input_snapshot={}, context_snapshot={})
    second = await create_report_case(db, user_id=1, service_request_id=None, source_report_task_id=None,
        application_snapshot={}, workflow_version=workflow)
    assert second.application_snapshot["skill_bindings"] == first.application_snapshot["skill_bindings"]
    new_workflow = await create_workflow_draft(db, "report.production", "New", default_workflow_definition(), None)
    await publish_workflow_version(db, new_workflow.id, None)
    third = await create_report_case(db, user_id=1, service_request_id=None, source_report_task_id=None,
        application_snapshot={}, workflow_version=new_workflow)
    assert all(third.application_snapshot["skill_bindings"][k]["id"] !=
               first.application_snapshot["skill_bindings"][k]["id"] for k in PRODUCTION_KEYS)


@pytest.mark.asyncio
async def test_changed_or_retired_bound_skill_is_rejected_without_fallback(quality_db):
    db = quality_db
    workflow = await create_workflow_draft(db, "report.production", "Frozen", default_workflow_definition(), None)
    await publish_workflow_version(db, workflow.id, None)
    case = await create_report_case(db, user_id=1, service_request_id=None, source_report_task_id=None,
        application_snapshot={}, workflow_version=workflow)
    skill = await resolve_case_skill(db, case, "report.fragment_authoring")
    original = deepcopy(skill.specification_json)
    skill.specification_json = {**original, "changed": True}
    with pytest.raises(ValueError, match="case_skill_binding_changed"):
        await resolve_case_skill(db, case, skill.skill_key)
    skill.specification_json = original
    skill.status = "RETIRED"
    with pytest.raises(ValueError, match="case_skill_binding_changed"):
        await resolve_case_skill(db, case, skill.skill_key)


def test_analysis_requires_real_structure_or_explicit_deferral():
    key = "analysis.s2.complex"
    record = {**coverage(), "details": {f: "明确假设并核对" for f in ANALYSIS_STRUCTURES[key]}}
    assert normalize_structured_analysis(key, record, "可核对的内容")["status"] == "FULFILLED"
    del record["details"]["protection"]
    with pytest.raises(ValueError, match="reasoning_analysis_details_required"):
        normalize_structured_analysis(key, record, "可核对的内容")
    deferred = {**coverage(status="DEFERRED"), "details": {}}
    assert normalize_structured_analysis(key, deferred, "可核对的内容")["follow_up_questions"]
    with pytest.raises(ValueError, match="framework_core_cannot_be_omitted"):
        normalize_structured_analysis(key, {**coverage(status="NOT_APPLICABLE"), "details": {}}, "可核对的内容")


def test_source_bound_action_rejects_wrong_resource_blocks_and_calculated_only_evidence():
    for change, expected in [
        (lambda p: p.update(resource_refs=["persona"]), "reasoning_resource_reference_invalid"),
        (lambda p: p.update(block_refs=["block.3"]), "reasoning_block_reference_mismatch"),
        (lambda p: p.update(evidence_refs=["calc"]), "reasoning_reality_evidence_required"),
        (lambda p: p.update(tool="与动作不同的工具"), "reasoning_action_path_required"),
    ]:
        model = semantic_fixture()
        action = next(f for f in model["findings"] if f["semantic_role"] == "ACTION")
        change(action["structured_data"]["reasoning_path"])
        with pytest.raises(ValueError, match=expected):
            validate_action_reasoning(model["findings"], {"q", "calc"}, reality_keys={"q"})


def test_individual_confirmation_cannot_skip_action_shape_or_use_lowercase_role_to_skip_reasoning():
    model = semantic_fixture()
    action = next(f for f in model["findings"] if f["semantic_role"] == "ACTION")
    sources = [f for f in model["findings"] if f["semantic_role"] != "ACTION"]
    validate_action_reasoning([*sources, action], {"q", "calc"}, reality_keys={"q"}, check_count=False)
    action["structured_data"]["frequency"] = "whenever"
    with pytest.raises(ValueError, match="report_analysis_experiment_invalid"):
        validate_action_reasoning([*sources, action], {"q", "calc"}, reality_keys={"q"}, check_count=False)
    action["structured_data"]["frequency"] = "weekly"
    action["semantic_role"] = "action"
    action["structured_data"].pop("reasoning_path")
    with pytest.raises(ValueError, match="reasoning_action_path_required"):
        validate_action_reasoning([*sources, action], {"q", "calc"}, reality_keys={"q"}, check_count=False)


def test_timeline_uses_referenced_actual_calculated_years():
    model = semantic_fixture()
    row = next(f for f in model["analysis_fragments"] if f["fragment_key"] == "analysis.s3.timeline")
    record = row["source_snapshot"]["structured_analysis"]
    validate_timeline_source(record, model["evidence"], {"calc"})
    with pytest.raises(ValueError, match="reasoning_period_source_mismatch"):
        validate_timeline_source(record, model["evidence"], {"q"})
    record["details"]["periods"][0]["start_year"] = 2021
    with pytest.raises(ValueError, match="reasoning_period_source_mismatch"):
        validate_timeline_source(record, model["evidence"], {"calc"})


def test_internal_resources_are_kept_as_required_action_sources_and_never_introduced_as_persona():
    model = semantic_fixture()
    model["findings"][0]["reportability"] = "INTERNAL_ONLY"
    plan = build_report_content_plan(model, {})
    assert not reasoning_issues(model)
    assert not [i for i in validate_report_content_plan(plan, model, {}) if i["severity"] == "BLOCK"]
    growth = next(s for s in plan["fragments"] if s["fragment_key"] == "report.direction.growth_experiments")
    assert "s1.foundation" in growth["required_finding_refs"]
    assert growth["finding_roles"]["s1.foundation"] == "REFERENCE"
    authored = authored_fixture(plan)
    body = next(f for f in authored if f["fragment_key"] == growth["fragment_key"])
    body["source_snapshot"]["findings"] = [r for r in body["source_snapshot"]["findings"] if r["finding_key"] != "s1.foundation"]
    assert any(i["type"] == "framework_action_source_uncovered" for i in report_coverage_issues(plan, authored))


def test_missing_structured_reasoning_blocks_content_plan_even_with_all_38_analysis_keys():
    model = semantic_fixture()
    next(a for a in model["analysis_fragments"] if a["fragment_key"] == "analysis.s2.mapping")["source_snapshot"].pop("structured_analysis")
    plan = build_report_content_plan(model, {})
    assert plan["status"] == "BLOCKED"
    assert any(i["target_fragment"] == "analysis.s2.mapping" for i in reasoning_issues(model))


def test_narrative_priority_blocks_are_individual_supported_blocks_not_chapter_groups():
    model = semantic_fixture()
    candidate = {"candidate_key": "c", "theme": "有来源的主线", "rationale": "具体矛盾",
        "supporting_findings": ["persona"], "deemphasized_findings": [], "narrative_arc": [],
        "priority_blocks": [{"title": f"卡点{i}", "finding_refs": [f"block.{i}"]} for i in range(4)]}
    output = {"candidates": [candidate, {**deepcopy(candidate), "candidate_key": "d"}]}
    context = {"context": {"semantic_model": model}}
    _validate_authoring_output(output, context, "reports.narrative_candidates")
    candidate["priority_blocks"][0]["finding_refs"] = ["persona"]
    with pytest.raises(ValueError, match="reasoning_priority_block_invalid"):
        _validate_authoring_output(output, context, "reports.narrative_candidates")
    candidate["priority_blocks"][0]["finding_refs"] = ["block.0", "block.1"]
    with pytest.raises(ValueError, match="reasoning_priority_block_invalid"):
        _validate_authoring_output(output, context, "reports.narrative_candidates")
