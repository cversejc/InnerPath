from copy import deepcopy
from datetime import datetime, timedelta
from app.core.time import api_datetime, utc_now_naive

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.report_generation import current_report_coherence_context
from app.domains.quality.programmatic import collect_programmatic_issues
from app.domains.quality.schemas import QAIssueResponse, ReportQualityResponse
from app.domains.quality.service import (
    get_case_qa_issues,
    group_quality_issues,
    latest_validator_run,
    resolve_qa_issue,
    run_programmatic_qa,
)
from app.domains.quality.models import QAIssue
from app.domains.quality.scorecard import RUBRIC
from app.domains.content.framework_coverage import normalize_framework_review
from app.domains.skills.models import SkillRun
from app.domains.skills.service import create_skill_run, ensure_default_validator_skill_version
from app.domains.skills.bindings import resolve_case_skill
from app.domains.workflow.models import ReportCase, StepTask, WorkflowOutbox

# Whole-report semantic validation emits a scorecard plus every located issue;
# the 8000-token historical default truncated long reports mid-JSON.
CASE_QA_MAX_TOKENS = 16000
CASE_QA_TIMEOUT_SECONDS = 300
# A queued run that no worker picked up within this window is orphaned (for
# example because the Outbox consumer is not running). An explicit re-run may
# reclaim it instead of being blocked by "validator_run_in_progress" forever.
CASE_QA_QUEUE_TIMEOUT_SECONDS = 300
# Allow the model gateway timeout plus transport overhead before a RUNNING
# run is treated as abandoned.
CASE_QA_STALL_GRACE_SECONDS = 120

# The consultant fast path imports an already written report and only asks for
# a final human authorization. Checks still run and still produce every
# suggestion, but nothing in this policy is a hard gate.
IMPORT_REVIEW_POLICY_VERSION = "import-review-v1"


