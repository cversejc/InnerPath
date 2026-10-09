"""Definition of the simplified full-report-text workflow.

The simplified workflow follows the same node catalog as the production
workflow (currently S1 -> S6). The only difference is the per-node contract:
every node consumes the user application plus the current full report text and
returns the next immutable version of that text.

    S1  v1.0  ->  S2  v2.0  ->  ...  ->  S6  v6.0 (delivered)

Version numbers, round numbers and the final flag are derived by the server
from ``config_snapshot``; clients only send the report text.
"""

from typing import Any

from .definitions import (
    SIMPLE_WORKFLOW_KEY,
    report_step_catalog,
    validate_workflow_definition,
)

SIMPLE_INPUT_CONTRACT = "user_info+report_text"


def _simplified_step(step: dict[str, Any], *, is_final: bool) -> dict[str, Any]:
    config = {
        "completion_policy": "MANUAL",
        "input_contract": SIMPLE_INPUT_CONTRACT,
        "output_version": step["sequence_no"],
    }
    if is_final:
        config["final_gate"] = True
    return {**step, "config": config}


_step_catalog = report_step_catalog()
SIMPLE_STEP_KEYS = tuple(step["step_key"] for step in _step_catalog)

SIMPLE_WORKFLOW_DEFINITION: dict[str, Any] = {
    "completion_policy": "MANUAL",
    "steps": [
        _simplified_step(step, is_final=index == len(_step_catalog) - 1)
        for index, step in enumerate(_step_catalog)
    ],
}


def simple_workflow_definition() -> dict[str, Any]:
    return validate_workflow_definition(SIMPLE_WORKFLOW_DEFINITION)
