from copy import deepcopy
from typing import Any


DEFAULT_WORKFLOW_KEY = "report.production"

DEFAULT_WORKFLOW_DEFINITION: dict[str, Any] = {
    "completion_policy": "MANUAL",
    "steps": [
        {
            "step_key": "S1",
            "name": "命理基础结构",
            "sequence_no": 1,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
        {
            "step_key": "S2",
            "name": "心理映射",
            "sequence_no": 2,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
        {
            "step_key": "S3",
            "name": "命理、心理与哲学整合",
            "sequence_no": 3,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
        {
            "step_key": "S4",
            "name": "机制、卡点与行动",
            "sequence_no": 4,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
        {
            "step_key": "S5",
            "name": "报告撰写",
            "sequence_no": 5,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
        {
            "step_key": "S6",
            "name": "最终质量审核",
            "sequence_no": 6,
            "executor": "HUMAN",
            "required_capability": "consultant",
            "config": {"completion_policy": "MANUAL"},
        },
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
