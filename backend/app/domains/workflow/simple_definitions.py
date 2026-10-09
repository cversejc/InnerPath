"""Definitions for the two supported ``report.simple`` execution protocols.

The original simple workflow follows the shared report node catalog (currently
S1 -> S6) and keeps one immutable full-report-text version per node:

    S1 v1.0 -> S2 v2.0 -> ... -> S6 v6.0 (delivered)

That protocol remains frozen for existing cases.  New AI-assisted cases use a
separate definition with the same six business nodes, but each node is an
AI-generated and consultant-reviewed revision loop.  The protocol marker is
stored in both the published workflow definition and the case application
snapshot so a later code deployment cannot silently change how a case runs.
"""

from typing import Any

from .definitions import (
    SIMPLE_WORKFLOW_KEY,
    report_step_catalog,
    validate_workflow_definition,
)
from app.domains.skills.definitions import (
    FINAL_VALIDATOR_SKILL_KEY,
    FRAGMENT_AUTHORING_SKILL_KEY,
    S1_FOUNDATION_SKILL_KEY,
    S2_PSYCHOLOGY_SKILL_KEY,
    S3_INTEGRATION_SKILL_KEY,
    S4_MECHANISM_SKILL_KEY,
)

SIMPLE_INPUT_CONTRACT = "user_info+report_text"
SIMPLE_PROTOCOL_LEGACY = "legacy_manual"
SIMPLE_PROTOCOL_AI_ASSISTED = "ai_assisted"
SUPPORTED_SIMPLE_PROTOCOLS = (
    SIMPLE_PROTOCOL_LEGACY,
    SIMPLE_PROTOCOL_AI_ASSISTED,
)
SIMPLE_AI_PROTOCOL_VERSION = 1

SIMPLE_AI_STEP_PROFILES: dict[str, str] = {
    "S1": "foundation_analysis",
    "S2": "psychology_mapping",
    "S3": "integration",
    "S4": "mechanism_action",
    "S5": "report_body",
    "S6": "final_quality_gate",
}

# Decision 6: reuse the existing production skills instead of publishing new
# Simple-only skill keys.  Per-node adaptation happens through the revision
# contract and, where needed, per-node runtime instructions.
SIMPLE_AI_STEP_SKILL_KEYS: dict[str, str] = {
    "S1": S1_FOUNDATION_SKILL_KEY,
    "S2": S2_PSYCHOLOGY_SKILL_KEY,
    "S3": S3_INTEGRATION_SKILL_KEY,
    "S4": S4_MECHANISM_SKILL_KEY,
    "S5": FRAGMENT_AUTHORING_SKILL_KEY,
    "S6": FINAL_VALIDATOR_SKILL_KEY,
}


def _simplified_step(step: dict[str, Any], *, is_final: bool) -> dict[str, Any]:
    config = {
        "completion_policy": "MANUAL",
        "input_contract": SIMPLE_INPUT_CONTRACT,
        "output_version": step["sequence_no"],
    }
    if is_final:
        config["final_gate"] = True
    return {**step, "config": config}


def _ai_assisted_step(step: dict[str, Any], *, is_final: bool) -> dict[str, Any]:
    step_key = step["step_key"]
    config = {
        "completion_policy": "MANUAL",
        "execution_protocol": SIMPLE_PROTOCOL_AI_ASSISTED,
        "input_contract": "simple_ai_step_input_v1",
        "output_contract": "simple_ai_step_revision_v1",
        "generation_profile": SIMPLE_AI_STEP_PROFILES[step_key],
        "skill_key": SIMPLE_AI_STEP_SKILL_KEYS[step_key],
        "requires_human_approval": True,
        "allow_manual_edit": True,
        "auto_retry_limit": 2,
    }
    if is_final:
        config["final_gate"] = True
    return {**step, "executor": "HYBRID", "config": config}


_step_catalog = report_step_catalog()
SIMPLE_STEP_KEYS = tuple(step["step_key"] for step in _step_catalog)

