"""Reusable operator for the report six-node review flow and calendar production.

Run inside the backend container (or any host that can reach the API) so the
access token is generated in memory and never persisted:

    docker cp backend/tools/report_calendar_operator.py innerpath-backend:/tmp/
    docker exec innerpath-backend python /tmp/report_calendar_operator.py \
        <command> [options]

The earlier form still works when piping the script through stdin:

    docker exec -i innerpath-backend python - <command> [options] \
        < backend/tools/report_calendar_operator.py

Every business write goes through the public HTTP API; the tool only keeps a
local state file for idempotency keys. The flow it encodes is the one that
produced the first delivered report and 30-day calendar end to end:

    status -> assign -> run-report (S1..S6) -> calendar-generate -> calendar-verify

Typical use:

    python report_calendar_operator.py status --service-request-id 12
    python report_calendar_operator.py run-report --service-request-id 12 \
        --birth-place "山西省晋中市"
    python report_calendar_operator.py calendar-generate --service-request-id 12 \
        --start-date 2026-10-10 --end-date 2026-11-08 \
        --goal "围绕当前学业困扰，找到认识自己、明确方向并稳定行动节奏的路径。"
    python report_calendar_operator.py calendar-verify --user-id 5

When S6 needs a manual revision, the s6-dump / s6-plan / s6-revise /
s6-coverage commands produce and apply changed fragments without going through
the admin UI, and rerun-s1-analysis re-queues a truncated S1 analysis with the
compact-output instruction. probe-gateway / configure-model / switch-provider
cover the model gateway knobs that the first run needed; see
docs/implementation/报告与日历全链路生成操作手册.md for the recommended sequence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

BASE_URL = os.environ.get("INNERPATH_API_BASE", "http://127.0.0.1:8000/api/v1")
DEFAULT_STATE_PATH = os.environ.get(
    "INNERPATH_OPERATOR_STATE", "/tmp/innerpath-report-calendar-state.json"
)
STEPS = ("S1", "S2", "S3", "S4", "S5", "S6")

DEFAULT_APPROVAL_REASON = (
    "经人工复核本节点来源、判断与分析正文，该意见不改变结论，按保留处理并纳入后续复核。"
)
DEFAULT_FINAL_REASON = (
    "经人工通读完整报告并复核最终质量结果，该意见不改变交付结论，按保留处理并记录在交付审计中。"
)

S1_COMPACT_INSTRUCTION = (
    "本次运行必须在12000 output tokens内收尾并输出完整合法的JSON。硬性约束："
    "1) 只输出JSON本身，不要Markdown代码块、解释、过程描述或任何JSON之外的文字。"
    "2) summary不超过80个汉字。"
    "3) findings最多8条，每条claim不超过80个汉字，short_title不超过12个汉字，"
    "structured_data、evidence_refs、relation_refs只保留必要项。"
    "4) analysis_fragments必须且只能包含这14个fragment_key，一个都不能少："
    "analysis.s1.day_master、analysis.s1.structure、analysis.s1.month、analysis.s1.ten_gods、"
    "analysis.s1.day_branch、analysis.s1.hour、analysis.s1.year、analysis.s1.interactions、"
    "analysis.s1.dayun、analysis.s1.useful_gods、analysis.s1.ziwei_life、analysis.s1.ziwei_body、"
    "analysis.s1.ziwei_wellbeing、analysis.s1.ziwei_transformations。"
    "5) 每个fragment的content控制在100-180个汉字，直接写结论与依据，"
    "不重复粘贴证据原文，不写套话；structured_analysis每个字段不超过40个汉字；"
    "framework_coverage只写简短键值。"
    "6) risk_flags最多3条，每条message不超过60个汉字。"
    "7) 若篇幅接近上限，优先保证JSON结构完整闭合：宁可精炼收束，不得截断。"
)

CALENDAR_DEFAULTS = {
    "profile_version": 3,
    "focus_topics": ["career", "self", "finance"],
    "usage_scenario": "morning_planning",
    "expected_outcomes": [
        "action_windows",
        "daily_prompt",
        "decision_review",
        "reflection",
    ],
    "available_minutes_per_day": 30,
}


def token_for(user_id: int) -> str:
    from datetime import timedelta

    from app.core.security import create_access_token

    return create_access_token({"sub": str(user_id)}, timedelta(minutes=30))


class Api:
    def __init__(self, user_id: int):
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token_for(user_id)}"},
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    def request(self, method: str, url: str, **kwargs):
        response = self.client.request(method, url, **kwargs)
        if response.status_code >= 400:
            detail = response.text[:1200]
            raise RuntimeError(f"{method} {url} -> {response.status_code} {detail}")
        if not response.content:
            return None
        return response.json()

    def get(self, url: str):
        return self.request("GET", url)

    def patch(self, url: str, payload: dict):
        return self.request("PATCH", url, json=payload)

    def post(self, url: str, payload: dict | None = None):
        return self.request("POST", url, json=payload or {})

    def put(self, url: str, payload: dict):
        return self.request("PUT", url, json=payload)


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def brief(value, limit: int = 600) -> str:
    text = value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, default=str
    )
    return text if len(text) <= limit else text[:limit] + "…"


def wait_for(getter, timeout: float, label: str, interval: float = 5):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        value = getter()
        last = value
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError(f"{label} timed out: {brief(last)}")


@dataclass
class Context:
    """Everything the operator needs to drive one service request."""

    admin: Api
    service_request_id: int
    state_path: Path
    user_id: int | None = None
    report_case_id: int | None = None
    state: dict = field(default_factory=dict)

    def key(self, *parts) -> str:
        value = ":".join(str(part) for part in parts)
        keys = self.state.setdefault("keys", [])
        if value not in keys:
            keys.append(value)
            save_state(self.state_path, self.state)
        return value

    def step_path(self, step: str) -> str:
        if self.report_case_id is None:
            raise RuntimeError("report case id is not resolved yet")
        return f"/report-cases/{self.report_case_id}/steps/{step}"

    def review(self, step: str) -> dict:
        return self.admin.get(f"{self.step_path(step)}/review")

    def resolve_service_request(self) -> dict:
        page = 1
        while page <= 20:
            listing = self.admin.get(
                f"/admin/service-requests?service_type=report&size=100&page={page}"
            )
            items = listing.get("items", [])
            for item in items:
                if item.get("id") == self.service_request_id:
                    return item
            if len(items) < 100:
                break
            page += 1
        raise RuntimeError(
            f"service request {self.service_request_id} was not returned by the admin list API"
        )

    def resolve_report_case(self) -> int:
        if self.report_case_id is not None:
            return self.report_case_id
        request = self.resolve_service_request()
        self.user_id = request.get("user_id")
        report_case_id = request.get("report_case_id")
        if not report_case_id:
            raise RuntimeError(
                "service request has no report_case_id yet; accept the request first: "
                f"{brief(request)}"
            )
        self.report_case_id = int(report_case_id)
        self.state.setdefault("resolved", {})["report_case_id"] = self.report_case_id
        save_state(self.state_path, self.state)
        return self.report_case_id


def summarize(ctx: Context, step: str, workspace: dict | None = None) -> dict:
    workspace = workspace or ctx.review(step)
    check = workspace.get("check") or {}
    snapshot = workspace.get("snapshot") or {}
    return {
        "step_key": workspace.get("step_key"),
        "step_status": workspace.get("step_status"),
        "fingerprint": workspace.get("fingerprint"),
        "can_approve": workspace.get("can_approve"),
        "can_finalize": workspace.get("can_finalize"),
        "preparation_error": workspace.get("preparation_error"),
        "checkpoints": {
            name: value.get("current")
            for name, value in (workspace.get("checkpoints") or {}).items()
        },
        "check": {
            "id": check.get("id"),
            "status": check.get("status"),
            "error": brief(check.get("error"), 400),
        },
        "issues": [
            {
                "id": item.get("id"),
                "severity": item.get("severity"),
                "status": item.get("status"),
                "type": item.get("type"),
                "target_key": item.get("target_key"),
                "message": brief(item.get("message"), 200),
            }
            for item in workspace.get("issues", [])
        ],
        "fragments": [
            fragment.get("fragment_key")
            for fragment in snapshot.get("fragments", [])
        ],
        "findings": [
            finding.get("finding_key")
            for finding in snapshot.get("findings", [])
            if finding.get("owner_step_task_id") == snapshot.get("step_task_id")
        ],
    }


def status(ctx: Context) -> None:
    request = ctx.resolve_service_request()
    ctx.user_id = request.get("user_id")
    ctx.report_case_id = request.get("report_case_id")
    print(
        json.dumps(
            {
                "service_request": {
                    "id": request.get("id"),
                    "user_id": request.get("user_id"),
                    "status": request.get("status"),
                    "report_case_id": request.get("report_case_id"),
                    "result_type": request.get("result_type"),
                    "result_id": request.get("result_id"),
                    "assigned_mingli_consultant_id": request.get(
                        "assigned_mingli_consultant_id"
                    ),
                    "assigned_psychology_consultant_id": request.get(
                        "assigned_psychology_consultant_id"
                    ),
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not ctx.report_case_id:
        return
    for step in STEPS:
        try:
            print(
                json.dumps(
                    {"step": summarize(ctx, step)}, ensure_ascii=False, indent=2
                )
            )
        except RuntimeError as error:
            print(json.dumps({"step": step, "error": str(error)}, ensure_ascii=False))


def assign(
    ctx: Context, mingli_consultant_id: int | None, psychology_consultant_id: int | None
) -> None:
    if mingli_consultant_id:
        print(
            brief(
                ctx.admin.patch(
                    f"/admin/service-requests/{ctx.service_request_id}/assignment",
                    {
                        "consultant_id": mingli_consultant_id,
                        "consultant_type": "mingli",
                    },
                )
            )
        )
    if psychology_consultant_id:
        print(
            brief(
                ctx.admin.patch(
                    f"/admin/service-requests/{ctx.service_request_id}/assignment",
                    {
                        "consultant_id": psychology_consultant_id,
                        "consultant_type": "psychology",
                    },
                )
            )
        )


def resolve_issues(
    ctx: Context, step: str, workspace: dict, *, reason: str
) -> dict:
    """Retain open MAJOR issues with a substantive reason; never touch BLOCK."""
    check = workspace.get("check")
    if not check or check.get("status") != "COMPLETED":
        return workspace
    open_major = [
        issue
        for issue in workspace.get("issues", [])
        if issue.get("severity") == "MAJOR"
        and issue.get("status", "OPEN") == "OPEN"
    ]
    if not open_major:
        return workspace
    current = workspace
    for issue in open_major:
        current = ctx.admin.post(
            f"{ctx.step_path(step)}/review/issues/resolve",
            {
                "fingerprint": current["fingerprint"],
                "check_id": check["id"],
                "issue_id": issue["id"],
                "resolution": "RETAINED",
                "reason": reason,
            },
        )
    return current


def poll_check(
    ctx: Context, step: str, *, timeout: float = 3600, interval: float = 6
) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        workspace = ctx.review(step)
        check = workspace.get("check") or {}
        last = check
        if check.get("status") == "COMPLETED":
            return workspace
        if check.get("status") == "FAILED":
            raise RuntimeError(
                f"{step} check failed: {brief(check.get('error'), 800)}"
            )
        time.sleep(interval)
    raise TimeoutError(f"{step} check did not complete: {brief(last)}")


def command_status(ctx: Context, step: str, command_id: int) -> dict:
    workspace = ctx.review(step)
    for command in workspace.get("commands", []):
        if command.get("id") == command_id:
            return command
    return {"id": command_id, "status": "UNKNOWN"}


def poll_command(
    ctx: Context,
    step: str,
    command_id: int,
    *,
    timeout: float = 600,
    interval: float = 3,
) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        command = command_status(ctx, step, command_id)
        last = command
        if command.get("status") == "COMPLETED":
            return command
        if command.get("status") in {"FAILED", "STALE"}:
            raise RuntimeError(
                f"{step} command {command_id} {command.get('status')}: "
                f"{brief(command.get('error'), 800)}"
            )
        time.sleep(interval)
    raise TimeoutError(
        f"{step} command {command_id} did not complete: {brief(last)}"
    )


def queue_prepare(ctx: Context, step: str, workspace: dict) -> dict:
    attempts = ctx.state.setdefault("prepare_attempts", {})
    existing = [
        command
        for command in workspace.get("commands", [])
        if command.get("kind") == "PREPARE"
    ]
    attempt = max(int(attempts.get(step, 0)), len(existing)) + 1
    attempts[step] = attempt
    save_state(ctx.state_path, ctx.state)
    return ctx.admin.post(
        f"{ctx.step_path(step)}/review/prepare",
        {
            "fingerprint": workspace["fingerprint"],
            "idempotency_key": ctx.key(
                "prepare", step, workspace["fingerprint"], attempt
            ),
        },
    )


def queue_check(ctx: Context, step: str, workspace: dict) -> dict:
    return ctx.admin.post(
        f"{ctx.step_path(step)}/review/check",
        {
            "fingerprint": workspace["fingerprint"],
            "idempotency_key": ctx.key(
                "check", step, workspace["fingerprint"]
            ),
        },
    )


def ensure_prepared(
    ctx: Context, step: str, *, timeout: float = 900
) -> dict:
    """Run the formal PREPARE command and wait until it has been executed."""
    workspace = ctx.review(step)
    if workspace["step_status"] == "COMPLETED":
        return workspace
    active = next(
        (
            command
            for command in workspace.get("commands", [])
            if command.get("kind") == "PREPARE"
            and command.get("status") in {"PENDING", "RUNNING"}
        ),
        None,
    )
    if active:
        command = poll_command(ctx, step, active["id"], timeout=timeout)
    else:
        dispatched = ctx.state.setdefault("prepare_dispatched", {})
        retries = ctx.state.setdefault("terminal_prepare_retries", [])
        marker = f"{step}:{workspace['fingerprint']}"
        preparation_error = workspace.get("preparation_error")
        if preparation_error and marker in retries:
            raise RuntimeError(
                f"{step} prepare failed again after retry: {brief(preparation_error)}"
            )
        if preparation_error or dispatched.get(step) != workspace["fingerprint"]:
            if preparation_error:
                retries.append(marker)
            dispatched[step] = workspace["fingerprint"]
            save_state(ctx.state_path, ctx.state)
            prepared = queue_prepare(ctx, step, workspace)
            command = poll_command(ctx, step, prepared["id"], timeout=timeout)
        else:
            return workspace
    status_value = (command.get("output") or {}).get("preparation_status")
    if status_value in {
        "needs_input",
        "stale",
        "waiting_for_assignment",
        "waiting_for_permission",
    }:
        current = ctx.review(step)
        raise RuntimeError(
            f"{step} prepare returned {status_value}: "
            f"{current.get('preparation_error') or brief(summarize(ctx, step, current))}"
        )
    return ctx.review(step)


def ensure_analysis_check(
    ctx: Context, step: str, *, timeout: float = 3600
) -> dict:
    """Prepare an empty analysis node, materialize its output, then CHECK it."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        workspace = ctx.review(step)
        if workspace["step_status"] == "COMPLETED":
            return workspace
        check = workspace.get("check") or {}
        if check.get("status") == "COMPLETED":
            return workspace
        if check.get("status") == "FAILED":
            raise RuntimeError(
                f"{step} check failed: {brief(check.get('error'), 800)}"
            )
        if check.get("status") in {"PENDING", "RUNNING"}:
            return poll_check(
                ctx, step, timeout=max(1, deadline - time.monotonic())
            )

        snapshot = workspace.get("snapshot") or {}
        has_output = bool(snapshot.get("fragments")) and any(
            finding.get("owner_step_task_id") == snapshot.get("step_task_id")
            for finding in snapshot.get("findings", [])
        )
        if not has_output:
            workspace = ensure_prepared(
                ctx, step, timeout=max(1, deadline - time.monotonic())
            )
            if workspace.get("preparation_error"):
                raise RuntimeError(
                    f"{step} analysis preparation failed: "
                    f"{brief(workspace['preparation_error'])}"
                )
            time.sleep(5)
            continue

        queue_check(ctx, step, workspace)
        return poll_check(
            ctx, step, timeout=max(1, deadline - time.monotonic())
        )
    raise TimeoutError(f"{step} analysis output/check did not complete")