def _quality_run_timeout_seconds(run: SkillRun) -> int:
    override = (run.context_snapshot or {}).get("model_policy_override") or {}
    try:
        return max(1, int(override.get("timeout_seconds") or CASE_QA_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        return CASE_QA_TIMEOUT_SECONDS


def quality_run_is_stalled(run: SkillRun, *, now: datetime | None = None) -> bool:
    """Report whether a validator run is abandoned and can be reclaimed."""

    current = now or utc_now_naive()
    if run.status == "PENDING":
        return bool(run.created_at) and run.created_at <= current - timedelta(
            seconds=CASE_QA_QUEUE_TIMEOUT_SECONDS
        )
    if run.status == "RUNNING":
        started = run.started_at or run.created_at
        return bool(started) and started <= current - timedelta(
            seconds=_quality_run_timeout_seconds(run) + CASE_QA_STALL_GRACE_SECONDS
        )
    return False


def _validator_run_timing(run: SkillRun, *, now: datetime | None = None) -> dict:
    current = now or utc_now_naive()
    queued_at = run.created_at
    started_at = run.started_at
    active_since = started_at or queued_at
    # Finished runs report how long they actually took; only an active run keeps
    # counting up, so the workbench never shows a stale timer next to a result.
    reference = run.completed_at if run.status in {"COMPLETED", "FAILED"} else None
    measured_at = reference or current
    return {
        "created_at": api_datetime(queued_at),
        "started_at": api_datetime(started_at),
        "queue_wait_seconds": (
            max(0, int((started_at - queued_at).total_seconds()))
            if started_at and queued_at
            else None
        ),
        "elapsed_seconds": (
            max(0, int((measured_at - active_since).total_seconds())) if active_since else None
        ),
        "queue_timeout_seconds": CASE_QA_QUEUE_TIMEOUT_SECONDS,
        "run_timeout_seconds": _quality_run_timeout_seconds(run),
    }


async def _release_stalled_quality_run(db: AsyncSession, run: SkillRun) -> None:
    """Fail an abandoned run and retire its Outbox event.

    Retiring the event matters: a consumer that starts later must not rerun an
    action the user has already retried.
    """

    run.status = "FAILED"
    run.error = "quality_run_stalled"
    run.completed_at = utc_now_naive()
    events = list(
        await db.scalars(
            select(WorkflowOutbox).where(
                WorkflowOutbox.aggregate_type == "skill_run",
                WorkflowOutbox.aggregate_id == run.id,
                WorkflowOutbox.event_type == "skill.run.requested",
                WorkflowOutbox.status.in_({"PENDING", "PUBLISHED"}),
            )
        )
    )
    for event in events:
        event.status = "FAILED"
        event.retry_count += 1


async def queue_case_quality_run(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    actor_id: int,
    idempotency_key: str,
    runtime_instruction: str | None = None,
    source_run_id: int | None = None,
    step_task: StepTask | None = None,
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
    if (
        report_case.review_policy_version != IMPORT_REVIEW_POLICY_VERSION
        and any(issue.severity == "BLOCK" for issue in program_issues)
    ):
        # Strict policies stop before spending a model call. The fast path keeps
        # going so the consultant still sees the full check result as advice.
        return {
            "status": "PROGRAMMATIC_BLOCKED",
            "validator_run": None,
            "issues": program_issues,
            "qa_fingerprint": fingerprint,
        }

    skill = await resolve_case_skill(db, report_case, "report.final_validator")
    feedback = (runtime_instruction or "").strip()
    if feedback and source_run_id is None:
        raise ValueError("quality_feedback_source_required")
    previous_run = None
    if source_run_id is not None:
        previous_run = await db.scalar(
            select(SkillRun).where(SkillRun.id == source_run_id)
        )
        if (
            previous_run is None
            or previous_run.report_case_id != report_case.id
            or previous_run.workflow_instance_id != report_case.workflow_instance_id
            or previous_run.skill_version_id != skill.id
            or previous_run.target_type != "REPORT_QA"
            or previous_run.target_key != "report.final"
            or previous_run.run_type != "VALIDATE"
            or (
                step_task is not None
                and previous_run.step_task_id not in {None, step_task.id}
            )
            or (
                step_task is not None
                and (previous_run.context_snapshot or {}).get(
                    "quality_activation_no"
                )
                not in {None, step_task.activation_no}
            )
            or previous_run.status != "COMPLETED"
            or not isinstance(previous_run.output_parsed, dict)
            or (previous_run.context_snapshot or {}).get("qa_fingerprint") != fingerprint
        ):
            raise ValueError("quality_feedback_source_invalid")
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
    if active_run is not None and quality_run_is_stalled(active_run):
        await _release_stalled_quality_run(db, active_run)
        await db.flush()
        active_run = None
    if active_run is not None:
        if feedback or source_run_id is not None:
            raise ValueError("validator_run_in_progress")
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
    if snapshot["semantic_model"].get("framework_contract"):
        qa_input["framework_contract"] = snapshot["semantic_model"]["framework_contract"]
    profile = request_snapshot.get("profile") or {}
    quality_context = {"qa_input": qa_input}
    if previous_run is not None:
        quality_context["feedback_rerun"] = {
            "source_run_id": previous_run.id,
            "previous_ai_output": deepcopy(previous_run.output_parsed),
        }
    input_data = {"profile": {"name": profile.get("name")}, "context": quality_context}
    safe_input = {
        "profile": {"name": profile.get("name")},
        "context": deepcopy(input_data["context"]),
    }
    run, created = await create_skill_run(
        db,
        skill_version_id=skill.id,
        idempotency_key=idempotency_key,
        input_snapshot=safe_input,
        context_snapshot={
            "qa_fingerprint": fingerprint,
            "node_review_policy": report_case.review_policy_version,
            # Reasoning tokens count against the same budget; the whole-report
            # pass must spend it on the JSON result, not on hidden thinking.
            "model_policy_override": {
                "thinking": False,
                "max_tokens": CASE_QA_MAX_TOKENS,
                "timeout_seconds": CASE_QA_TIMEOUT_SECONDS,
            },
            **(
                {"quality_activation_no": step_task.activation_no}
                if step_task is not None
                else {}
            ),
            **(
                {"quality_feedback_source_run_id": previous_run.id}
                if previous_run is not None
                else {}
            ),
        },
        run_type="VALIDATE",
        target_type="REPORT_QA",
        target_key="report.final",
        report_case_id=report_case.id,
        workflow_instance_id=report_case.workflow_instance_id,
        step_task_id=step_task.id if step_task is not None else None,
        runtime_instruction=feedback or None,
    )
    if created:
        if report_case.review_policy_version == "six-node-review-v1" and not feedback:
            run.runtime_instruction = "每项事实、语义或表达问题须指定实际target_fragment_key，evidence须从该片段正文逐字摘录。全篇问题也须引用具体正文，不得只写泛泛的评语。评分门槛由程序依据scorecard判断。"
        db.add(
            WorkflowOutbox(
                aggregate_type="skill_run",
                aggregate_id=run.id,
                event_type="skill.run.requested",
                payload_json={"skill_run_id": run.id},
                status="PENDING",
                retry_count=0,
                created_at=utc_now_naive(),
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
    open_issues = [issue for issue in issues if issue.status == "OPEN" and issue.severity in {"BLOCK", "MAJOR"}]
    scorecard_required = bool(run and ((run.context_snapshot or {}).get("context") or {}).get("qa_input", {}).get("scorecard_required"))
    scorecard_ready = not scorecard_required or bool(run and (run.output_parsed or {}).get("scorecard", {}).get("passes_threshold"))
    framework_ready = True
    # The fast path imports a consultant-authored report: there is no authored
    # Finding/coverage provenance for the framework mapper to reconcile, so the
    # product-framework review is not part of this policy's gate.
    if (
        report_case.review_policy_version != "import-review-v1"
        and (report_case.application_snapshot or {}).get("framework_contract")
    ):
        framework_ready = False
        if run and fingerprint_matches:
            qa_input = ((run.context_snapshot or {}).get("context") or {}).get("qa_input", {})
            try:
                review = normalize_framework_review((run.output_parsed or {}).get("framework_review"),
                    qa_input.get("framework_contract"), qa_input.get("content_plan") or {}, qa_input.get("report_fragments") or [])
                framework_ready = all(item["status"] != "MISSING" for item in review)
            except ValueError:
                pass
    advisory_only = report_case.review_policy_version == IMPORT_REVIEW_POLICY_VERSION
    can_approve = (
        fingerprint_matches and not open_issues and scorecard_ready and framework_ready
    )
    # The fast path never blocks on check results: the check is optional advice,
    # so the consultant may confirm and deliver at any time, with or without it.
    can_finalize = True if advisory_only else can_approve
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
                "current": fingerprint_matches,
                "error": run.error,
                "runtime_instruction": run.runtime_instruction,
                "feedback_source_run_id": (run.context_snapshot or {}).get(
                    "quality_feedback_source_run_id"
                ),
                "model_trace": run.model_trace,
                "completed_at": api_datetime(run.completed_at),
                "scorecard": (run.output_parsed or {}).get("scorecard") if fingerprint_matches else None,
                "framework_review": (run.output_parsed or {}).get("framework_review") if fingerprint_matches else None,
                **_validator_run_timing(run),
            }
            if run
            else None
        ),
        issues=issues,
        issue_groups=group_quality_issues(issues),
        can_approve=can_approve,
        advisory_only=advisory_only,
        can_finalize=can_finalize,
        final_gate_override=(
            await _persisted_import_override(db, report_case, current_fingerprint)
            if advisory_only
            else None
        ),
        unresolved_advisories=(
            _advisory_summary(open_issues) if advisory_only else []
        ),
        blocking_count=sum(issue.severity == "BLOCK" for issue in open_issues),
        open_count=len(open_issues),
        qa_fingerprint_current=current_fingerprint,
    )


def _advisory_summary(issues: list[QAIssue]) -> list[dict]:
    return [
        {
            "id": issue.id,
            "severity": issue.severity,
            "issue_type": issue.issue_type,
            "target_fragment_key": issue.target_fragment_key,
            "message": issue.message,
        }
        for issue in issues
    ]


async def _persisted_import_override(
    db: AsyncSession,
    report_case: ReportCase,
    current_fingerprint: str,
) -> dict | None:
    """Return the stored fast-path gate approval while it still applies.

    The approval may have been given with no validator run at all, so it is
    matched to the report text it was given for instead of to a check. Only the
    S6 row written by :func:`approve_case_final_gate` can authorize an overridden
    delivery; the client never supplies these fields.
    """

    gate = await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S6",
        )
    )
    result = (gate.result_json or {}) if gate is not None else {}
    if (
        not result.get("final_gate_approved")
        or not result.get("advisory_only")
        or result.get("qa_fingerprint") != current_fingerprint
    ):
        return None
    return dict(result)


