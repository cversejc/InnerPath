"""Import reviewed Qingniao artifacts into the local development workbench.

Creates a dedicated consultant and synthetic client. Never resets existing
passwords; generated credentials are printed once, never stored in this file.
This is a developer-reviewed demo, not a real consultation or live AI run.
"""
import argparse
import asyncio
import hashlib
import json
import secrets
from datetime import datetime
from app.core.time import utc_now_naive
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.application.report_analysis import get_analysis_step_completion_gate
from app.application.report_cases import ensure_default_workflow_version
from app.application.report_delivery import approve_case_final_gate, deliver_report_case
from app.application.report_quality import queue_case_quality_run, quality_state
from app.application.skill_runtime import queue_allocated_fragment_skill_run, execute_skill_run_record
from app.domains.content.evidence import create_evidence_item
from app.domains.content.findings import create_finding_revision
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.models import ContentFragmentRevision
from app.domains.content.narrative import confirm_narrative_plan, semantic_source_snapshot
from app.domains.content.queries import load_case_semantic_model
from app.domains.quality.service import resolve_qa_issue
from app.domains.service_requests.models import ServiceRequest
from app.domains.skills.service import ensure_default_analysis_skill_versions, ensure_default_narrative_skill_versions, create_skill_run
from app.domains.workflow.models import StepTask, WorkflowOutbox
from app.domains.workflow.service import create_report_case

CONSULTANT_PHONE = "19900001002"
CLIENT_PHONE = "19900001001"
DEMO_KEY = "qingniao-reviewed-demo-20261004-v1"


class StoredGateway:
    def __init__(self, output, trace):
        self.output, self.trace = output, trace

    async def complete(self, **kwargs):
        return SimpleNamespace(content=json.dumps(self.output, ensure_ascii=False), trace={**self.trace, "replayed_for_local_demo": True})


async def suppress_demo_dispatch(db, case_id, run_id=None):
    """Consume only demo outbox rows so workers do not rerun accepted output."""
    rows = await db.scalars(select(WorkflowOutbox).where(WorkflowOutbox.status == "PENDING"))
    for row in rows:
        payload = row.payload_json or {}
        if payload.get("report_case_id") == case_id or (run_id is not None and payload.get("skill_run_id") == run_id):
            row.status, row.published_at = "PUBLISHED", utc_now_naive()