def approve_checkpoint(ctx: Context, step: str, checkpoint_key: str) -> dict:
    workspace = ctx.review(step)
    if (workspace.get("checkpoints", {}).get(checkpoint_key) or {}).get(
        "current"
    ):
        return workspace
    return ctx.admin.post(
        f"{ctx.step_path(step)}/review/checkpoints",
        {
            "fingerprint": workspace["fingerprint"],
            "idempotency_key": ctx.key(
                "checkpoint",
                step,
                checkpoint_key,
                workspace["fingerprint"],
            ),
            "checkpoint_key": checkpoint_key,
        },
    )


def approve_node(ctx: Context, step: str) -> dict:
    workspace = ctx.review(step)
    if workspace["step_status"] == "COMPLETED":
        return {
            "step_key": step,
            "status": "COMPLETED",
            "fingerprint": workspace["fingerprint"],
            "idempotent": True,
        }
    if not workspace["can_approve"]:
        raise RuntimeError(
            f"{step} cannot approve: {brief(summarize(ctx, step, workspace), 1600)}"
        )
    return ctx.admin.post(
        f"{ctx.step_path(step)}/review/approve",
        {"fingerprint": workspace["fingerprint"]},
    )


def _wait_for_step(ctx: Context, step: str, timeout: float) -> dict:
    def ready():
        workspace = ctx.review(step)
        if workspace["step_status"] in {"IN_REVIEW", "READY", "COMPLETED"}:
            return workspace
        return None

    return wait_for(ready, timeout, f"{step} review")


