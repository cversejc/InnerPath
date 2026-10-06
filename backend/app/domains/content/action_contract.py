"""Validate confirmed action shape and its actual Block ownership."""


def validate_growth_experiments(findings, upstream_keys=(), *, require_actions=True, check_count=True):
    upstream = [item for item in upstream_keys if isinstance(item, dict)]
    blocks = {item["finding_key"] for item in [*findings, *upstream]
              if item.get("semantic_role", "").upper() == "BLOCK"}
    actions = [item for item in findings if item.get("semantic_role", "").upper() == "ACTION"]
    if check_count and (actions or require_actions) and not 3 <= len(actions) <= 5:
        raise ValueError("report_analysis_experiment_count_invalid")
    for action in actions:
        data = action.get("structured_data") or {}
        refs, steps, duration = data.get("block_refs"), data.get("steps"), data.get("duration_minutes")
        if (not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or ref not in blocks for ref in refs)
                or not isinstance(steps, list) or not steps or any(not isinstance(s, str) or not s.strip() for s in steps)
                or not isinstance(data.get("frequency"), str)
                or data["frequency"] not in {"daily", "weekly", "monthly", "quarterly"}
                or not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 60
                or any(not isinstance(data.get(key), str) or not data[key].strip()
                       for key in ("method", "observation", "stop_rule"))):
            raise ValueError("report_analysis_experiment_invalid")
