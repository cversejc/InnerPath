"""Structural coverage gates; actual meaning is checked independently by QA."""
from copy import deepcopy
from .product_framework import validate_framework
from .action_contract import validate_growth_experiments

STATUSES = {"FULFILLED", "DEFERRED", "NOT_APPLICABLE", "MISSING"}


def normalize_coverage(record, content, *, allow_not_applicable=False):
    if (not isinstance(record, dict) or not isinstance(record.get("status"), str)
            or record["status"] not in STATUSES):
        raise ValueError("framework_coverage_required")
    status, reason, quote = record["status"], record.get("reason"), record.get("quote")
    questions = record.get("follow_up_questions", [])
    if (not isinstance(reason, str) or not reason.strip()
            or not isinstance(quote, str) or not quote.strip() or quote not in content
            or not isinstance(questions, list)
            or any(not isinstance(q, str) or not q.strip() for q in questions)):
        raise ValueError("framework_coverage_invalid")
    if status == "NOT_APPLICABLE" and not allow_not_applicable:
        raise ValueError("framework_core_cannot_be_omitted")
    if status == "DEFERRED" and not questions:
        raise ValueError("framework_follow_up_required")
    return {"status": status, "reason": reason.strip(), "quote": quote,
            "follow_up_questions": list(dict.fromkeys(questions))}


def normalize_requirement_coverage(records, requirements, content):
    if not isinstance(records, list):
        raise ValueError("framework_requirement_coverage_required")
    if any(not isinstance(r, dict) or not isinstance(r.get("requirement_id"), str) for r in records):
        raise ValueError("framework_requirement_coverage_incomplete")
    by_id = {r["requirement_id"]: r for r in records}
    expected = {r["requirement_id"] for r in requirements}
    if len(by_id) != len(records) or set(by_id) != expected:
        raise ValueError("framework_requirement_coverage_incomplete")
    return [{"requirement_id": r["requirement_id"], **normalize_coverage(
        by_id[r["requirement_id"]], content,
        allow_not_applicable=r.get("allow_not_applicable", False))} for r in requirements]


def analysis_coverage_issues(contract, analyses, *, stage=None):
    validate_framework(contract)
    by_key = {a["fragment_key"]: a for a in analyses}
    issues = []
    for requirement in contract["analysis_requirements"]:
        if stage and requirement["stage"] != stage:
            continue
        row = by_key.get(requirement["fragment_key"])
        try:
            record = normalize_coverage(
                (row.get("source_snapshot") or {}).get("framework_coverage") if row else None,
                row.get("content", "") if row else "", allow_not_applicable=True)
            if record["status"] == "MISSING":
                raise ValueError("framework_analysis_missing")
        except ValueError as error:
            issues.append({"type": str(error), "severity": "BLOCK", **requirement})
    return issues


def attach_framework_requirements(specs, semantic_model, contract):
    """Keep content duties independent from headings and require exact source ownership."""
    validate_framework(contract)
    analyses = {a["fragment_key"]: a for a in semantic_model.get("analysis_fragments", [])}
    findings = {f["finding_key"]: f for f in semantic_model.get("findings", [])}
    issues = analysis_coverage_issues(contract, list(analyses.values()))
    allocations = []
    for requirement in contract["report_requirements"]:
        target = requirement["target_fragment"]
        targets = [s for s in specs if s["fragment_key"] == target or
                   (target.endswith("*") and s["fragment_key"].startswith(target[:-1]))]
        if not targets and not target.endswith("*"):
            sources = [key for key in requirement["analysis_sources"] if key in analyses]
            refs = list(dict.fromkeys(ref["finding_key"] for key in sources
                for ref in (analyses[key].get("source_snapshot") or {}).get("findings", [])
                if ref.get("finding_key") in findings))
            if sources:
                chapter = "direction" if target.startswith("report.direction") or target == "report.ending" else "identity"
                new = {"fragment_key": target, "chapter": chapter,
                       "purpose": requirement["title"], "finding_refs": refs,
                       "analysis_refs": [], "evidence_refs": [], "action_refs": [],
                       "must_cover": [], "must_not_repeat": [], "new_information_role": "DEEPEN",
                       "finding_roles": {key: "REFERENCE" for key in refs}, "block_key": None,
                       "required": True}
                specs.append(new)
                targets = [new]
        if not targets:
            issues.append({"type": "FRAMEWORK_REPORT_REQUIREMENT_UNASSIGNED", "severity": "BLOCK",
                           "requirement_id": requirement["requirement_id"], "target_fragment": target})
        for spec in targets:
            spec["required"] = True
            spec.setdefault("requirements", []).append(deepcopy(requirement))
            spec["must_cover"].extend(c for c in requirement["checks"] if c not in spec["must_cover"])
            if requirement["requirement_id"] == "R.psychic_structure":
                refs = [ref["finding_key"] for key in requirement["analysis_sources"] if key in analyses
                        for ref in (analyses[key].get("source_snapshot") or {}).get("findings", [])
                        if ref.get("finding_key") in findings]
                for key in refs:
                    if key not in spec["finding_refs"]:
                        spec["finding_refs"].append(key)
                        spec["finding_roles"][key] = "REFERENCE"
        allocations.append({"requirement_id": requirement["requirement_id"],
                            "fragment_keys": [s["fragment_key"] for s in targets],
                            "state": "ALLOCATED" if targets else "MISSING"})
    # Place new duties in reader order; sources themselves are assigned by the SOP router.
    order = ["report.overview.psychic_structure", "report.identity.outer_self",
             "report.identity.foundation_notes", "report.identity.self_perception",
             "report.identity.hidden_self", "report.identity.self_direction",
             "report.identity.energy_pattern", "report.identity.relationship_pattern"]
    tail = ["report.blocks.common_pattern", "report.blocks.breakthrough",
            "report.direction.current_stage", "report.direction.life_map",
            "report.direction.growth_experiments", "report.ending"]
    def position(spec):
        key = spec["fragment_key"]
        return order.index(key) if key in order else 10 if spec.get("block_key") else 20 + tail.index(key) if key in tail else 40
    specs.sort(key=position)
    return {"contract": deepcopy(contract), "allocations": allocations, "issues": issues}