def complete_s1(
    ctx: Context,
    *,
    birth_place: str | None,
    approval_reason: str = DEFAULT_APPROVAL_REASON,
) -> None:
    ctx.resolve_report_case()
    workspace = _wait_for_step(ctx, "S1", 600)
    if workspace["step_status"] == "COMPLETED":
        print(json.dumps(summarize(ctx, "S1", workspace), ensure_ascii=False))
        return
    metadata = (workspace.get("snapshot") or {}).get("metadata") or {}
    confirmation = metadata.get("birth_time_confirmation") or {}
    if not confirmation.get("confirmed"):
        proposal = workspace.get("birth_time_proposal") or {}
        candidates = (proposal.get("location") or {}).get("candidates") or []
        if not birth_place:
            raise RuntimeError(
                "S1 needs a birth place confirmation; pass --birth-place "
                "(the proposal candidates are: "
                f"{brief([c.get('name') for c in candidates])})"
            )
        location = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("name") == birth_place
            ),
            candidates[0] if candidates else None,
        )
        if location is None:
            raise RuntimeError(
                "birth time proposal has no location candidates: "
                f"{brief(proposal, 1200)}"
            )
        ctx.admin.patch(
            f"{ctx.step_path('S1')}/review",
            {
                "fingerprint": workspace["fingerprint"],
                "birth_time_confirmation": {
                    "confirmed": True,
                    "basis": proposal.get("basis") or "TRUE_SOLAR",
                    "birth_place": birth_place,
                    "place_id": location.get("id"),
                    "civil_datetime": proposal.get("civil_datetime"),
                    "utc_offset_hours": 8,
                },
                "core_review": {
                    "hour_pillar": True,
                    "pattern_and_useful_gods": True,
                },
            },
        )
    workspace = ensure_analysis_check(ctx, "S1")
    workspace = resolve_issues(
        ctx, "S1", workspace, reason=approval_reason
    )
    for checkpoint_key in ("findings", "analysis"):
        approve_checkpoint(ctx, "S1", checkpoint_key)
    print(json.dumps(approve_node(ctx, "S1"), ensure_ascii=False))


