"""Offline regression dataset loading and deterministic output scoring."""

import hashlib
import json
from pathlib import Path
from typing import Any


_DATASET_PATH = Path(__file__).with_name("regression_cases.json")


def load_regression_dataset() -> dict[str, Any]:
    with _DATASET_PATH.open(encoding="utf-8") as source:
        dataset = json.load(source)
    if not isinstance(dataset, dict) or not isinstance(dataset.get("cases"), list):
        raise ValueError("skill_regression_dataset_invalid")
    calendar = json.loads(_DATASET_PATH.with_name("calendar_regression_cases.json").read_text(encoding="utf-8"))
    dataset["cases"].extend(calendar["cases"])
    dataset["version"] += "+" + calendar["version"]
    return dataset


def regression_cases(*, skill_key: str | None = None) -> list[dict[str, Any]]:
    cases = load_regression_dataset()["cases"]
    return [
        case
        for case in cases
        if skill_key is None or case.get("skill_key") == skill_key
    ]


def select_regression_cases(
    *, skill_key: str, case_keys: list[str] | None = None
) -> list[dict[str, Any]]:
    available = regression_cases(skill_key=skill_key)
    by_key = {case["case_key"]: case for case in available}
    requested = list(dict.fromkeys(case_keys or by_key.keys()))
    if not requested:
        raise ValueError("skill_regression_cases_missing")
    unknown = [key for key in requested if key not in by_key]
    if unknown:
        raise ValueError("skill_regression_case_not_found")
    return [by_key[key] for key in requested]


def specification_digest(specification: dict[str, Any]) -> str:
    encoded = json.dumps(
        specification, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_regression_output(
    output: dict[str, Any], expectation: dict[str, Any]
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, *, expected: Any = None, actual: Any = None):
        checks.append(
            {"name": name, "passed": bool(passed), "expected": expected, "actual": actual}
        )

    record("output_is_object", isinstance(output, dict) and bool(output))

    for field in expectation.get("required_fields", []):
        record(
            f"required:{field}",
            field in output,
            expected=True,
            actual=field in output,
        )

    for item in expectation.get("path_equals", []):
        actual = _path_value(output, item.get("path", []))
        record(
            f"path_equals:{'.'.join(map(str, item.get('path', [])))}",
            actual is not _MISSING and actual == item.get("value"),
            expected=item.get("value"),
            actual=None if actual is _MISSING else actual,
        )

    for item in expectation.get("minimum_array_length", []):
        actual = _path_value(output, item.get("path", []))
        length = len(actual) if isinstance(actual, list) else None
        minimum = item.get("value")
        record(
            f"minimum_array_length:{'.'.join(map(str, item.get('path', [])))}",
            length is not None and length >= minimum,
            expected=minimum,
            actual=length,
        )

    for path in expectation.get("nonempty_paths", []):
        actual = _path_value(output, path)
        record(f"nonempty:{'.'.join(map(str, path))}", isinstance(actual, str) and bool(actual.strip()),
               expected="nonempty string", actual=None if actual is _MISSING else actual)

    allowed_refs = expectation.get("allowed_finding_refs")
    if allowed_refs is not None:
        actual_refs = sorted(_finding_references(output))
        unexpected = sorted(set(actual_refs) - set(allowed_refs))
        record(
            "allowed_finding_refs",
            not unexpected,
            expected=sorted(set(allowed_refs)),
            actual=actual_refs,
        )

    score = sum(check["passed"] for check in checks) / max(len(checks), 1)
    minimum_score = expectation.get("minimum_score", 1.0)
    return {
        "score": round(score, 4),
        "minimum_score": minimum_score,
        "passed": all(check["passed"] for check in checks) and score >= minimum_score,
        "checks": checks,
    }


_MISSING = object()


def _path_value(value: Any, path: list[Any]) -> Any:
    current = value
    for part in path:
        if isinstance(current, dict) and isinstance(part, str) and part in current:
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return _MISSING
    return current


def _finding_references(value: Any, *, key: str | None = None) -> set[str]:
    references: set[str] = set()
    reference_fields = {
        "finding_refs",
        "supporting_findings",
        "deemphasized_findings",
        "used_findings",
        "source_refs",
    }
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key in reference_fields and isinstance(child, list):
                references.update(item for item in child if isinstance(item, str))
            else:
                references.update(_finding_references(child, key=child_key))
    elif isinstance(value, list):
        for item in value:
            references.update(_finding_references(item, key=key))
    return references
