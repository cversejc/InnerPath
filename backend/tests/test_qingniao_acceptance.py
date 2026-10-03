"""Replay saved, real-model demo through persistence and release gates, offline."""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_report_quality_delivery import quality_db, StubGateway
from app.application.report_analysis import get_analysis_step_completion_gate
from app.application.skill_runtime import queue_allocated_fragment_skill_run, execute_skill_run_record
from app.application.report_quality import queue_case_quality_run, quality_state, delivery_quality_snapshot
from app.application.report_delivery import snapshot_case_skill_runs
from app.domains.content.evidence import create_evidence_item
from app.domains.content.findings import create_finding_revision
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.models import ContentFragmentRevision
from app.domains.content.narrative import confirm_narrative_plan, semantic_source_snapshot
from app.domains.content.queries import load_case_semantic_model
from app.domains.delivery.assembler import assemble_report_version
from app.domains.quality.service import resolve_qa_issue
from app.domains.skills.service import ensure_default_analysis_skill_versions, ensure_default_narrative_skill_versions, create_skill_run
from app.domains.workflow.models import ReportCase, WorkflowVersion, WorkflowInstance, StepTask

ARTIFACTS = Path(__file__).resolve().parents[2] / "docs" / "acceptance" / "qingniao"


def read(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def artifact_hash(name):
    """Bind content without depending on Windows/Git newline conversion."""
    canonical = json.dumps(read(name), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_reviewed_qingniao_reaches_immutable_report_with_full_provenance(quality_db):
    db, now = quality_db, datetime.utcnow()
    input_data = read("input.json")
    case = ReportCase(user_id=1, status="ACTIVE", application_snapshot={"profile": input_data["profile"], "context": input_data["context"]}, application_submitted_at=now, created_at=now, updated_at=now)
    db.add(case)
    version = WorkflowVersion(workflow_key="demo", name="Offline demo", version=1, status="PUBLISHED", definition_json={"steps": []}, created_at=now)
    db.add(version)
    await db.flush()
    instance = WorkflowInstance(report_case_id=case.id, workflow_version_id=version.id, status="RUNNING", created_at=now, updated_at=now)
    db.add(instance)
    await db.flush()
    case.workflow_instance_id = instance.id
    for evidence in input_data["evidence"]:
        assumed = evidence["source_type"] == "DEMO_ASSUMPTION"
        await create_evidence_item(db, report_case_id=case.id, evidence_key=evidence["evidence_key"], source_type="EXTERNAL_REFERENCE" if assumed else evidence["source_type"], source_ref="demo.assumption" if assumed else evidence["evidence_key"], value=evidence["value"])
    steps = []
    for index in range(1, 7):
        step = StepTask(workflow_instance_id=instance.id, step_key=f"S{index}", sequence_no=index, executor="HYBRID", status="PENDING", activation_no=1, config_snapshot={}, created_at=now, updated_at=now)
        db.add(step)
        steps.append(step)
    await db.flush()
    skills = await ensure_default_analysis_skill_versions(db)
    for index, skill in enumerate(skills):
        step = steps[index]
        step.status = "IN_REVIEW"
        record = read(f"{step.step_key}.json")
        assert record["review"]["status"] == "DEVELOPER_ACCEPTED_FOR_DEMO"
        run, _ = await create_skill_run(db, skill_version_id=skill.id, report_case_id=case.id, step_task_id=step.id, idempotency_key=f"demo-{step.step_key}", input_snapshot={}, context_snapshot={}, target_type="ANALYSIS_DRAFT", target_key=step.step_key)
        run.status, run.output_parsed, run.model_trace = "COMPLETED", record["output"], record["trace"]
        for finding in record["output"]["findings"]:
            await create_finding_revision(db, report_case_id=case.id, status="CONFIRMED", owner_step_task_id=step.id, source_skill_run_id=run.id, **finding)
        for fragment in record["output"]["analysis_fragments"]:
            await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=fragment["fragment_key"], title=fragment["title"], content=fragment["content"], finding_refs=fragment["finding_refs"], evidence_refs=fragment["evidence_refs"], status="CONFIRMED", owner_step_task_id=step.id, source_skill_run_id=run.id)
        gate = await get_analysis_step_completion_gate(db, case_id=case.id, step_key=step.step_key, actor=SimpleNamespace(id=1, role="admin"))
        assert gate["can_complete"] and not gate["missing_topics"]
        step.status = "COMPLETED"
    planner = (await ensure_default_narrative_skill_versions(db))[0]
    model = await load_case_semantic_model(db, case.id)
    candidate_record = read("S5-candidates.json")
    candidate_run, _ = await create_skill_run(db, skill_version_id=planner.id, report_case_id=case.id, idempotency_key="demo-plan", input_snapshot={}, context_snapshot={"semantic_source_snapshot": semantic_source_snapshot(model)}, target_type="NARRATIVE_CANDIDATES", target_key="S5")
    candidate_run.status, candidate_run.output_parsed = "COMPLETED", candidate_record["output"]
    saved_plan = read("S5-plan.json")["plan"]
    plan = await confirm_narrative_plan(db, report_case_id=case.id, skill_run_id=candidate_run.id, candidate_key=saved_plan["selected_candidate"], overrides={"priority_blocks": saved_plan["priority_blocks"]}, actor_id=1)
    assert plan.plan_json["content_plan"]["status"] == "READY"
    authored = {f["fragment_key"]: f for f in read("S5-report.json")["fragments"]}
    for allocation in plan.plan_json["content_plan"]["fragments"]:
        output = authored[allocation["fragment_key"]]
        run, _ = await queue_allocated_fragment_skill_run(db, report_case=case, step=steps[4], plan=plan, semantic_model=model, allocation=allocation, idempotency_key=f'demo-write-{allocation["fragment_key"]}', continuity={})
        completed = await execute_skill_run_record(db, run.id, gateway=StubGateway(json.dumps(output, ensure_ascii=False)))
        assert completed.status == "COMPLETED", (allocation["fragment_key"], completed.error)
        row = await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case.id, ContentFragmentRevision.fragment_key == allocation["fragment_key"], ContentFragmentRevision.is_current.is_(True)))
        await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=row.fragment_key, fragment_type="REPORT", content=row.content, title=row.title, status="CONFIRMED", edit_kind="STYLE")
    plan.plan_json = {**plan.plan_json, "generation": {"status": "READY_FOR_REVIEW", "issues": []}}
    steps[4].status = "COMPLETED"
    queued = await queue_case_quality_run(db, report_case=case, actor_id=1, idempotency_key="demo-qa")
    assert queued["status"] != "PROGRAMMATIC_BLOCKED", [(i.issue_type, i.message) for i in queued["issues"]]
    qa = read("S6.json")["output"]
    review = read("S6-review.json")
    assert review["hash_format"] == "canonical-json-utf8-sorted-compact"
    assert review["qa_sha256"] == artifact_hash("S6.json")
    assert review["report_sha256"] == artifact_hash("S5-report.json")
    assert qa["scorecard"]["passes_threshold"]
    completed = await execute_skill_run_record(db, queued["validator_run"].id, gateway=StubGateway(json.dumps(qa, ensure_ascii=False)))
    assert completed.status == "COMPLETED", completed.error
    state = await quality_state(db, case)
    for issue in state.issues:
        if issue.status == "OPEN":
            if issue.source_type == "VALIDATOR":
                decision = next(d for d in review["decisions"] if d["message"] == issue.message and d["issue_type"] == issue.issue_type)
                status, reason = decision["status"], decision["resolution"]
            else:
                assert issue.issue_type == "FINDING_OVER_REPEATED" and issue.severity == "MINOR"
                status, reason = "ACCEPTED", "来源复用承担概览/深入/回应不同职责，核查正文未发现三次完整重复；不是真实咨询师签字。"
            await resolve_qa_issue(db, report_case_id=case.id, issue_id=issue.id, status=status, resolution=f"开发验收：{reason}", actor_id=1)
    state = await quality_state(db, case)
    assert state.can_approve
    steps[5].status = "COMPLETED"
    steps[5].result_json = {"final_gate_approved": True, "attested_by": 1, "note": "Offline developer test only", "validator_run_id": completed.id}
    case.status, instance.status = "READY_TO_DELIVER", "COMPLETED"
    await db.flush()
    snapshot = await delivery_quality_snapshot(db, case)
    report = await assemble_report_version(db, case, actor_id=1, quality_snapshot=snapshot, skill_run_snapshot=await snapshot_case_skill_runs(db, case.id))
    assert len(report.fragment_snapshot) == len(authored)
    sections = report.structured_data["structured_sections"]
    assert sections[0]["fragment_key"] == "report.overview.psychic_structure"
    assert sections[0]["section_key"] == "identity"
    assert sections[-1]["fragment_key"] == "report.ending"
    assert sections[-1]["section_key"] == "direction"
    assert report.semantic_snapshot["quality"]["scorecard"]["passes_threshold"]
    assert {f"S{i}" for i in range(1, 5)} <= {r["target_key"] for r in report.semantic_snapshot["skill_runs"]}