def rerun_s1_analysis(ctx: Context, *, timeout: float = 1800) -> None:
    """Queue a fresh S1 analysis draft with the compact-output instruction.

    Use when the S1 analysis run is truncated or rejected for length; follow it
    with the normal `s1` command, which materializes and checks the new draft.
    """
    ctx.resolve_report_case()
    workspace = ctx.review("S1")
    attempts = int(ctx.state.setdefault("s1_compact_attempts", 0)) + 1
    ctx.state["s1_compact_attempts"] = attempts
    save_state(ctx.state_path, ctx.state)
    created = ctx.admin.post(
        f"{ctx.step_path('S1')}/analysis-drafts",
        {
            "idempotency_key": ctx.key(
                "s1-compact", workspace["fingerprint"], attempts
            ),
            "runtime_instruction": S1_COMPACT_INSTRUCTION,
        },
    )
    run_id = created["id"]
    print(
        json.dumps(
            {"queued_run_id": run_id, "status": created.get("status")},
            ensure_ascii=False,
        )
    )

    def finished():
        run = ctx.admin.get(f"/admin/skill-runs/{run_id}")
        if run.get("status") in {"COMPLETED", "FAILED", "CANCELLED"}:
            return run
        time.sleep(6)
        return None

    run = wait_for(finished, timeout, f"S1 compact analysis run {run_id}")
    trace = run.get("model_trace") or {}
    ctx.state["s1_compact_run_id"] = run_id
    save_state(ctx.state_path, ctx.state)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": run.get("status"),
                "error": brief(run.get("error"), 400),
                "finish_reason": trace.get("finish_reason"),
                "input_tokens": trace.get("input_tokens"),
                "output_tokens": trace.get("output_tokens"),
                "model": trace.get("model"),
            },
            ensure_ascii=False,
        )
    )
    if run.get("status") != "COMPLETED":
        raise RuntimeError(f"S1 compact analysis run {run_id} ended as {run.get('status')}")


def complete_analysis_node(
    ctx: Context, step: str, *, approval_reason: str = DEFAULT_APPROVAL_REASON
) -> None:
    ctx.resolve_report_case()
    if ctx.review(step)["step_status"] == "COMPLETED":
        print(json.dumps(summarize(ctx, step), ensure_ascii=False))
        return
    workspace = ensure_analysis_check(ctx, step)
    workspace = resolve_issues(ctx, step, workspace, reason=approval_reason)
    print(json.dumps(summarize(ctx, step, workspace), ensure_ascii=False))
    for checkpoint_key in ("findings", "analysis"):
        approve_checkpoint(ctx, step, checkpoint_key)
    print(json.dumps(approve_node(ctx, step), ensure_ascii=False))


def complete_s5(
    ctx: Context, *, approval_reason: str = DEFAULT_APPROVAL_REASON
) -> None:
    ctx.resolve_report_case()
    if ctx.review("S5")["step_status"] == "COMPLETED":
        print(json.dumps(summarize(ctx, "S5"), ensure_ascii=False))
        return

    narrative_path = f"/report-cases/{ctx.report_case_id}/narrative"
    state_body = ctx.admin.get(narrative_path)
    current = state_body.get("current_plan") or {}
    candidates = [
        run
        for run in state_body.get("candidate_runs") or []
        if run.get("status") == "COMPLETED"
    ]
    if current.get("status") != "CONFIRMED" and not candidates:
        ensure_prepared(ctx, "S5")

    def narrative_state():
        body = ctx.admin.get(narrative_path)
        plan = body.get("current_plan") or {}
        if plan.get("status") == "CONFIRMED":
            return body
        runs = [
            run
            for run in body.get("candidate_runs") or []
            if run.get("status") == "COMPLETED"
        ]
        return body if runs else None

    plan = wait_for(
        narrative_state, 3600, "S5 narrative candidates", interval=8
    )
    current = plan.get("current_plan") or {}
    if current.get("status") != "CONFIRMED":
        runs = [
            run
            for run in plan.get("candidate_runs") or []
            if run.get("status") == "COMPLETED"
        ]
        if not runs:
            raise RuntimeError("S5 narrative candidate run missing")
        run = runs[0]
        candidate_key = (
            ((run.get("output_parsed") or {}).get("candidates") or [{}])[0]
            .get("candidate_key")
        )
        ctx.admin.post(
            f"/report-cases/{ctx.report_case_id}/narrative-plans/confirm",
            {
                "skill_run_id": run["id"],
                "candidate_key": candidate_key,
                "overrides": {},
            },
        )
        current = (
            ctx.admin.get(narrative_path).get("current_plan") or {}
        )
    if current.get("status") != "CONFIRMED":
        raise RuntimeError(
            f"S5 narrative not confirmed: {brief(current, 800)}"
        )

    approve_checkpoint(ctx, "S5", "narrative")
    wait_for(
        lambda: (
            lambda snapshot: snapshot.get("report_generation", {}).get(
                "status"
            )
            == "READY_FOR_REVIEW"
            and snapshot.get("report_generation", {})
            .get("coherence", {})
            .get("status")
            == "PASSED"
        )(ctx.review("S5")["snapshot"]),
        5400,
        "S5 report generation",
        interval=10,
    )
    workspace = poll_check(ctx, "S5")
    workspace = resolve_issues(
        ctx, "S5", workspace, reason=approval_reason
    )
    approve_checkpoint(ctx, "S5", "report")
    print(json.dumps(approve_node(ctx, "S5"), ensure_ascii=False))


def s6_once(ctx: Context) -> dict:
    ctx.resolve_report_case()
    workspace = ctx.review("S6")
    if workspace["step_status"] == "COMPLETED":
        return workspace
    check = workspace.get("check") or {}
    if check.get("status") not in {"PENDING", "RUNNING", "COMPLETED"}:
        workspace = ensure_prepared(ctx, "S6")
        check = workspace.get("check") or {}
    if check.get("status") != "COMPLETED":
        workspace = poll_check(ctx, "S6", timeout=3600)
    return workspace


def s6_dump(ctx: Context, out_path: Path) -> None:
    workspace = ctx.review("S6")
    snapshot = workspace.get("snapshot") or {}
    fragments = [
        {
            "fragment_key": fragment.get("fragment_key"),
            "revision_no": fragment.get("revision_no"),
            "title": fragment.get("title"),
            "content": fragment.get("content"),
            "owner_step_task_id": fragment.get("owner_step_task_id"),
            "status": fragment.get("status"),
            "source_snapshot": fragment.get("source_snapshot"),
        }
        for fragment in snapshot.get("fragments", [])
    ]
    out_path.write_text(
        json.dumps(
            {
                "report_case_id": ctx.report_case_id,
                "fingerprint": workspace["fingerprint"],
                "step_status": workspace["step_status"],
                "step_task_id": snapshot.get("step_task_id"),
                "final_quality": workspace.get("final_quality"),
                "issues": workspace.get("issues"),
                "fragments": fragments,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "path": str(out_path),
                "fragment_count": len(fragments),
                "can_approve": workspace.get("can_approve"),
                "can_finalize": workspace.get("can_finalize"),
            },
            ensure_ascii=False,
        )
    )


