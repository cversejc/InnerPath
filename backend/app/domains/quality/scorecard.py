"""Product's seven-dimensional rubric, independent from AI pass/fail prose."""
RUBRIC = {"fact_fidelity": 20, "personalization": 20, "psychological_logic": 15, "structure_coherence": 15, "reading_experience": 10, "action_value": 10, "uncertainty_safety": 10}
LABELS = {"fact_fidelity": "案例事实忠实度", "personalization": "个性化", "psychological_logic": "心理逻辑", "structure_coherence": "三章连贯性", "reading_experience": "阅读体验", "action_value": "行动价值", "uncertainty_safety": "不确定性与安全"}


def validate_scorecard(value, fragment_keys):
    if not isinstance(value, dict) or not isinstance(value.get("dimensions"), dict):
        raise ValueError("validator_scorecard_required")
    dimensions = value["dimensions"]
    if set(dimensions) != set(RUBRIC):
        raise ValueError("validator_scorecard_dimensions_invalid")
    total = 0
    for key, maximum in RUBRIC.items():
        item = dimensions[key]
        if not isinstance(item, dict):
            raise ValueError("validator_scorecard_invalid")
        score, reason, refs = item.get("score"), item.get("reason"), item.get("fragment_keys")
        if (not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= maximum
                or not isinstance(reason, str) or not reason.strip()
                or not isinstance(refs, list) or not refs or any(ref not in fragment_keys for ref in refs)):
            raise ValueError("validator_scorecard_invalid")
        item.update(max_score=maximum, label=LABELS[key])
        total += score
    value["total"] = round(total, 2)
    value["max_score"] = 100
    value["passes_threshold"] = total >= 80 and dimensions["fact_fidelity"]["score"] >= 16 and dimensions["uncertainty_safety"]["score"] >= 8
    return value
