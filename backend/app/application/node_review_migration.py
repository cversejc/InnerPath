"""Dry-run impact inventory and resumable upgrade of unfinished production cases."""
from sqlalchemy import select

from app.core.time import utc_now_naive
from app.domains.workflow.models import ReportCase, WorkflowInstance, WorkflowVersion, StepTask
from app.domains.workflow.service import enqueue_outbox_event
from app.domains.content.models import CaseEvidenceItem
from app.domains.content.evidence import retract_case_evidence
from app.domains.skills.models import SkillRun
from app.domains.skills.bindings import freeze_report_skills
from app.domains.review.models import POLICY_VERSION
from app.domains.reports.generation.birth_time import resolve_birth_time
from app.application.node_review_workspace import save_metadata


async def migrate_reviews(db, *, apply=False):
    cases = list(await db.scalars(select(ReportCase).join(WorkflowInstance, ReportCase.workflow_instance_id == WorkflowInstance.id).join(WorkflowVersion, WorkflowInstance.workflow_version_id == WorkflowVersion.id).where(WorkflowVersion.workflow_key == "report.production", ReportCase.status.not_in(["DELIVERED", "CANCELLED"]), ReportCase.review_policy_version.is_(None)).order_by(ReportCase.id).with_for_update()))
    inventory = []
    for case in cases:
        tasks = list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id).order_by(StepTask.sequence_no)))
        runs = list(await db.scalars(select(SkillRun).where(SkillRun.report_case_id == case.id, SkillRun.status.in_(["PENDING", "RUNNING"]))))
        try:
            time = resolve_birth_time((case.application_snapshot or {}).get("profile") or {})
        except (KeyError, TypeError, ValueError):
            time = {"status": "NEEDS_CONFIRMATION", "limitations": ["出生资料不完整"]}
        record = {"case_id": case.id, "earliest_review": "S1", "time_status": time["status"],
                  "in_flight_run_ids": [r.id for r in runs], "legacy_reviews": [{"step_key": t.step_key, "status": t.status, "activation_no": t.activation_no, "result": t.result_json} for t in tasks],
                  "reason": "新时间口径与整体审核政策需要核验；旧签核保留，不转为新时间确认"}
        inventory.append(record)
        if not apply:
            continue
        if any(run.status == "RUNNING" for run in runs):
            # Wait for the model call to finish; do not race an older deployment's writer.
            record["migration_status"] = "WAITING_FOR_RUNNING_TASKS"
            continue
        bindings = (case.application_snapshot or {}).get("skill_bindings") or await freeze_report_skills(db)
        await save_metadata(db, case.id, "S1", {"migration": record, "runtime_skill_bindings": bindings, "core_review": {}})
        for run in runs:
            run.status = "FAILED"
            run.error = "archived_by_node_review_migration"
            run.completed_at = utc_now_naive()
            run.context_snapshot = {**(run.context_snapshot or {}), "node_archived": "legacy_policy"}
        for evidence in list(await db.scalars(select(CaseEvidenceItem).where(CaseEvidenceItem.report_case_id == case.id, CaseEvidenceItem.status == "ACTIVE"))):
            if isinstance(evidence.value_json, dict) and evidence.value_json.get("calculation_version") == "mingli-v2" and not evidence.value_json.get("birth_time"):
                await retract_case_evidence(db, report_case_id=case.id, evidence_key=evidence.evidence_key, reason="review_time_policy_requires_recalculation")
        case.review_policy_version = POLICY_VERSION
        waiting = case.status == "BLOCKED"
        case.status = "BLOCKED" if waiting else "ACTIVE"
        instance = await db.get(WorkflowInstance, case.workflow_instance_id)
        instance.status = "SUSPENDED" if waiting else "RUNNING"
        instance.completed_at = None
        for task in tasks:
            task.activation_no += 1
            task.status = ("IN_REVIEW" if waiting else "READY") if task.step_key == "S1" else "PENDING"
            task.completed_at = None
            task.started_at = None
            task.last_error = None
        first = next(t for t in tasks if t.step_key == "S1")
        if not waiting:
            await enqueue_outbox_event(db, aggregate_type="workflow_instance", aggregate_id=instance.id, event_type="workflow.step.ready", payload={"report_case_id": case.id, "step_task_id": first.id, "activation_no": first.activation_no})
        record["migration_status"] = "MIGRATED"
    if apply:
        await db.commit()
    return inventory