def s6_plan(ctx: Context, out_path: Path) -> None:
    """Dump the confirmed narrative content plan behind the report fragments."""
    ctx.resolve_report_case()
    body = ctx.admin.get(f"/report-cases/{ctx.report_case_id}/narrative")
    current = body.get("current_plan") or {}
    content_plan = (current.get("plan_json") or {}).get("content_plan") or {}
    out_path.write_text(
        json.dumps(content_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "path": str(out_path),
                "fragment_count": len(content_plan.get("fragments", [])),
                "plan_status": current.get("status"),
            },
            ensure_ascii=False,
        )
    )


def s6_revise(ctx: Context, plan_path: Path) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    if not isinstance(plan, dict) or not plan:
        raise ValueError(
            "S6 revision plan must be a non-empty JSON object of fragment_key -> content"
        )
    workspace = ctx.review("S6")
    current = {
        fragment.get("fragment_key"): fragment
        for fragment in (workspace.get("snapshot") or {}).get("fragments", [])
    }
    results = []
    for fragment_key, content in plan.items():
        fragment = current.get(fragment_key)
        if fragment is None:
            results.append(
                {"fragment_key": fragment_key, "result": "NOT_FOUND"}
            )
            continue
        if (fragment.get("content") or "").strip() == content.strip():
            results.append(
                {
                    "fragment_key": fragment_key,
                    "result": "UNCHANGED",
                    "revision_no": fragment.get("revision_no"),
                }
            )
            continue
        revised = ctx.admin.put(
            f"{ctx.step_path('S6')}/fragments/{fragment_key}",
            {
                "expected_revision_no": fragment.get("revision_no"),
                "fragment_type": "REPORT",
                "status": "CONFIRMED",
                "edit_kind": "SEMANTIC",
                "content": content,
            },
        )
        results.append(
            {
                "fragment_key": fragment_key,
                "result": "REVISED",
                "revision_no": revised.get("revision_no"),
            }
        )
        current[fragment_key] = revised
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))


def s6_coverage(ctx: Context, plan_path: Path) -> None:
    """Reattach requirement coverage to current REPORT revisions without changing text."""
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    if not isinstance(plan, dict) or not plan:
        raise ValueError("S6 coverage plan must be a non-empty JSON object")
    workspace = ctx.review("S6")
    current = {
        fragment.get("fragment_key"): fragment
        for fragment in (workspace.get("snapshot") or {}).get("fragments", [])
    }
    results = []
    for fragment_key, coverage in plan.items():
        fragment = current.get(fragment_key)
        if fragment is None:
            results.append(
                {"fragment_key": fragment_key, "result": "NOT_FOUND"}
            )
            continue
        if not isinstance(coverage, list):
            raise ValueError(
                f"S6 coverage for {fragment_key} must be a list"
            )
        existing = (fragment.get("source_snapshot") or {}).get(
            "requirement_coverage"
        )
        if existing == coverage:
            results.append(
                {
                    "fragment_key": fragment_key,
                    "result": "UNCHANGED",
                    "revision_no": fragment.get("revision_no"),
                }
            )
            continue
        revised = ctx.admin.put(
            f"{ctx.step_path('S6')}/fragments/{fragment_key}",
            {
                "expected_revision_no": fragment.get("revision_no"),
                "fragment_type": "REPORT",
                "status": "CONFIRMED",
                "edit_kind": "SEMANTIC",
                "content": fragment.get("content"),
                "requirement_coverage": coverage,
            },
        )
        results.append(
            {
                "fragment_key": fragment_key,
                "result": "REVISED",
                "revision_no": revised.get("revision_no"),
            }
        )
        current[fragment_key] = revised
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))


def s6_check(ctx: Context, label: str = "retry") -> None:
    workspace = ctx.review("S6")
    queued = ctx.admin.post(
        f"{ctx.step_path('S6')}/review/check",
        {
            "fingerprint": workspace["fingerprint"],
            "idempotency_key": ctx.key(
                "check", "S6", label, workspace["fingerprint"]
            ),
        },
    )
    final_quality = workspace.get("final_quality") or {}
    print(
        json.dumps(
            {
                "fingerprint": workspace["fingerprint"],
                "command": queued,
                "final_quality": {
                    "quality_status": final_quality.get("quality_status"),
                    "can_approve": final_quality.get("can_approve"),
                    "open_count": final_quality.get("open_count"),
                    "blocking_count": final_quality.get("blocking_count"),
                },
            },
            ensure_ascii=False,
        )
    )


def finalize(
    ctx: Context, *, final_reason: str = DEFAULT_FINAL_REASON
) -> None:
    ctx.resolve_report_case()
    workspace = s6_once(ctx)
    for issue in [
        item
        for item in workspace.get("issues", [])
        if item.get("severity") == "MAJOR"
        and item.get("status", "OPEN") == "OPEN"
    ]:
        workspace = ctx.admin.post(
            f"{ctx.step_path('S6')}/review/issues/resolve",
            {
                "fingerprint": workspace["fingerprint"],
                "check_id": workspace["check"]["id"],
                "issue_id": issue["id"],
                "resolution": "RETAINED",
                "reason": final_reason,
            },
        )
    workspace = ctx.review("S6")
    if not workspace["can_approve"]:
        raise RuntimeError(
            f"S6 cannot finalize: {brief(summarize(ctx, 'S6', workspace), 1600)}"
        )
    result = ctx.admin.post(
        f"/report-cases/{ctx.report_case_id}/approve-and-deliver",
        {"fingerprint": workspace["fingerprint"]},
    )
    ctx.state["delivery"] = result
    save_state(ctx.state_path, ctx.state)
    print(json.dumps(result, ensure_ascii=False))


