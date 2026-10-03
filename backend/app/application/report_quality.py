from copy import deepcopy
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.report_generation import current_report_coherence_context
from app.domains.quality.programmatic import collect_programmatic_issues
from app.domains.quality.schemas import QAIssueResponse, ReportQualityResponse
from app.domains.quality.service import (
    get_case_qa_issues,
    latest_validator_run,
    resolve_qa_issue,
    run_programmatic_qa,
)
from app.domains.quality.models import QAIssue
from app.domains.quality.scorecard import RUBRIC
from app.domains.skills.models import SkillRun
from app.domains.skills.service import create_skill_run, ensure_default_validator_skill_version
from app.domains.workflow.models import ReportCase, WorkflowOutbox


async def queue_case_quality_run(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    actor_id: int,
    idempotency_key: str,
) -> dict:
    locked_case = await db.scalar(
        select(ReportCase)
        .where(ReportCase.id == report_case.id)
        .with_for_update()
    )
    if locked_case is None:
        raise ValueError("report_case_not_found")
    report_case = locked_case
    program_issues, fingerprint, snapshot = await run_programmatic_qa(
        db, report_case, actor_id=actor_id
    )
    if any(issue.severity == "BLOCK" for issue in program_issues):
        return {
            "status": "PROGRAMMATIC_BLOCKED",
            "validator_run": None,
            "issues": program_issues,
            "qa_fingerprint": fingerprint,
        }

    skill = await ensure_default_validator_skill_version(db)
    active_run = await db.scalar(
        select(SkillRun)
        .where(
            SkillRun.report_case_id == report_case.id,
            SkillRun.target_type == "REPORT_QA",
            SkillRun.status.in_({"PENDING", "RUNNING"}),
        )
        .order_by(SkillRun.created_at.desc(), SkillRun.id.desc())
        .limit(1)
    )
    if active_run is not None:
        if (active_run.context_snapshot or {}).get("qa_fingerprint") != fingerprint:
            raise ValueError("validator_run_in_progress")
        return {
            "status": active_run.status,
            "validator_run": active_run,
            "issues": program_issues,
            "qa_fingerprint": fingerprint,
        }
    existing = await db.scalar(
        select(SkillRun).where(SkillRun.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.report_case_id != report_case.id or existing.target_type != "REPORT_QA":
            raise ValueError("skill_run_idempotency_conflict")
        return {
            "status": existing.status,
            "validator_run": existing,
            "issues": program_issues,
            "qa_fingerprint": fingerprint,
        }

    request_snapshot = report_case.application_snapshot or {}
    narrative_plan_snapshot = deepcopy(snapshot["narrative_plan"])
    coherence_context = await current_report_coherence_context(
        db, report_case.id
    )
    if narrative_plan_snapshot is not None and coherence_context is not None:
        plan_json = narrative_plan_snapshot.get("plan_json") or {}
        generation = plan_json.get("generation") or {}
        generation["chapter_checks"] = coherence_context["chapter_checks"]
        generation["coherence"] = coherence_context["coherence"]
        generation["issues"] = coherence_context["issues"]
        plan_json["generation"] = generation
        narrative_plan_snapshot["plan_json"] = plan_json
    qa_input = {
        "scorecard_required": True,
        "scoring_rubric": RUBRIC,
        "application_context": {
            "context": request_snapshot.get("context") or {},
            "selected_topics": request_snapshot.get("selected_topics") or [],
        },
        "confirmed_semantics": snapshot["semantic_model"],
        "narrative_plan": narrative_plan_snapshot,
        "content_plan": (
            (narrative_plan_snapshot.get("plan_json") or {}).get("content_plan")
            if narrative_plan_snapshot
            else None
        ),
        "validation_scope": [
            "source_fidelity",
            "chapter_coherence",
            "report_coherence",
            "repetition",
            "block_to_action_link",
            "safety",
        ],
        "report_fragments": [
            {
                "fragment_key": row["fragment_key"],
                "revision_no": row["revision_no"],
                "title": row["title"],
                "content": row["content"],
                "source_snapshot": row["source_snapshot"],
            }
            for row in snapshot["fragments"]
        ],
    }
    profile = request_snapshot.get("profile") or {}
    input_data = {"profile": {"name": profile.get("name")}, "context": {"qa_input": qa_input}}
    safe_input = {
        "profile": {"name": profile.get("name")},
        "context": deepcopy(input_data["context"]),
    }
    run, created = await create_skill_run(
        db,
        skill_version_id=skill.id,
        idempotency_key=idempotency_key,
        input_snapshot=safe_input,
        context_snapshot={"qa_fingerprint": fingerprint},
        run_type="VALIDATE",
        target_type="REPORT_QA",
        target_key="report.final",
        report_case_id=report_case.id,
        workflow_instance_id=report_case.workflow_instance_id,
    )
    if created:
        db.add(
            WorkflowOutbox(
                aggregate_type="skill_run",
                aggregate_id=run.id,
                event_type="skill.run.requested",
                payload_json={"skill_run_id": run.id},
                status="PENDING",
                retry_count=0,
                created_at=datetime.utcnow(),
            )
        )
        await db.flush()
    return {
        "status": run.status,
        "validator_run": run,
        "issues": program_issues,
        "qa_fingerprint": fingerprint,
    }


async def quality_state(
    db: AsyncSession, report_case: ReportCase
) -> ReportQualityResponse:
    issue_history = await get_case_qa_issues(db, report_case.id)
    run = await latest_validator_run(db, report_case.id)
    _, current_fingerprint, _ = await collect_programmatic_issues(db, report_case)
    fingerprint_matches = bool(
        run
        and run.status == "COMPLETED"
        and (run.context_snapshot or {}).get("qa_fingerprint") == current_fingerprint
    )
    issues = [
        issue
        for issue in issue_history
        if (
            issue.source_type == "PROGRAMMATIC"
            and (issue.evidence_json or {}).get("qa_fingerprint") == current_fingerprint
        )
        or (
            issue.source_type == "VALIDATOR"
            and run is not None
            and fingerprint_matches
            and issue.source_ref_id == run.id
        )
    ]
    open_issues = [issue for issue in issues if issue.status == "OPEN"]
    scorecard_required = bool(run and ((run.context_snapshot or {}).get("context") or {}).get("qa_input", {}).get("scorecard_required"))
    scorecard_ready = not scorecard_required or bool(run and (run.output_parsed or {}).get("scorecard", {}).get("passes_threshold"))
    return ReportQualityResponse(
        report_case_id=report_case.id,
        quality_status=(
            "PROGRAMMATIC_BLOCKED"
            if any(
                issue.source_type == "PROGRAMMATIC"
                and issue.status == "OPEN"
                and issue.severity == "BLOCK"
                for issue in issues
            )
            else run.status if run else "NOT_RUN"
        ),
        latest_validator_run=(
            {
                "id": run.id,
                "status": run.status,
                "error": run.error,
                "model_trace": run.model_trace,
                "completed_at": run.completed_at,
                "scorecard": (run.output_parsed or {}).get("scorecard") if fingerprint_matches else None,
            }
            if run
            else None
        ),
        issues=issues,
        can_approve=fingerprint_matches and not open_issues and scorecard_ready,
        blocking_count=sum(issue.severity == "BLOCK" for issue in open_issues),
        open_count=len(open_issues),
        qa_fingerprint_current=current_fingerprint,
    )


async def case_can_be_delivered(db: AsyncSession, report_case: ReportCase) -> bool:
    state = await quality_state(db, report_case)
    return state.can_approve


async def delivery_quality_snapshot(
    db: AsyncSession, report_case: ReportCase
) -> dict:
    state = await quality_state(db, report_case)
    if not state.can_approve:
        raise ValueError("final_qa_issues_open_or_stale")
    issue_history = await get_case_qa_issues(db, report_case.id)
    return {
        "can_approve": True,
        "quality_status": state.quality_status,
        "qa_fingerprint": state.qa_fingerprint_current,
        "blocking_count": state.blocking_count,
        "open_count": state.open_count,
        "issues": [
            QAIssueResponse.model_validate(issue).model_dump(mode="json")
            for issue in issue_history
        ],
        "validator_run_id": (state.latest_validator_run or {}).get("id"),
        "scorecard": (state.latest_validator_run or {}).get("scorecard"),
    }


async def close_case_qa_issue(
    db: AsyncSession,
    *,
    report_case_id: int,
    issue_id: int,
    status: str,
    resolution: str,
    actor_id: int,
) -> QAIssue:
    return await resolve_qa_issue(
        db,
        report_case_id=report_case_id,
        issue_id=issue_id,
        status=status,
        resolution=resolution,
        actor_id=actor_id,
    )
