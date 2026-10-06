"""Auditable analysis structures and source-bound resource-to-action paths."""
from copy import deepcopy
from hashlib import sha256
import json

from .framework_coverage import normalize_coverage
from .action_contract import validate_growth_experiments

VERSION = "report-reasoning-2026-10-04-v1"
ANALYSIS_STRUCTURES = {
    "analysis.s2.mapping": {
        "self_description": "用户如何看待自己，区分自述与解释",
        "core_belief": "应该/必须/不能所形成的底层信念假设",
        "authority_origin": "权威内化的依据，不补造童年经历",
        "counterexample": "自述反证，或明确列出待核对的问题",
    },
    "analysis.s2.complex": {
        "trigger": "具体或待核对的触发情境", "emotion": "核心情绪假设",
        "automatic_thought": "自动想法/信念假设", "defense": "防御方式",
        "protection": "短期保护功能", "repetition_cost": "长期重复和代价",
        "reality_check": "现实依据、反证和核对方式",
    },
    "analysis.s3.self": {
        "dominant_pole": "目前偏重的一端", "excluded_pole": "被排除的另一端",
        "integration": "两端共同存在的能力与具体情境",
    },
    "analysis.s3.quadrant": {
        "archetype": "中式人物意象", "learnable_capacity": "可学习能力",
        "fit_reason": "为何回应本人的议题", "boundary": "比喻与不适用边界",
    },
    "analysis.s3.timeline": {
        "periods": "各阶段对象列表：start_year/end_year/interaction/theme/capacity/old_pattern",
        "uncertainty": "计算前提与条件式未来边界",
    },
    "analysis.s4.energy": {
        "charging": "充电情境及用户反馈", "draining": "耗电情境及用户反馈",
        "reality_check": "反例、未确认部分与观察方式",
    },
    "analysis.s4.functions": {
        "exploration": "探索入口", "valuation": "价值判断入口",
        "execution": "执行入口", "feedback": "反馈入口",
        "tension": "本人路径及张力，未自报不推断类型/分数",
    },
    "analysis.s4.breakthrough": {
        "common_mechanism": "多个卡点的共性机制", "resource_translation": "资源到调节功能的转译",
        "capacity_gap": "需发展能力及现实缺口", "integration_task": "整合任务",
        "tool_rationale": "工具为何承接能力和卡点，关联Action中的reasoning_path",
    },
}
PATH_FIELDS = {
    "regulation_function": "资源如何调节", "capacity": "需要发展的能力",
    "reality_gap": "现实缺口", "integration_task": "两端整合任务",
    "tool": "采用工具", "rationale": "工具到该实验的适配理由及边界",
}
RESOURCE_ROLES = {"RESOURCE", "USEFUL_GOD", "STRUCTURE", "SELF_DIRECTION"}


def reasoning_snapshot():
    contract = {"version": VERSION, "analysis_structures": deepcopy(ANALYSIS_STRUCTURES),
                "path_fields": deepcopy(PATH_FIELDS), "resource_roles": sorted(RESOURCE_ROLES)}
    contract["digest"] = sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest()
    return contract


def validate_reasoning_contract(contract):
    if contract != reasoning_snapshot():
        raise ValueError("reasoning_contract_invalid")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def normalize_structured_analysis(key, record, content):
    fields = ANALYSIS_STRUCTURES.get(key)
    if fields is None:
        raise ValueError("reasoning_analysis_key_invalid")
    normalized = normalize_coverage(record, content)
    details = record.get("details")
    if not isinstance(details, dict) or set(details) - set(fields):
        raise ValueError("reasoning_analysis_details_invalid")
    if normalized["status"] == "FULFILLED":
        if set(details) != set(fields) or any(not _text(v) for k, v in details.items() if k != "periods"):
            raise ValueError("reasoning_analysis_details_required")
        if "periods" in fields:
            periods = details["periods"]
            if not isinstance(periods, list) or not periods:
                raise ValueError("reasoning_periods_required")
            last_end = None
            for period in periods:
                if not isinstance(period, dict):
                    raise ValueError("reasoning_period_invalid")
                start, end = period.get("start_year"), period.get("end_year")
                if (not isinstance(start, int) or isinstance(start, bool)
                        or not isinstance(end, int) or isinstance(end, bool) or start > end
                        or last_end is not None and start <= last_end
                        or any(not _text(period.get(f)) for f in ("interaction", "theme", "capacity", "old_pattern"))):
                    raise ValueError("reasoning_period_invalid")
                last_end = end
    return {**normalized, "details": deepcopy(details)}