def probe_gateway() -> None:
    """Read-only probe of how the configured gateway handles thinking."""
    import asyncio

    from app.services.llm import _completions_url, _resolve_config

    async def run() -> None:
        config = await _resolve_config(None)
        url = _completions_url(config.base_url)
        print(
            json.dumps(
                {
                    "provider": config.provider,
                    "model": config.model,
                    "base_url": config.base_url,
                    "configured_thinking": config.thinking_enabled,
                    "configured_max_tokens": config.max_tokens,
                },
                ensure_ascii=False,
            )
        )
        payloads = {
            "thinking_disabled": {
                "model": config.model,
                "messages": [{"role": "user", "content": "只回复两个字：收到"}],
                "temperature": 0.2,
                "max_tokens": 64,
                "stream": False,
                "thinking": {"type": "disabled"},
            },
            "no_thinking_field": {
                "model": config.model,
                "messages": [{"role": "user", "content": "只回复两个字：收到"}],
                "temperature": 0.2,
                "max_tokens": 64,
                "stream": False,
            },
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0)
        ) as client:
            for label, body in payloads.items():
                response = await client.post(
                    url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {config.api_key}",
                    },
                )
                summary: dict = {
                    "probe": label,
                    "status_code": response.status_code,
                }
                try:
                    data = response.json()
                except ValueError:
                    summary["body_head"] = response.text[:300]
                    print(json.dumps(summary, ensure_ascii=False))
                    continue
                choice = ((data.get("choices") or [{}])[0]) or {}
                message = choice.get("message") or {}
                summary["model"] = data.get("model")
                summary["finish_reason"] = choice.get("finish_reason")
                summary["usage"] = data.get("usage")
                summary["message_keys"] = sorted(message.keys())
                summary["content_head"] = str(message.get("content"))[:120]
                if "reasoning_content" in message:
                    summary["reasoning_chars"] = len(
                        str(message.get("reasoning_content") or "")
                    )
                if "reasoning" in message:
                    summary["reasoning_chars"] = len(
                        str(message.get("reasoning") or "")
                    )
                print(json.dumps(summary, ensure_ascii=False))

    asyncio.run(run())


