import pytest
from app.domains.quality.scorecard import RUBRIC, validate_scorecard


def card():
    return {"dimensions": {key: {"score": maximum, "reason": "核对对应章节", "fragment_keys": ["report.identity.1"]} for key, maximum in RUBRIC.items()}}


def test_scores_are_computed_and_safety_is_a_separate_gate():
    value = card()
    value["total"] = 1
    assert validate_scorecard(value, {"report.identity.1"})["total"] == 100
    value["dimensions"]["uncertainty_safety"]["score"] = 7
    assert not validate_scorecard(value, {"report.identity.1"})["passes_threshold"]


def test_scorecard_requires_all_dimensions_and_real_fragment_references():
    with pytest.raises(ValueError, match="scorecard_required"):
        validate_scorecard(None, set())
    value = card()
    value["dimensions"]["fact_fidelity"]["fragment_keys"] = ["invented"]
    with pytest.raises(ValueError, match="scorecard_invalid"):
        validate_scorecard(value, {"report.identity.1"})