async def case_can_be_delivered(db: AsyncSession, report_case: ReportCase) -> bool:
    state = await quality_state(db, report_case)
    return state.can_approve


async def delivery_quality_snapshot(
    db: AsyncSession, report_case: ReportCase
) -> dict:
    state = await quality_state(db, report_case)
    # The fast path has no quality gate at all: checks are optional advice and
    # the S6 approval recorded by the consultant is the only authorization.
    if not state.advisory_only and not state.can_approve:
        raise ValueError("final_qa_issues_open_or_stale")
    issue_history = await get_case_qa_issues(db, report_case.id)
    return {
        "can_approve": state.can_approve,
        "advisory_only": state.advisory_only,
        "final_gate_override": state.final_gate_override,
        "unresolved_advisories": state.unresolved_advisories,
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
        "framework_review": (state.latest_validator_run or {}).get("framework_review") or [],
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


async def close_case_qa_issues(
    db: AsyncSession,
    *,
    report_case_id: int,
    issue_ids: list[int],
    status: str,
    resolution: str,
    actor_id: int,
) -> list[QAIssue]:
    """同类问题整体处理：一次填写依据，每条问题仍保留独立处理记录。"""
    existing = {
        row.id: row
        for row in await db.scalars(
            select(QAIssue).where(
                QAIssue.report_case_id == report_case_id,
                QAIssue.id.in_(issue_ids),
            )
        )
    }
    resolved = []
    for issue_id in issue_ids:
        row = existing.get(issue_id)
        if row is None:
            raise ValueError("qa_issue_not_found")
        if row.status != "OPEN":
            continue
        resolved.append(
            await resolve_qa_issue(
                db,
                report_case_id=report_case_id,
                issue_id=issue_id,
                status=status,
                resolution=resolution,
                actor_id=actor_id,
            )
        )
    return resolved