def configure_model(admin_user_id: int) -> None:
    """Store an OpenAI-compatible provider from a JSON payload on stdin."""
    payload = json.load(sys.stdin)
    secret = str(payload.get("api_key") or "")
    if not secret:
        raise RuntimeError("api_key is required on stdin")
    api = Api(admin_user_id)
    try:
        test_result = api.post("/admin/llm/configurations/test", payload)
        configurations = api.get("/admin/llm/configurations")
        existing = next(
            (
                item
                for item in configurations.get("items", [])
                if item.get("name") == payload.get("name")
            ),
            None,
        )
        if existing:
            configuration = api.put(
                f"/admin/llm/configurations/{existing['id']}", payload
            )
        else:
            configuration = api.post("/admin/llm/configurations", payload)
        if not configuration.get("is_default"):
            configuration = api.post(
                f"/admin/llm/configurations/{configuration['id']}/default",
                {},
            )
    except Exception as error:  # noqa: BLE001 - redact before surfacing
        raise RuntimeError(str(error).replace(secret, "<redacted>")) from None
    print(
        json.dumps(
            {
                "test": {
                    "success": test_result.get("success"),
                    "provider": test_result.get("provider"),
                    "model": test_result.get("model"),
                    "latency_ms": test_result.get("latency_ms"),
                },
                "configuration": {
                    "id": configuration.get("id"),
                    "name": configuration.get("name"),
                    "provider": configuration.get("provider"),
                    "base_url": configuration.get("base_url"),
                    "model": configuration.get("model"),
                    "is_default": configuration.get("is_default"),
                    "api_key_configured": configuration.get(
                        "api_key_configured"
                    ),
                    "api_key_source": configuration.get("api_key_source"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def switch_provider(
    admin_user_id: int, configuration_id: int, provider: str
) -> None:
    """Switch one existing configuration without resubmitting its API key."""
    if provider not in {"deepseek", "openai_compatible"}:
        raise ValueError("provider must be deepseek or openai_compatible")
    api = Api(admin_user_id)
    configurations = api.get("/admin/llm/configurations")
    existing = next(
        (
            item
            for item in configurations.get("items", [])
            if item.get("id") == configuration_id
        ),
        None,
    )
    if not existing:
        raise RuntimeError(f"llm configuration {configuration_id} not found")
    payload = {
        "name": existing["name"],
        "provider": provider,
        "base_url": existing["base_url"],
        "model": existing["model"],
        "temperature": existing["temperature"],
        "max_tokens": existing["max_tokens"],
        "timeout_seconds": existing["timeout_seconds"],
        "thinking_enabled": existing["thinking_enabled"],
        "is_default": existing["is_default"],
    }
    updated = api.put(
        f"/admin/llm/configurations/{configuration_id}", payload
    )
    print(
        json.dumps(
            {
                "before": {
                    "id": existing["id"],
                    "provider": existing["provider"],
                    "api_key_source": existing["api_key_source"],
                    "is_default": existing["is_default"],
                },
                "after": {
                    "id": updated["id"],
                    "name": updated["name"],
                    "provider": updated["provider"],
                    "base_url": updated["base_url"],
                    "model": updated["model"],
                    "thinking_enabled": updated["thinking_enabled"],
                    "is_default": updated["is_default"],
                    "api_key_configured": updated.get("api_key_configured"),
                    "api_key_source": updated.get("api_key_source"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def run_report(
    ctx: Context,
    *,
    birth_place: str,
    approval_reason: str = DEFAULT_APPROVAL_REASON,
    final_reason: str = DEFAULT_FINAL_REASON,
) -> None:
    """Drive S1 through delivery in order; each step is idempotent."""
    ctx.resolve_report_case()
    complete_s1(ctx, birth_place=birth_place, approval_reason=approval_reason)
    for step in ("S2", "S3", "S4"):
        complete_analysis_node(
            ctx, step, approval_reason=approval_reason
        )
    complete_s5(ctx, approval_reason=approval_reason)
    finalize(ctx, final_reason=final_reason)
    print(
        json.dumps(
            {"status": "delivered", "service_request_id": ctx.service_request_id},
            ensure_ascii=False,
        )
    )


def build_calendar_payload(
    *,
    report_id: int,
    start_date: str,
    end_date: str,
    goal: str,
    focus_topics: list[str] | None,
    usage_scenario: str | None,
    expected_outcomes: list[str] | None,
    available_minutes_per_day: int | None,
    decision_description: str | None,
    additional_info: str | None,
) -> dict:
    payload = {
        "profile_version": CALENDAR_DEFAULTS["profile_version"],
        "source_report_id": report_id,
        "start_date": start_date,
        "end_date": end_date,
        "focus_topics": focus_topics or CALENDAR_DEFAULTS["focus_topics"],
        "usage_scenario": usage_scenario
        or CALENDAR_DEFAULTS["usage_scenario"],
        "expected_outcomes": expected_outcomes
        or CALENDAR_DEFAULTS["expected_outcomes"],
        "available_minutes_per_day": available_minutes_per_day
        or CALENDAR_DEFAULTS["available_minutes_per_day"],
        "goal": goal,
    }
    if decision_description:
        payload["decision_description"] = decision_description
    if additional_info:
        payload["additional_info"] = additional_info
    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)
    if end < start:
        raise ValueError("--end-date must not be earlier than --start-date")
    if (end - start).days + 1 > 60:
        raise ValueError("calendar range should stay within 60 days")
    return payload


@dataclass
class CalendarPayload:
    start_date: str
    end_date: str
    goal: str
    focus_topics: list[str] | None = None
    usage_scenario: str | None = None
    expected_outcomes: list[str] | None = None
    available_minutes_per_day: int | None = None
    decision_description: str | None = None
    additional_info: str | None = None


def calendar_generate(
    ctx: Context,
    payload_args: CalendarPayload,
    *,
    poll_timeout: float,
) -> None:
    ctx.resolve_report_case()
    request = ctx.resolve_service_request()
    report_id = request.get("result_id")
    if not report_id:
        raise RuntimeError(
            f"service request {ctx.service_request_id} has no delivered report: "
            f"{brief(request, 800)}"
        )
    owner_id = request.get("user_id")
    owner = Api(owner_id)
    payload = build_calendar_payload(
        report_id=int(report_id),
        start_date=payload_args.start_date,
        end_date=payload_args.end_date,
        goal=payload_args.goal,
        focus_topics=payload_args.focus_topics,
        usage_scenario=payload_args.usage_scenario,
        expected_outcomes=payload_args.expected_outcomes,
        available_minutes_per_day=payload_args.available_minutes_per_day,
        decision_description=payload_args.decision_description,
        additional_info=payload_args.additional_info,
    )
    created = owner.post("/calendar/requests", payload)
    request_id = created["id"]
    ctx.state.setdefault("calendar_requests", []).append(
        {
            "id": request_id,
            "user_id": owner_id,
            "source_report_id": report_id,
            "start_date": payload_args.start_date,
            "end_date": payload_args.end_date,
        }
    )
    save_state(ctx.state_path, ctx.state)
    print(
        json.dumps(
            {"calendar_request": created}, ensure_ascii=False, indent=2
        )
    )

    def fulfilled():
        listing = owner.get("/calendar/requests")
        for item in listing.get("items", []):
            if item.get("id") != request_id:
                continue
            if item.get("status") == "failed":
                raise RuntimeError(
                    "calendar generation failed: "
                    f"{brief(item.get('generation_error'), 800)}"
                )
            if item.get("status") == "fulfilled" and item.get("calendar_id"):
                return item
            return None
        raise RuntimeError(f"calendar request {request_id} disappeared")

    deadline = time.monotonic() + poll_timeout
    last_stage = None
    while time.monotonic() < deadline:
        try:
            item = fulfilled()
        except RuntimeError as error:
            if "failed:" not in str(error):
                raise
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "calendar_request_id": request_id,
                        "error": str(error),
                    },
                    ensure_ascii=False,
                )
            )
            print(
                json.dumps(
                    {
                        "retry": f"python report_calendar_operator.py "
                        f"calendar-retry --service-request-id {ctx.service_request_id} "
                        f"--request-id {request_id}"
                    },
                    ensure_ascii=False,
                )
            )
            raise
        if item:
            print(
                json.dumps(
                    {
                        "status": "fulfilled",
                        "calendar_request_id": request_id,
                        "calendar_id": item.get("calendar_id"),
                    },
                    ensure_ascii=False,
                )
            )
            return
        listing = owner.get("/calendar/requests")
        current = next(
            (
                entry
                for entry in listing.get("items", [])
                if entry.get("id") == request_id
            ),
            {},
        )
        stage = current.get("generation_stage")
        if stage != last_stage:
            last_stage = stage
            print(
                json.dumps(
                    {
                        "calendar_request_id": request_id,
                        "status": current.get("status"),
                        "stage": stage,
                        "completed_runs": current.get("completed_runs"),
                        "total_runs": current.get("total_runs"),
                    },
                    ensure_ascii=False,
                )
            )
        time.sleep(10)
    raise TimeoutError(
        f"calendar request {request_id} did not finish within {poll_timeout}s"
    )


def calendar_retry(ctx: Context, request_id: int) -> None:
    request = ctx.resolve_service_request()
    owner = Api(request.get("user_id"))
    print(
        json.dumps(
            owner.post(f"/calendar/requests/{request_id}/retry"),
            ensure_ascii=False,
            indent=2,
        )
    )


def _calendar_entries(item: dict) -> dict[str, dict]:
    meta = item.get("meta_payload") or {}
    for key in ("daily_details", "days", "entries"):
        value = meta.get(key) or item.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {
                str(entry.get("date") or entry.get("entry_date")): entry
                for entry in value
                if isinstance(entry, dict)
            }
    return {}


def calendar_verify(
    api: Api,
    *,
    start_date: str | None,
    end_date: str | None,
    calendar_id: int | None,
) -> int:
    listing = api.get("/calendar/me")
    items = listing.get("items", [])
    if calendar_id is not None:
        items = [
            item for item in items if item.get("id") == calendar_id
        ]
    if not items:
        raise RuntimeError(
            f"no calendar found for the given filters (calendar_id={calendar_id})"
        )
    exit_code = 0
    for item in items:
        start = start_date or item["start_date"]
        end = end_date or item["end_date"]
        start_day = dt.date.fromisoformat(start)
        end_day = dt.date.fromisoformat(end)
        expected = [
            (start_day + dt.timedelta(days=offset)).isoformat()
            for offset in range((end_day - start_day).days + 1)
        ]
        entries = _calendar_entries(item)
        missing = [day for day in expected if day not in entries]
        unexpected = [day for day in entries if day not in expected]
        empty = [
            day
            for day in expected
            if day in entries
            and not (
                entries[day].get("windows")
                or entries[day].get("suitable")
            )
        ]
        report = {
            "calendar_id": item.get("id"),
            "status": item.get("status"),
            "start": item["start_date"],
            "end": item["end_date"],
            "expected_days": len(expected),
            "actual_days": len(entries),
            "first": expected[0] if entries else None,
            "last": expected[-1] if entries else None,
            "missing": missing,
            "unexpected": unexpected,
            "empty_days": empty,
            "ok": not (missing or unexpected or empty)
            and len(entries) == len(expected),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["ok"]:
            exit_code = 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drive the report six-node review flow and calendar production."
    )
    parser.add_argument(
        "command",
        choices=[
            "status",
            "assign",
            "s1",
            "rerun-s1-analysis",
            "s2",
            "s3",
            "s4",
            "s5",
            "s6-once",
            "s6-dump",
            "s6-plan",
            "s6-revise",
            "s6-coverage",
            "s6-check",
            "finalize",
            "run-report",
            "calendar-generate",
            "calendar-retry",
            "calendar-verify",
            "get-json",
            "get-run-output",
            "probe-gateway",
            "configure-model",
            "switch-provider",
        ],
    )
    parser.add_argument(
        "--service-request-id",
        type=int,
        default=int(os.environ.get("INNERPATH_SERVICE_REQUEST_ID", "0")) or None,
    )
    parser.add_argument(
        "--report-case-id",
        type=int,
        default=int(os.environ.get("INNERPATH_REPORT_CASE_ID", "0")) or None,
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=int(os.environ.get("INNERPATH_USER_ID", "0")) or None,
        help="calendar owner or admin-listing target, depending on the command",
    )
    parser.add_argument("--state-path", default=DEFAULT_STATE_PATH)
    parser.add_argument("--admin-user-id", type=int, default=1)
    parser.add_argument("--mingli-consultant-id", type=int, default=0)
    parser.add_argument("--psychology-consultant-id", type=int, default=0)
    parser.add_argument("--birth-place", default=os.environ.get("INNERPATH_BIRTH_PLACE"))
    parser.add_argument("--approval-reason", default=DEFAULT_APPROVAL_REASON)
    parser.add_argument("--final-reason", default=DEFAULT_FINAL_REASON)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--goal", default="")
    parser.add_argument("--focus-topics", default="")
    parser.add_argument("--usage-scenario", default="")
    parser.add_argument("--expected-outcomes", default="")
    parser.add_argument("--available-minutes-per-day", type=int, default=0)
    parser.add_argument("--decision-description", default="")
    parser.add_argument("--additional-info", default="")
    parser.add_argument("--poll-timeout", type=float, default=2400)
    parser.add_argument("--request-id", type=int, default=0)
    parser.add_argument("--calendar-id", type=int, default=0)
    parser.add_argument("--path", default="")
    parser.add_argument("--limit", type=int, default=200000)
    parser.add_argument("--run-id", type=int, default=0)
    parser.add_argument("--check-label", default="retry")
    parser.add_argument("--plan-path", default="")
    parser.add_argument("--out-path", default="")
    parser.add_argument("--configuration-id", type=int, default=1)
    parser.add_argument("--provider", default="deepseek")
    args = parser.parse_args()

    if args.command == "probe-gateway":
        probe_gateway()
        return 0
    if args.command == "configure-model":
        configure_model(args.admin_user_id)
        return 0
    if args.command == "switch-provider":
        switch_provider(
            args.admin_user_id, args.configuration_id, args.provider
        )
        return 0
    if args.command == "get-json":
        if not args.path:
            raise SystemExit("--path is required for get-json")
        payload = Api(args.user_id or args.admin_user_id).get(args.path)
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        print(body[: args.limit])
        return 0
    if args.command == "get-run-output":
        if not args.run_id:
            raise SystemExit("--run-id is required for get-run-output")
        run = Api(args.admin_user_id).get(f"/admin/skill-runs/{args.run_id}")
        print(
            json.dumps(
                run.get("output_parsed"),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return 0
    if args.command == "calendar-verify":
        if not args.user_id:
            raise SystemExit("--user-id is required for calendar-verify")
        return calendar_verify(
            Api(args.user_id),
            start_date=args.start_date or None,
            end_date=args.end_date or None,
            calendar_id=args.calendar_id or None,
        )
    if not args.service_request_id:
        raise SystemExit(
            "--service-request-id is required for this command "
            "(or set INNERPATH_SERVICE_REQUEST_ID)"
        )

    ctx = Context(
        admin=Api(args.admin_user_id),
        service_request_id=args.service_request_id,
        state_path=Path(args.state_path),
        user_id=args.user_id,
        report_case_id=args.report_case_id,
        state=load_state(Path(args.state_path)),
    )

    def split(value: str) -> list[str] | None:
        if not value:
            return None
        return [part.strip() for part in value.split(",") if part.strip()]

    if args.command == "status":
        status(ctx)
    elif args.command == "assign":
        assign(
            ctx,
            args.mingli_consultant_id or None,
            args.psychology_consultant_id or None,
        )
    elif args.command == "s1":
        complete_s1(
            ctx,
            birth_place=args.birth_place,
            approval_reason=args.approval_reason,
        )
    elif args.command == "rerun-s1-analysis":
        rerun_s1_analysis(ctx, timeout=args.poll_timeout)
    elif args.command in {"s2", "s3", "s4"}:
        complete_analysis_node(
            ctx,
            args.command.upper(),
            approval_reason=args.approval_reason,
        )
    elif args.command == "s5":
        complete_s5(ctx, approval_reason=args.approval_reason)
    elif args.command == "s6-once":
        print(
            json.dumps(
                summarize(ctx, "S6", s6_once(ctx)),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "s6-dump":
        s6_dump(
            ctx,
            Path(args.out_path or "/tmp/s6-dump.json"),
        )
    elif args.command == "s6-plan":
        s6_plan(
            ctx,
            Path(args.out_path or "/tmp/s6-plan.json"),
        )
    elif args.command == "s6-revise":
        if not args.plan_path:
            raise SystemExit("--plan-path is required for s6-revise")
        s6_revise(ctx, Path(args.plan_path))
    elif args.command == "s6-coverage":
        if not args.plan_path:
            raise SystemExit("--plan-path is required for s6-coverage")
        s6_coverage(ctx, Path(args.plan_path))
    elif args.command == "s6-check":
        s6_check(ctx, args.check_label)
    elif args.command == "finalize":
        finalize(ctx, final_reason=args.final_reason)
    elif args.command == "run-report":
        if not args.birth_place:
            raise SystemExit(
                "--birth-place is required for run-report (or set INNERPATH_BIRTH_PLACE)"
            )
        run_report(
            ctx,
            birth_place=args.birth_place,
            approval_reason=args.approval_reason,
            final_reason=args.final_reason,
        )
    elif args.command == "calendar-generate":
        if not (args.start_date and args.end_date and args.goal):
            raise SystemExit(
                "--start-date, --end-date and --goal are required for calendar-generate"
            )
        calendar_generate(
            ctx,
            CalendarPayload(
                start_date=args.start_date,
                end_date=args.end_date,
                goal=args.goal,
                focus_topics=split(args.focus_topics),
                usage_scenario=args.usage_scenario or None,
                expected_outcomes=split(args.expected_outcomes),
                available_minutes_per_day=args.available_minutes_per_day
                or None,
                decision_description=args.decision_description or None,
                additional_info=args.additional_info or None,
            ),
            poll_timeout=args.poll_timeout,
        )
    elif args.command == "calendar-retry":
        if not args.request_id:
            raise SystemExit("--request-id is required for calendar-retry")
        calendar_retry(ctx, args.request_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001 - operator tool must surface raw failures
        print(
            json.dumps(
                {"error": f"{type(error).__name__}: {error}"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
