from copy import deepcopy
from typing import Any


# Built-in standard workflow. New applications no longer choose it, but it is
# retained for callers that request it explicitly.
DEFAULT_WORKFLOW_KEY = "report.production"
SIMPLE_WORKFLOW_KEY = "report.simple"
SUPPORTED_WORKFLOW_KEYS = (DEFAULT_WORKFLOW_KEY, SIMPLE_WORKFLOW_KEY)

# Workflow a new application receives when the caller names none: applications
# only describe the problem, and staff work them through the simplified flow.
DEFAULT_APPLICATION_WORKFLOW_KEY = SIMPLE_WORKFLOW_KEY

# The node catalog is the one part shared by every report workflow: the
# production workflow and any simplified variant must expose the same node
# keys, names and order. What differs per workflow is only the per-node
# contract stored in ``config``.
REPORT_WORKFLOW_STEP_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "step_key": "S1",
        "name": "命理基础结构",
        "sequence_no": 1,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
    {
        "step_key": "S2",
        "name": "心理映射",
        "sequence_no": 2,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
    {
        "step_key": "S3",
        "name": "命理、心理与哲学整合",
        "sequence_no": 3,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
    {
        "step_key": "S4",
        "name": "机制、卡点与行动",
        "sequence_no": 4,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
    {
        "step_key": "S5",
        "name": "报告撰写",
        "sequence_no": 5,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
    {
        "step_key": "S6",
        "name": "最终质量审核",
        "sequence_no": 6,
        "executor": "HUMAN",
        "required_capability": "consultant",
    },
)


def report_step_catalog() -> list[dict[str, Any]]:
    """Return a detached copy so callers can vary per-workflow contracts."""
    return deepcopy(list(REPORT_WORKFLOW_STEP_CATALOG))


DEFAULT_WORKFLOW_DEFINITION: dict[str, Any] = {
    "completion_policy": "MANUAL",
    "steps": [
        {**step, "config": {"completion_policy": "MANUAL"}}
        for step in report_step_catalog()
    ],
}


def validate_workflow_definition(definition: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(definition, dict):
        raise ValueError("workflow_definition_invalid")
    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("workflow_steps_required")

    normalized_steps = []
    seen_keys: set[str] = set()
    seen_sequences: set[int] = set()
    for raw_step in steps:
        if not isinstance(raw_step, dict):
            raise ValueError("workflow_step_invalid")
        step = deepcopy(raw_step)
        key = str(step.get("step_key") or "").strip()
        name = str(step.get("name") or "").strip()
        executor = str(step.get("executor") or "").upper()
        sequence_no = step.get("sequence_no")
        if not key or not name or executor not in {"HUMAN", "AI", "HYBRID"}:
            raise ValueError("workflow_step_invalid")
        if not isinstance(sequence_no, int) or sequence_no < 1:
            raise ValueError("workflow_step_sequence_invalid")
        if key in seen_keys or sequence_no in seen_sequences:
            raise ValueError("workflow_step_duplicate")
        if not isinstance(step.get("config", {}), dict):
            raise ValueError("workflow_step_config_invalid")
        seen_keys.add(key)
        seen_sequences.add(sequence_no)
        step.update(
            step_key=key,
            name=name,
            executor=executor,
            required_capability=step.get("required_capability"),
            config=step.get("config", {}),
        )
        normalized_steps.append(step)

    if seen_sequences != set(range(1, len(normalized_steps) + 1)):
        raise ValueError("workflow_step_sequence_invalid")
    if definition.get("completion_policy", "MANUAL") != "MANUAL":
        raise ValueError("workflow_completion_policy_unsupported")

    return {
        **deepcopy(definition),
        "completion_policy": "MANUAL",
        "steps": sorted(normalized_steps, key=lambda item: item["sequence_no"]),
    }


def default_workflow_definition() -> dict[str, Any]:
    return validate_workflow_definition(DEFAULT_WORKFLOW_DEFINITION)


def normalize_workflow_key(value: Any) -> str:
    """Resolve a requested workflow key to a supported workflow.

    A blank key means the caller did not choose, so the application receives
    ``DEFAULT_APPLICATION_WORKFLOW_KEY``.  Legacy cases without a stored key
    keep using the production workflow through ``case_workflow_key``.
    """
    key = str(value or "").strip()
    if not key:
        return DEFAULT_APPLICATION_WORKFLOW_KEY
    if key not in SUPPORTED_WORKFLOW_KEYS:
        raise ValueError("workflow_key_unsupported")
    return key


def case_workflow_key(report_case: Any) -> str:
    """Read the workflow key frozen on a case, defaulting for legacy cases.

    Cases created before multiple workflows existed, or created directly by
    background jobs, have no stored key.  They always belong to the production
    report workflow, so the fallback is never treated as missing data.
    """
    snapshot = getattr(report_case, "application_snapshot", None)
    if snapshot is None and isinstance(report_case, dict):
        snapshot = report_case
    if not isinstance(snapshot, dict):
        return DEFAULT_WORKFLOW_KEY
    key = str(snapshot.get("workflow_key") or "").strip()
    return key or DEFAULT_WORKFLOW_KEY