def validate_framework_plan(plan, semantic_model, contract):
    validate_framework(contract)
    issues = analysis_coverage_issues(contract, semantic_model.get("analysis_fragments", []))
    specs = plan.get("fragments", [])
    expected_ids = {r["requirement_id"] for r in contract["report_requirements"]}
    present = {r["requirement_id"] for s in specs for r in s.get("requirements", [])}
    for key in sorted(expected_ids - present):
        issues.append({"type": "FRAMEWORK_REPORT_REQUIREMENT_UNASSIGNED", "severity": "BLOCK", "requirement_id": key})
    for requirement in contract["report_requirements"]:
        owners = [s for s in specs if any(r.get("requirement_id") == requirement["requirement_id"] for r in s.get("requirements", []))]
        for spec in owners:
            if not spec.get("required") or not set(requirement["checks"]).issubset(spec.get("must_cover", [])):
                issues.append({"type": "FRAMEWORK_REQUIREMENT_CONTRACT_CHANGED", "severity": "BLOCK",
                               "requirement_id": requirement["requirement_id"], "target_fragment": spec["fragment_key"]})
    findings = semantic_model.get("findings", [])
    growth = next((s for s in specs if s["fragment_key"] == "report.direction.growth_experiments"), {})
    actions = [f for f in findings if f["finding_key"] in growth.get("action_refs", [])]
    try:
        validate_growth_experiments(actions, findings)
    except ValueError as error:
        issues.append({"type": str(error), "severity": "BLOCK", "target_fragment": "report.direction.growth_experiments"})
    selected_blocks = {ref for s in specs if s.get("block_key") for ref in s.get("finding_refs", [])
                       if any(f["finding_key"] == ref and f.get("semantic_role") == "BLOCK" for f in findings)}
    addressed = {ref for action in actions for ref in (action.get("structured_data") or {}).get("block_refs", [])}
    if selected_blocks - addressed:
        issues.append({"type": "FRAMEWORK_BLOCK_ACTION_UNCOVERED", "severity": "BLOCK", "finding_keys": sorted(selected_blocks - addressed)})
    if not 3 <= len(selected_blocks) <= 5:
        issues.append({"type": "FRAMEWORK_BLOCK_COUNT_INVALID", "severity": "BLOCK"})
    return issues


def report_coverage_issues(plan, fragments):
    """Check declared coverage against current text; QA then judges the declaration."""
    by_key = {f["fragment_key"]: f for f in fragments}
    issues = []
    for spec in plan.get("fragments", []):
        requirements = spec.get("requirements", [])
        if not requirements:
            continue
        row = by_key.get(spec["fragment_key"])
        try:
            records = normalize_requirement_coverage(
                (row.get("source_snapshot") or {}).get("requirement_coverage") if row else None,
                requirements, row.get("content", "") if row else "")
            if any(r["status"] == "MISSING" for r in records):
                raise ValueError("framework_report_content_missing")
            source = row.get("source_snapshot") or {}
            used_analysis = {r.get("fragment_key") for r in source.get("fragments", [])}
            used_findings = {r.get("finding_key") for r in source.get("findings", [])}
            if not set(spec.get("analysis_refs", [])).issubset(used_analysis):
                raise ValueError("framework_analysis_source_uncovered")
            if not set(spec.get("action_refs", []) + spec.get("required_finding_refs", [])).issubset(used_findings):
                raise ValueError("framework_action_source_uncovered")
        except ValueError as error:
            issues.append({"type": str(error), "severity": "BLOCK", "target_fragment": spec["fragment_key"]})
    return issues


def normalize_framework_review(records, contract, plan, fragments):
    validate_framework(contract)
    requirements = contract["report_requirements"]
    by_key = {f["fragment_key"]: f for f in fragments}
    if not isinstance(records, list) or len(records) != len(requirements):
        raise ValueError("framework_review_required")
    if any(not isinstance(r, dict) or not isinstance(r.get("requirement_id"), str) for r in records):
        raise ValueError("framework_review_incomplete")
    by_id = {r["requirement_id"]: r for r in records}
    if set(by_id) != {r["requirement_id"] for r in requirements}:
        raise ValueError("framework_review_incomplete")
    normalized = []
    for requirement in requirements:
        record = by_id[requirement["requirement_id"]]
        keys = record.get("fragment_keys")
        allowed = {s["fragment_key"] for s in plan.get("fragments", []) if any(
            r.get("requirement_id") == requirement["requirement_id"] for r in s.get("requirements", []))}
        if (not isinstance(keys, list) or not keys or any(not isinstance(k, str) for k in keys)
                or len(set(keys)) != len(keys) or set(keys) != allowed or not allowed.issubset(by_key)):
            raise ValueError("framework_review_fragment_invalid")
        quote = record.get("quote")
        if not isinstance(quote, str) or not any(quote and quote in by_key[k]["content"] for k in keys):
            raise ValueError("framework_review_quote_invalid")
        content = next(by_key[k]["content"] for k in keys if quote in by_key[k]["content"])
        normalized.append({"requirement_id": requirement["requirement_id"], "fragment_keys": keys,
                           **normalize_coverage(record, content)})
    return normalized