def validate_action_reasoning(findings, evidence_keys, *, reality_keys=None, check_count=True):
    by_key = {f["finding_key"]: f for f in findings}
    validate_growth_experiments(findings, findings, check_count=check_count)
    for action in (f for f in findings if str(f.get("semantic_role", "")).upper() == "ACTION"):
        data = action.get("structured_data") or {}
        path = data.get("reasoning_path")
        if (not isinstance(path, dict) or any(not _text(path.get(field)) for field in PATH_FIELDS)
                or path.get("tool") != data.get("method")):
            raise ValueError("reasoning_action_path_required")
        resources = path.get("resource_refs")
        refs = path.get("evidence_refs")
        if (not isinstance(resources, list) or not resources
                or any(not isinstance(k, str) or k not in by_key or str(by_key[k].get("semantic_role", "")).upper() not in RESOURCE_ROLES
                       for k in resources)):
            raise ValueError("reasoning_resource_reference_invalid")
        if (not isinstance(refs, list) or not refs
                or any(not isinstance(k, str) or k not in evidence_keys for k in refs)
                or not set(refs).intersection(evidence_keys if reality_keys is None else reality_keys)):
            raise ValueError("reasoning_reality_evidence_required")
        # Every link must use these same Blocks; generic role labels do not substitute for IDs.
        if path.get("block_refs") != data.get("block_refs"):
            raise ValueError("reasoning_block_reference_mismatch")
        blocks = data.get("block_refs")
        if (not isinstance(blocks, list) or not blocks or any(
                not isinstance(k, str) or k not in by_key or str(by_key[k].get("semantic_role", "")).upper() != "BLOCK" for k in blocks)):
            raise ValueError("reasoning_block_reference_mismatch")


def validate_timeline_source(record, evidence, source_keys):
    if record["status"] != "FULFILLED":
        return
    known = set()
    for row in evidence:
        value = row.get("value") or {}
        if row.get("source_type") not in {"SYSTEM_CALCULATED", "CONSULTANT_CORRECTED"} or row.get("evidence_key") not in source_keys or not isinstance(value, dict):
            continue
        for period in (value.get("bazi_facts") or {}).get("dayun", []):
            if isinstance(period, dict):
                known.add((period.get("start_year"), period.get("end_year")))
    provided = {(p["start_year"], p["end_year"]) for p in record["details"]["periods"]}
    if not known or not provided.issubset(known):
        raise ValueError("reasoning_period_source_mismatch")


def reasoning_issues(model, *, stage=None):
    contract = model.get("reasoning_contract")
    if not contract:
        return []
    validate_reasoning_contract(contract)
    by_key = {a["fragment_key"]: a for a in model.get("analysis_fragments", [])}
    issues = []
    for key in ANALYSIS_STRUCTURES:
        if stage and not key.startswith(f"analysis.{stage.lower()}."):
            continue
        row = by_key.get(key, {})
        try:
            record = normalize_structured_analysis(key, (row.get("source_snapshot") or {}).get("structured_analysis"),
                                                  row.get("content", ""))
            if record["status"] == "MISSING":
                raise ValueError("reasoning_analysis_missing")
            if key == "analysis.s3.timeline":
                validate_timeline_source(record, model.get("evidence", []), {
                    e.get("evidence_key") for e in (row.get("source_snapshot") or {}).get("evidence", [])})
        except ValueError as error:
            issues.append({"type": str(error), "severity": "BLOCK", "target_fragment": key})
    if stage in (None, "S4"):
        try:
            validate_action_reasoning(model.get("findings", []), {e["evidence_key"] for e in model.get("evidence", [])},
                reality_keys={e["evidence_key"] for e in model.get("evidence", []) if e.get("source_type") == "USER_PROVIDED"})
        except ValueError as error:
            issues.append({"type": str(error), "severity": "BLOCK", "target_fragment": "report.direction.growth_experiments"})
    return issues


def action_source_refs(finding):
    data = finding.get("structured_data") or {}
    path = data.get("reasoning_path") or {}
    if not isinstance(path, dict):
        raise ValueError("reasoning_action_path_required")
    refs = [data.get("block_refs", []), path.get("resource_refs", [])]
    if any(not isinstance(group, list) or any(not isinstance(k, str) for k in group) for group in refs):
        raise ValueError("reasoning_resource_reference_invalid")
    return list(dict.fromkeys([k for group in refs for k in group]))


def validate_priority_blocks(candidate, model):
    by_key = {f["finding_key"]: f for f in model.get("findings", [])}
    addressed = {k for f in model.get("findings", []) if f.get("semantic_role") == "ACTION"
                 for k in (f.get("structured_data") or {}).get("block_refs", [])}
    blocks = candidate.get("priority_blocks")
    if not isinstance(blocks, list) or not 3 <= len(blocks) <= 5:
        raise ValueError("reasoning_priority_blocks_required")
    selected = set()
    for block in blocks:
        refs = block.get("finding_refs") if isinstance(block, dict) else None
        if not isinstance(refs, list) or any(not isinstance(k, str) or k not in by_key for k in refs):
            raise ValueError("reasoning_priority_block_invalid")
        owners = [k for k in refs if by_key[k].get("semantic_role") == "BLOCK"]
        if len(owners) != 1 or owners[0] in selected or owners[0] not in addressed:
            raise ValueError("reasoning_priority_block_invalid")
        selected.add(owners[0])