async def import_demo(artifacts):
    database = make_url(settings.DATABASE_URL)
    if settings.ENVIRONMENT.lower() not in {"dev", "development", "local"} or database.host not in {"postgres", "localhost", "127.0.0.1"} or database.database != "innerpath":
        raise RuntimeError("This command is restricted to the local innerpath development database")
    engine.echo = False
    read = lambda name: json.loads((artifacts / name).read_text(encoding="utf-8"))
    review = read("S6-review.json")
    for name, key in [("S6.json", "qa_sha256"), ("S5-report.json", "report_sha256")]:
        digest = hashlib.sha256(json.dumps(read(name), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if review[key] != digest:
            raise ValueError("Reviewed artifact fingerprint does not match")
    password = secrets.token_urlsafe(15)
    async with AsyncSessionLocal() as db:
        if await db.scalar(select(ServiceRequest).where(ServiceRequest.idempotency_key == DEMO_KEY)):
            raise RuntimeError("This demo was already imported; no account or password was changed")
        if await db.scalar(select(User).where(User.phone.in_([CONSULTANT_PHONE, CLIENT_PHONE]))):
            raise RuntimeError("Demo phone collision; no existing account was changed")
        consultant = User(phone=CONSULTANT_PHONE, name="青鸟流程演示咨询师", role="consultant", is_active=True, password_hash=get_password_hash(password), phone_verified_at=utc_now_naive())
        client = User(phone=CLIENT_PHONE, name="青鸟 · 出生信息为演示假设", role="user", is_active=True)
        db.add_all([consultant, client])
        await db.flush()
        data = read("input.json")
        snapshot = {"profile": data["profile"], "context": data["context"], "selected_topics": data["context"]["focus_topics"], "demo_fixture": True}
        request = ServiceRequest(user_id=client.id, service_type="report", status="reviewing", assigned_consultant_id=consultant.id, request_payload=snapshot, idempotency_key=DEMO_KEY)
        db.add(request)
        await db.flush()
        version = await ensure_default_workflow_version(db)
        case = await create_report_case(db, user_id=client.id, service_request_id=request.id, source_report_task_id=None, application_snapshot=snapshot, workflow_version=version)
        steps = list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id).order_by(StepTask.sequence_no)))
        for step in steps:
            step.activation_no, step.assignee_id = 1, consultant.id
        for item in data["evidence"]:
            assumed = item["source_type"] == "DEMO_ASSUMPTION"
            await create_evidence_item(db, report_case_id=case.id, evidence_key=item["evidence_key"], source_type="EXTERNAL_REFERENCE" if assumed else item["source_type"], source_ref="demo.assumption" if assumed else item["evidence_key"], value=item["value"])
        skills = await ensure_default_analysis_skill_versions(db)
        for step, skill in zip(steps, skills):
            record = read(f"{step.step_key}.json")
            if record.get("review", {}).get("status") != "DEVELOPER_ACCEPTED_FOR_DEMO":
                raise ValueError("Analysis requires recorded developer acceptance")
            step.status = "IN_REVIEW"
            run, _ = await create_skill_run(db, skill_version_id=skill.id, report_case_id=case.id, step_task_id=step.id, workflow_instance_id=case.workflow_instance_id, idempotency_key=f"{DEMO_KEY}-{step.step_key}", input_snapshot={"profile": data["profile"], "context": data["context"]}, context_snapshot={"analysis_activation_no": 1, "demo_review": record["review"]}, target_type="REPORT_ANALYSIS_DRAFT", target_key=step.step_key)
            run.status, run.output_parsed, run.model_trace = "COMPLETED", record["output"], {**record["trace"], "replayed_for_local_demo": True}
            run.output_raw = json.dumps(record.get("original_model_output", record["output"]), ensure_ascii=False)
            run.completed_at = utc_now_naive()
            for finding in record["output"]["findings"]:
                await create_finding_revision(db, report_case_id=case.id, status="CONFIRMED", owner_step_task_id=step.id, source_skill_run_id=run.id, created_by=consultant.id, **finding)
            for fragment in record["output"]["analysis_fragments"]:
                await create_content_fragment_revision(db, report_case_id=case.id, owner_step_task_id=step.id, source_skill_run_id=run.id, status="CONFIRMED", created_by=consultant.id, **fragment)
            gate = await get_analysis_step_completion_gate(db, case_id=case.id, step_key=step.step_key, actor=consultant)
            if not gate["can_complete"]:
                raise ValueError(f"{step.step_key} coverage gate failed")
            step.status, step.completed_at = "COMPLETED", utc_now_naive()
            step.result_json = {"demo_review": "开发者验收回放，不是真实咨询师签字"}
        planner = (await ensure_default_narrative_skill_versions(db))[0]
        model = await load_case_semantic_model(db, case.id)
        candidate_record = read("S5-candidates.json")
        candidate, _ = await create_skill_run(db, skill_version_id=planner.id, report_case_id=case.id, step_task_id=steps[4].id, idempotency_key=f"{DEMO_KEY}-plan", input_snapshot={}, context_snapshot={"semantic_source_snapshot": semantic_source_snapshot(model)}, target_type="NARRATIVE_CANDIDATES", target_key="S5")
        candidate.status, candidate.output_parsed = "COMPLETED", candidate_record["output"]
        candidate.model_trace, candidate.completed_at = candidate_record["trace"], utc_now_naive()
        selected = read("S5-plan.json")["plan"]
        plan = await confirm_narrative_plan(db, report_case_id=case.id, skill_run_id=candidate.id, candidate_key=selected["selected_candidate"], overrides={"priority_blocks": selected["priority_blocks"]}, actor_id=consultant.id)
        print(json.dumps({"case_id": case.id, "status": "IMPORTING"}, ensure_ascii=False), flush=True)
        authored = {f["fragment_key"]: f for f in read("S5-report.json")["fragments"]}
        for allocation in plan.plan_json["content_plan"]["fragments"]:
            output = authored[allocation["fragment_key"]]
            run, _ = await queue_allocated_fragment_skill_run(db, report_case=case, step=steps[4], plan=plan, semantic_model=model, allocation=allocation, idempotency_key=f'{DEMO_KEY}-write-{allocation["fragment_key"]}', continuity={}, commit=False)
            await suppress_demo_dispatch(db, case.id, run.id)
            completed = await execute_skill_run_record(db, run.id, gateway=StoredGateway(output, {"provider": "reviewed-artifact"}))
            if completed.status != "COMPLETED":
                raise ValueError(completed.error)
            row = await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case.id, ContentFragmentRevision.fragment_key == allocation["fragment_key"], ContentFragmentRevision.is_current.is_(True)))
            await create_content_fragment_revision(db, report_case_id=case.id, fragment_key=row.fragment_key, fragment_type="REPORT", content=row.content, title=row.title, status="CONFIRMED", edit_kind="STYLE", created_by=consultant.id)
        plan.plan_json = {**plan.plan_json, "generation": {"status": "READY_FOR_REVIEW", "issues": []}}
        steps[4].status, steps[5].status = "COMPLETED", "IN_REVIEW"
        steps[4].completed_at = utc_now_naive()
        queued = await queue_case_quality_run(db, report_case=case, actor_id=consultant.id, idempotency_key=f"{DEMO_KEY}-qa")
        if queued["status"] == "PROGRAMMATIC_BLOCKED":
            raise ValueError("Programmatic quality gate failed")
        await suppress_demo_dispatch(db, case.id, queued["validator_run"].id)
        qa_record = read("S6.json")
        completed = await execute_skill_run_record(db, queued["validator_run"].id, gateway=StoredGateway(qa_record["output"], qa_record["trace"]))
        if completed.status != "COMPLETED":
            raise ValueError(completed.error)
        state = await quality_state(db, case)
        for issue in state.issues:
            if issue.status != "OPEN":
                continue
            if issue.source_type == "VALIDATOR":
                decision = next(d for d in review["decisions"] if d["message"] == issue.message and d["issue_type"] == issue.issue_type)
                status, reason = decision["status"], decision["resolution"]
            else:
                if issue.issue_type != "FINDING_OVER_REPEATED" or issue.severity != "MINOR":
                    raise ValueError("Unexpected programmatic issue")
                status, reason = "ACCEPTED", "来源复用承担不同段落职责，经开发验收核对正文未三次完整重复。"
            await resolve_qa_issue(db, report_case_id=case.id, issue_id=issue.id, status=status, resolution=f"演示开发验收，非真实咨询师签字：{reason}", actor_id=consultant.id)
        await approve_case_final_gate(db, report_case=case, actor=consultant, note="已审阅成果导入演示；非真实咨询师签字")
        await deliver_report_case(db, report_case=case, actor=consultant)
        print(json.dumps({"phone": consultant.phone, "password": password, "request_id": request.id, "case_id": case.id, "report_id": request.result_id, "environment": "local-development"}, ensure_ascii=False))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    asyncio.run(import_demo(parser.parse_args().artifacts))
