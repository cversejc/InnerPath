from datetime import datetime
from html import escape

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content.models import ContentFragmentRevision, NarrativePlan
from app.domains.content.queries import load_case_semantic_model
from app.domains.delivery.models import ReportVersion
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
)


SECTION_ORDER = (("identity", "你是谁"), ("challenge", "卡在哪"), ("direction", "往哪去"))


async def assemble_report_version(
    db: AsyncSession,
    report_case: ReportCase,
    *,
    actor_id: int,
    quality_snapshot: dict | None = None,
    skill_run_snapshot: list[dict] | None = None,
) -> ReportVersion:
    if report_case.status != "READY_TO_DELIVER":
        raise ValueError("workflow_not_ready_to_deliver")
    instance = await db.get(WorkflowInstance, report_case.workflow_instance_id)
    if instance is None or instance.status != "COMPLETED":
        raise ValueError("workflow_not_complete")
    final_gate = await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S6",
        )
    )
    if (
        final_gate is None
        or final_gate.status != "COMPLETED"
        or not (final_gate.result_json or {}).get("final_gate_approved")
    ):
        raise ValueError("final_gate_approval_required")
    if not quality_snapshot or quality_snapshot.get("can_approve") is not True:
        raise ValueError("final_qa_issues_open_or_stale")
    if skill_run_snapshot is None:
        raise ValueError("skill_provenance_snapshot_required")
    workflow_version = await db.get(WorkflowVersion, instance.workflow_version_id)
    if workflow_version is None:
        raise ValueError("workflow_version_not_found")
    plan = await db.scalar(
        select(NarrativePlan).where(
            NarrativePlan.report_case_id == report_case.id,
            NarrativePlan.is_current.is_(True),
            NarrativePlan.status == "CONFIRMED",
        )
    )
    if plan is None:
        raise ValueError("narrative_plan_confirmation_required")
    fragment_rows = list(
        await db.scalars(
            select(ContentFragmentRevision)
            .where(
                ContentFragmentRevision.report_case_id == report_case.id,
                ContentFragmentRevision.is_current.is_(True),
                ContentFragmentRevision.fragment_type == "REPORT",
                ContentFragmentRevision.status == "CONFIRMED",
            )
            .order_by(ContentFragmentRevision.fragment_key)
        )
    )
    if not fragment_rows:
        raise ValueError("report_fragments_required")
    semantics = await load_case_semantic_model(db, report_case.id)
    fragment_snapshot = [
        {
            "id": row.id,
            "fragment_key": row.fragment_key,
            "revision_no": row.revision_no,
            "semantic_revision": row.semantic_revision,
            "content_revision": row.content_revision,
            "title": row.title,
            "content": row.content,
            "source_snapshot": row.source_snapshot,
            "source_skill_run_id": row.source_skill_run_id,
            "source_narrative_plan_id": row.source_narrative_plan_id,
        }
        for row in fragment_rows
    ]
    structured_sections = []
    for section_key, section_title in SECTION_ORDER:
        matching = [
            row
            for row in fragment_snapshot
            if row["fragment_key"] == f"report.{section_key}"
            or row["fragment_key"].startswith(f"report.{section_key}.")
        ]
        for row in matching:
            structured_sections.append(
                {
                    "section_key": section_key,
                    "section_title": section_title,
                    "fragment_key": row["fragment_key"],
                    "title": row["title"],
                    "content": row["content"],
                    "revision_no": row["revision_no"],
                }
            )
    extras = [
        row
        for row in fragment_snapshot
        if not any(
            row["fragment_key"] == f"report.{section_key}"
            or row["fragment_key"].startswith(f"report.{section_key}.")
            for section_key, _ in SECTION_ORDER
        )
    ]
    for row in extras:
        structured_sections.append(
            {
                "section_key": "additional",
                "section_title": row["title"] or "补充内容",
                "fragment_key": row["fragment_key"],
                "title": row["title"],
                "content": row["content"],
                "revision_no": row["revision_no"],
            }
        )
    rendered_html = "<article class=\"report-version\">" + "".join(
        "<section data-fragment=\"{}\"><h2>{}</h2><h3>{}</h3><p>{}</p></section>".format(
            escape(item["fragment_key"], quote=True),
            escape(item["section_title"]),
            escape(item.get("title") or ""),
            escape(item["content"]).replace("\n", "<br>"),
        )
        for item in structured_sections
    ) + "</article>"
    latest_version = await db.scalar(
        select(func.max(ReportVersion.version_no)).where(
            ReportVersion.report_case_id == report_case.id
        )
    )
    now = datetime.utcnow()
    version = ReportVersion(
        report_case_id=report_case.id,
        version_no=(latest_version or 0) + 1,
        workflow_version_id=workflow_version.id,
        narrative_plan_id=plan.id,
        fragment_snapshot=fragment_snapshot,
        semantic_snapshot={
            "application_snapshot": report_case.application_snapshot or {},
            "semantics": semantics,
            "narrative_plan": {
                "id": plan.id,
                "version_no": plan.version_no,
                "selected_candidate_key": plan.selected_candidate_key,
                "plan_json": plan.plan_json,
                "source_snapshot": plan.source_snapshot,
            },
            "workflow": {
                "instance_id": instance.id,
                "version_id": workflow_version.id,
                "version": workflow_version.version,
                "definition": workflow_version.definition_json,
            },
            "skill_runs": skill_run_snapshot,
            "quality": quality_snapshot,
            "final_gate": {
                "step_task_id": final_gate.id,
                "activation_no": final_gate.activation_no,
                "completed_at": (
                    final_gate.completed_at.isoformat()
                    if final_gate.completed_at
                    else None
                ),
                "result_json": final_gate.result_json or {},
            },
        },
        structured_data={
            "title": "辰鉴·人生说明书",
            "narrative_plan": plan.plan_json,
            "structured_sections": structured_sections,
            "source_fragment_ids": [row["id"] for row in fragment_snapshot],
            "workflow_version_id": workflow_version.id,
        },
        rendered_html=rendered_html,
        pdf_url=None,
        created_at=now,
        delivered_at=now,
    )
    db.add(version)
    await db.flush()
    return version
