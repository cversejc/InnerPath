"""Current human guidance extracted exclusively from the product frameworks."""
import json
from copy import deepcopy
from pathlib import Path


_ASSET = json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf-8"))


def framework_reasoning_guidance(skill_key: str) -> dict:
    guidance = _ASSET["skills"][skill_key]
    return deepcopy({key: guidance[key] for key in ("objective", "methodology")})


def framework_source(skill_key: str) -> dict:
    guidance = _ASSET["skills"][skill_key]
    return {"source": guidance["source"], "sections": deepcopy(guidance["sections"]),
            "sha256": _ASSET["sources"][guidance["source"]]["sha256"]}


def framework_reference(reference_key: str) -> dict:
    return deepcopy(_ASSET["references"][reference_key])