SIMPLE_WORKFLOW_DEFINITION: dict[str, Any] = {
    "completion_policy": "MANUAL",
    "steps": [
        _simplified_step(step, is_final=index == len(_step_catalog) - 1)
        for index, step in enumerate(_step_catalog)
    ],
}

SIMPLE_AI_WORKFLOW_DEFINITION: dict[str, Any] = {
    "simple_protocol": SIMPLE_PROTOCOL_AI_ASSISTED,
    "protocol_version": SIMPLE_AI_PROTOCOL_VERSION,
    "completion_policy": "MANUAL",
    "steps": [
        _ai_assisted_step(step, is_final=index == len(_step_catalog) - 1)
        for index, step in enumerate(_step_catalog)
    ],
}


def simple_workflow_definition() -> dict[str, Any]:
    """Return the frozen legacy manual protocol.

    Do not add metadata to this definition.  The first published version is
    already used by existing cases, and keeping it byte-for-byte stable avoids
    creating a new legacy version merely because code added a feature flag.
    """
    return validate_workflow_definition(SIMPLE_WORKFLOW_DEFINITION)


def ai_assisted_simple_workflow_definition() -> dict[str, Any]:
    return validate_workflow_definition(SIMPLE_AI_WORKFLOW_DEFINITION)


def simple_protocol_from_definition(definition: dict[str, Any] | None) -> str:
    """Read the frozen protocol marker, treating old definitions as legacy."""
    value = (definition or {}).get("simple_protocol")
    return normalize_simple_protocol(value)


def normalize_simple_protocol(value: Any) -> str:
    """Resolve a requested protocol, defaulting unset values to legacy."""
    if value is None:
        return SIMPLE_PROTOCOL_LEGACY
    if isinstance(value, str) and not value.strip():
        return SIMPLE_PROTOCOL_LEGACY
    protocol = str(value).strip()
    if protocol not in SUPPORTED_SIMPLE_PROTOCOLS:
        raise ValueError("simple_protocol_unsupported")
    return protocol


def case_simple_protocol(report_case: Any) -> str:
    """Return the protocol frozen on a case, defaulting old cases to legacy."""
    snapshot = getattr(report_case, "application_snapshot", None)
    if snapshot is None and isinstance(report_case, dict):
        snapshot = report_case
    if not isinstance(snapshot, dict):
        return SIMPLE_PROTOCOL_LEGACY
    return normalize_simple_protocol(snapshot.get("simple_protocol"))


def ensure_legacy_simple_protocol(report_case: Any) -> None:
    """Reject legacy Simple commands when a case froze the AI protocol."""
    if case_simple_protocol(report_case) == SIMPLE_PROTOCOL_AI_ASSISTED:
        raise ValueError("simple_ai_protocol_required")


def simple_ai_step_config(step_key: str) -> dict[str, Any]:
    """Return the frozen AI profile config for one business step."""
    for step in SIMPLE_AI_WORKFLOW_DEFINITION["steps"]:
        if step["step_key"] == step_key:
            return dict(step["config"])
    raise ValueError("step_task_not_found")


def simple_ai_required_skill_keys(
    definition: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return the skill keys the AI-assisted definition binds, in stable order."""
    source = definition or SIMPLE_AI_WORKFLOW_DEFINITION
    keys = {
        (step.get("config") or {}).get("skill_key")
        for step in source.get("steps", [])
    }
    keys.discard(None)
    return tuple(sorted(key for key in keys if isinstance(key, str)))


def step_simple_step_config(step_task: Any) -> dict[str, Any]:
    """Return the frozen AI config of a case step, falling back to code."""
    snapshot = getattr(step_task, "config_snapshot", None)
    if isinstance(snapshot, dict) and snapshot.get("execution_protocol"):
        return dict(snapshot)
    return simple_ai_step_config(getattr(step_task, "step_key", ""))
