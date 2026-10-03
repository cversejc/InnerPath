from collections import Counter
from typing import Any
from .report_sop_plan import enrich_sop_plan


_IMPORTANCE_SCORE = {"LOW": 0, "MEDIUM": 100, "HIGH": 250, "CRITICAL": 400}
_REPORTABILITY_SCORE = {
    "INTERNAL_ONLY": -1000,
    "OPTIONAL": 0,
    "RECOMMENDED": 150,
    "MUST_INCLUDE": 500,
}
_BLOCK_ROLE_TOKENS = (
    "BLOCK",
    "CHALLENGE",
    "DEFENSE",
    "PATTERN",
    "CONFLICT",
    "卡点",
    "挑战",
    "防御",
    "模式",
    "冲突",
    "张力",
)
_ACTION_ROLE_TOKENS = (
    "ACTION",
    "EXPERIMENT",
    "PRACTICE",
    "行动",
    "实验",
    "练习",
    "实践",
)
_DIRECTION_ROLE_TOKENS = (
    "DIRECTION",
    "STAGE",
    "TIMING",
    "INTEGRATION",
    "GROWTH",
    "方向",
    "阶段",
    "时机",
    "整合",
    "成长",
)


def _role(finding: dict[str, Any]) -> str:
    value = finding.get("semantic_role") or ""
    structured = finding.get("structured_data") or {}
    tags = structured.get("report_roles") or structured.get("roles") or []
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, (list, tuple, set)):
        tags = []
    return " ".join([str(value), *(str(tag) for tag in tags)]).upper()


def _contains(role: str, tokens: tuple[str, ...]) -> bool:
    return any(token in role for token in tokens)


def _rank(finding: dict[str, Any], focus_topics: set[str]) -> tuple[int, str]:
    score = _REPORTABILITY_SCORE.get(finding.get("reportability"), 0)
    score += _IMPORTANCE_SCORE.get(finding.get("importance"), 0)
    score += {"HIGH": 60, "MEDIUM": 30, "LOW": 0}.get(
        finding.get("confidence"), 0
    )
    score += min(len(finding.get("evidence_refs") or []), 4) * 15
    role = _role(finding)
    if _contains(role, _ACTION_ROLE_TOKENS + _DIRECTION_ROLE_TOKENS):
        score += 25
    searchable = " ".join(
        [str(finding.get("claim") or ""), str(finding.get("structured_data") or "")]
    ).casefold()
    if any(topic and topic.casefold() in searchable for topic in focus_topics):
        score += 40
    return score, str(finding.get("finding_key") or "")


def _unique_refs(values: Any, known: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(
        dict.fromkeys(
            value for value in values if isinstance(value, str) and value in known
        )
    )


def _snapshot_keys(snapshot: Any, field: str, key_name: str) -> set[str]:
    if not isinstance(snapshot, dict):
        return set()
    values = snapshot.get(field)
    if not isinstance(values, list):
        return set()
    return {
        item[key_name]
        for item in values
        if isinstance(item, dict) and isinstance(item.get(key_name), str)
    }


def _resolved_analysis_sources(
    fragment_key: str,
    fragments_by_key: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> tuple[set[str], set[str]]:
    if seen is None:
        seen = set()
    if fragment_key in seen:
        return set(), set()
    fragment = fragments_by_key.get(fragment_key)
    if fragment is None:
        return set(), set()
    seen.add(fragment_key)
    snapshot = fragment.get("source_snapshot") or {}
    findings = _snapshot_keys(snapshot, "findings", "finding_key")
    evidence = _snapshot_keys(snapshot, "evidence", "evidence_key")
    for child_key in _snapshot_keys(snapshot, "fragments", "fragment_key"):
        child_findings, child_evidence = _resolved_analysis_sources(
            child_key, fragments_by_key, seen
        )
        findings.update(child_findings)
        evidence.update(child_evidence)
    return findings, evidence


def _candidate_blocks(
    candidate: dict[str, Any], findings: list[dict[str, Any]], ranked: list[str]
) -> list[dict[str, Any]]:
    known = {item["finding_key"] for item in findings}
    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(candidate.get("priority_blocks") or [], start=1):
        if isinstance(block, dict):
            refs = _unique_refs(block.get("finding_refs"), known)
            key = block.get("block_key") or block.get("key") or f"block_{index:02d}"
            title = block.get("title") or block.get("name") or f"核心卡点 {index}"
        elif isinstance(block, str) and block in known:
            refs = [block]
            key = f"block_{index:02d}"
            title = f"核心卡点 {index}"
        else:
            continue
        if refs:
            blocks.append(
                {"block_key": str(key), "title": str(title), "finding_refs": refs}
            )
    if blocks:
        return blocks[:5]

    by_key = {item["finding_key"]: item for item in findings}
    block_refs = [
        key for key in ranked if _contains(_role(by_key[key]), _BLOCK_ROLE_TOKENS)
    ]
    return [
        {
            "block_key": f"block_{index:02d}",
            "title": f"核心卡点 {index}",
            "finding_refs": [finding_key],
        }
        for index, finding_key in enumerate(block_refs[:5], start=1)
    ]


def build_report_content_plan(
    semantic_model: dict[str, Any],
    narrative_plan: dict[str, Any],
    *,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings = [
        item
        for item in semantic_model.get("findings", [])
        if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
    ]
    by_key = {item["finding_key"]: item for item in findings}
    raw_focus_topics = (user_context or {}).get("focus_topics") or []
    if isinstance(raw_focus_topics, str):
        raw_focus_topics = [raw_focus_topics]
    focus_topics = {
        str(item)
        for item in raw_focus_topics
        if isinstance(item, (str, int, float))
    }
    ranked = [
        item["finding_key"]
        for item in sorted(
            findings,
            key=lambda item: _rank(item, focus_topics),
            reverse=True,
        )
    ]
    known = set(by_key)
    must_include = _unique_refs(narrative_plan.get("must_include_findings"), known)
    if not must_include and ranked:
        must_include = [ranked[0]]

    def role_refs(tokens: tuple[str, ...]) -> list[str]:
        return [key for key in ranked if _contains(_role(by_key[key]), tokens)]

    identity_refs = role_refs(
        ("PERSONA", "IDENTITY", "SELF_BELIEF", "RESOURCE", "ENERGY")
    )
    hidden_refs = role_refs(("SHADOW", "HIDDEN", "DEFENSE", "TENSION", "COMPLEX"))
    direction_refs = role_refs(_DIRECTION_ROLE_TOKENS)
    action_refs = role_refs(_ACTION_ROLE_TOKENS)
    relationship_refs = role_refs(("RELATIONSHIP",))
    explicit_direction = narrative_plan.get("self_direction")
    invalid_explicit_direction = False
    if (
        isinstance(explicit_direction, str)
        and explicit_direction in known
        and _contains(_role(by_key[explicit_direction]), _DIRECTION_ROLE_TOKENS)
    ):
        direction_refs = list(dict.fromkeys([explicit_direction, *direction_refs]))
    elif explicit_direction:
        invalid_explicit_direction = True
    blocks = _candidate_blocks(
        {"priority_blocks": narrative_plan.get("priority_blocks") or []},
        findings,
        ranked,
    )

    specs: list[dict[str, Any]] = []

    def add(
        key: str,
        chapter: str,
        purpose: str,
        refs: list[str],
        *,
        role: str,
        must_cover: list[str],
        required: bool = True,
        analysis_refs: list[str] | None = None,
        block_key: str | None = None,
        action_source_refs: list[str] | None = None,
        role_overrides: dict[str, str] | None = None,
    ) -> None:
        finding_refs = list(dict.fromkeys(ref for ref in refs if ref in by_key))
        if not finding_refs:
            return
        evidence_refs = list(
            dict.fromkeys(
                evidence
                for ref in finding_refs
                for evidence in (by_key[ref].get("evidence_refs") or [])
                if isinstance(evidence, str)
            )
        )
        roles = {ref: role for ref in finding_refs}
        roles.update(
            {ref: value for ref, value in (role_overrides or {}).items() if ref in roles}
        )
        specs.append(
            {
                "fragment_key": key,
                "chapter": chapter,
                "purpose": purpose,
                "finding_refs": finding_refs,
                "analysis_refs": list(dict.fromkeys(analysis_refs or [])),
                "evidence_refs": evidence_refs,
                "action_refs": _unique_refs(action_source_refs or [], set(finding_refs)),
                "must_cover": must_cover,
                "must_not_repeat": [],
                "new_information_role": role,
                "finding_roles": roles,
                "block_key": block_key,
                "required": required,
            }
        )

    add(
        "report.overview.psychic_structure",
        "identity",
        "用已确认材料概述整份说明书的主线，不展开单个判断。",
        ranked[:3],
        role="SYNTHESIZE",
        must_cover=["整体结构", "核心主题"],
        required=False,
    )
    add(
        "report.identity.outer_self",
        "identity",
        "从用户能够识别的外在表现开始建立共鸣。",
        (identity_refs or ranked)[:2],
        role="INTRODUCE",
        must_cover=["可识别的外在表现"],
    )
    self_belief = role_refs(("SELF_BELIEF", "SELF_PERCEPTION", "IDENTITY"))
    if self_belief:
        add(
            "report.identity.self_perception",
            "identity",
            "说明用户如何理解自己，并与其他已确认材料形成对照。",
            self_belief[:2],
            role="DEEPEN",
            must_cover=["自我认知"],
            required=False,
        )
    fallback_hidden = [key for key in ranked if key not in (identity_refs or ranked)[:2]]
    add(
        "report.identity.hidden_self",
        "identity",
        "在不新增诊断的前提下呈现已有材料支持的内在张力。",
        (hidden_refs or fallback_hidden or identity_refs or ranked)[:2],
        role="DEEPEN",
        must_cover=["已确认材料支持的内在张力"],
    )
    energy_refs = role_refs(("ENERGY", "RESOURCE", "CAREER_PATTERN"))
    if energy_refs:
        add(
            "report.identity.energy_pattern",
            "identity",
            "表达已确认的资源、能量和工作模式。",
            energy_refs[:2],
            role="MANIFEST",
            must_cover=["资源或能量模式"],
            required=False,
        )
    if relationship_refs:
        add(
            "report.identity.relationship_pattern",
            "identity",
            "呈现已有 Finding 支持的关系互动模式。",
            relationship_refs[:3],
            role="MANIFEST",
            must_cover=["关系互动模式"],
            required=False,
        )
    if direction_refs:
        add(
            "report.identity.self_direction",
            "identity",
            "为后续发展方向埋下已确认的语义线索。",
            direction_refs[:2],
            role="REFERENCE",
            must_cover=["发展方向的语义线索"],
            required=False,
        )

    for index, block in enumerate(blocks, start=1):
        block_key = block["block_key"]
        add(
            f"report.blocks.block_{index:02d}",
            "challenge",
            "沿现实表现、已确认机制、保护功能与长期影响解释一个卡点；缺少来源时返回语义缺口。",
            block["finding_refs"],
            role="MANIFEST",
            must_cover=["现实表现", "已确认机制", "变化所需的下一步理解"],
            block_key=block_key,
        )
    block_finding_refs = list(
        dict.fromkeys(ref for block in blocks for ref in block["finding_refs"])
    )
    if len(block_finding_refs) >= 2:
        add(
            "report.blocks.common_pattern",
            "challenge",
            "综合多个已确认卡点，说明它们是否共享同一运作模式。",
            block_finding_refs[:5],
            role="SYNTHESIZE",
            must_cover=["共同模式", "模式之间的关系"],
        )
    if block_finding_refs and action_refs:
        breakthrough_refs = list(
            dict.fromkeys(block_finding_refs[:2] + direction_refs[:1] + action_refs[:2])
        )
        add(
            "report.blocks.breakthrough",
            "challenge",
            "从已确认卡点连接到发展方向和行动，不重新选择专业判断。",
            breakthrough_refs,
            role="RESPOND",
            role_overrides={ref: "MANIFEST" for ref in block_finding_refs[:2]},
            must_cover=["需要发展的能力", "与行动的联系"],
            action_source_refs=action_refs[:2],
        )

    stage_refs = role_refs(("CURRENT_STAGE", "TIMING", "STAGE_THEME"))
    if stage_refs:
        add(
            "report.direction.current_stage",
            "direction",
            "说明当前阶段可能放大的议题和适合发展的能力，不作确定性预测。",
            stage_refs[:3],
            role="RESPOND",
            must_cover=["阶段主题", "可发展的能力"],
            required=False,
        )
    if direction_refs:
        add(
            "report.direction.life_map",
            "direction",
            "把已确认的 Self Direction 组织成现实发展方向。",
            direction_refs[:3],
            role="RESPOND",
            must_cover=["发展方向", "与前文卡点的联系"],
            required=False,
        )
    if block_finding_refs and action_refs and direction_refs:
        growth_refs = list(
            dict.fromkeys(block_finding_refs[:2] + direction_refs[:1] + action_refs[:5])
        )
        add(
            "report.direction.growth_experiments",
            "direction",
            "生成与已确认卡点、自我方向和 Action 相连的低成本成长实验。",
            growth_refs,
            role="RESPOND",
            must_cover=["目标卡点", "具体做法", "观察内容", "适配原因"],
            action_source_refs=action_refs[:5],
        )
    add(
        "report.ending",
        "direction",
        "回扣 NarrativePlan 主线，并收束到一个由来源支持的可行动方向。",
        list(dict.fromkeys(must_include[:2] + direction_refs[:1] + action_refs[:1])),
        role="REFERENCE",
        must_cover=["主线回扣", "现实落点"],
        required=False,
        action_source_refs=action_refs[:1],
    )

    enrich_sop_plan(specs, semantic_model, by_key, ranked)

    high_priority = [
        key
        for key in ranked
        if by_key[key].get("importance") in {"HIGH", "CRITICAL"}
        and by_key[key].get("reportability") != "INTERNAL_ONLY"
    ]
    allocated = {ref for spec in specs for ref in spec["finding_refs"]}
    for finding_key in dict.fromkeys(must_include + high_priority):
        if finding_key in allocated:
            continue
        preferred = "direction" if _contains(_role(by_key[finding_key]), _ACTION_ROLE_TOKENS + _DIRECTION_ROLE_TOKENS) else "identity"
        target = next((item for item in specs if item["chapter"] == preferred and (not _contains(_role(by_key[finding_key]), _ACTION_ROLE_TOKENS) or item["fragment_key"] == "report.direction.growth_experiments")), None)
        if target:
            target["finding_refs"].append(finding_key)
            target["finding_roles"][finding_key] = "REFERENCE"
            target["evidence_refs"] = list(
                dict.fromkeys(
                    target["evidence_refs"]
                    + (by_key[finding_key].get("evidence_refs") or [])
                )
            )
        else:
            add(
                "report.identity.outer_self",
                "identity",
                "建立与用户相关的识别感。",
                [finding_key],
                role="INTRODUCE",
                must_cover=["可识别的外在表现"],
            )

    analysis_fragments = [
        item
        for item in semantic_model.get("analysis_fragments", [])
        if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
    ]
    analysis_by_key = {item["fragment_key"]: item for item in analysis_fragments}
    analysis_coverage = {key: [] for key in analysis_by_key}
    for analysis_key, analysis_fragment in analysis_by_key.items():
        assigned = [spec["fragment_key"] for spec in specs if analysis_key in spec["analysis_refs"]]
        if assigned:
            analysis_coverage[analysis_key] = assigned
            continue
        source_findings, source_evidence = _resolved_analysis_sources(
            analysis_key, analysis_by_key
        )
        candidates = []
        for sequence_no, spec in enumerate(specs):
            finding_overlap = source_findings.intersection(spec["finding_refs"])
            evidence_overlap = source_evidence.intersection(spec["evidence_refs"])
            if finding_overlap or evidence_overlap:
                introduced = any(
                    spec["finding_roles"].get(key) in {"INTRODUCE", "DEEPEN"}
                    for key in finding_overlap
                )
                candidates.append(
                    (
                        spec["fragment_key"] == "report.overview.psychic_structure",
                        not spec["required"],
                        not introduced,
                        sequence_no,
                        spec,
                    )
                )
        if not candidates:
            continue
        target = min(candidates, key=lambda item: item[:4])[4]
        target["analysis_refs"].append(analysis_key)
        analysis_coverage[analysis_key].append(target["fragment_key"])

    introductions: dict[str, str] = {}
    usage: dict[str, dict[str, Any]] = {
        key: {
            "introduced_at": None,
            "used_in": [],
            "full_explanation_count": 0,
            "reference_count": 0,
        }
        for key in ranked
    }
    for spec in specs:
        for ref in spec["finding_refs"]:
            record = usage[ref]
            record["used_in"].append(spec["fragment_key"])
            role = spec["finding_roles"].get(ref)
            if role == "INTRODUCE":
                record["full_explanation_count"] += 1
                introductions.setdefault(ref, spec["fragment_key"])
                record["introduced_at"] = introductions[ref]
            else:
                record["reference_count"] += 1
                if ref in introductions:
                    spec["must_not_repeat"].append(
                        f"不要重新完整解释 {ref}；以 {role} 方式承接。"
                    )

    fragments = [
        {
            **spec,
            "sequence_no": index,
            "continuity_inputs": [
                "established_points",
                "used_metaphors",
                "unresolved_threads",
            ],
        }
        for index, spec in enumerate(specs, start=1)
    ]
    gaps = []
    if invalid_explicit_direction:
        gaps.append(
            {
                "type": "MISSING_SEMANTIC_SUPPORT",
                "target_fragment": "report.direction.growth_experiments",
                "needed": "NarrativePlan 的自我方向必须引用已确认的 Direction Finding。",
                "related_sources": [explicit_direction],
            }
        )
    if not block_finding_refs:
        gaps.append(
            {
                "type": "MISSING_SEMANTIC_SUPPORT",
                "target_fragment": "report.blocks.block_01",
                "needed": "卡点章节需要已确认的 Block Finding 或 NarrativePlan 指定的卡点来源。",
                "related_sources": [],
            }
        )
    if not action_refs:
        gaps.append(
            {
                "type": "MISSING_SEMANTIC_SUPPORT",
                "target_fragment": "report.direction.growth_experiments",
                "needed": "成长实验需要至少一个已确认 Action Finding。",
                "related_sources": block_finding_refs,
            }
        )
    if not direction_refs:
        gaps.append(
            {
                "type": "MISSING_SEMANTIC_SUPPORT",
                "target_fragment": "report.direction.growth_experiments",
                "needed": "成长实验需要一个已确认的 Self Direction Finding。",
                "related_sources": action_refs,
            }
        )

    coverage: dict[str, list[str]] = {key: [] for key in ranked}
    for spec in fragments:
        for ref in spec["finding_refs"]:
            coverage[ref].append(spec["fragment_key"])

    return {
        "version": 1,
        "status": "READY" if not gaps else "BLOCKED",
        "semantic_priorities": {
            "must_include": must_include,
            "high_priority": high_priority,
            "optional": [
                key for key in ranked if key not in must_include and key not in high_priority
            ],
            "internal_only": [],
            "candidate_blocks": blocks,
            "candidate_actions": action_refs,
            "self_direction": direction_refs,
            "analysis_fragments": [
                key for key, destinations in analysis_coverage.items() if destinations
            ],
        },
        "finding_usage": usage,
        "fragments": fragments,
        "coverage": coverage,
        "analysis_coverage": analysis_coverage,
        "gaps": gaps,
    }


def validate_report_content_plan(
    content_plan: dict[str, Any],
    semantic_model: dict[str, Any],
    narrative_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    findings = {
        item.get("finding_key")
        for item in semantic_model.get("findings", [])
        if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
    }
    fragments = content_plan.get("fragments")
    if not isinstance(fragments, list) or not 6 <= len(fragments) <= 18:
        issues.append({"type": "CONTENT_PLAN_SIZE_INVALID", "severity": "BLOCK"})
        fragments = fragments if isinstance(fragments, list) else []
    keys = [
        item.get("fragment_key")
        for item in fragments
        if isinstance(item, dict) and isinstance(item.get("fragment_key"), str)
    ]
    if len(keys) != len(fragments) or len(set(keys)) != len(keys):
        issues.append({"type": "CONTENT_PLAN_FRAGMENT_KEYS_INVALID", "severity": "BLOCK"})

    analysis_keys = {
        item.get("fragment_key")
        for item in semantic_model.get("analysis_fragments", [])
        if isinstance(item, dict)
    }
    assigned: set[str] = set()
    introductions: Counter[str] = Counter()
    analysis_usage: Counter[str] = Counter()
    analysis_coverage: dict[str, list[str]] = {key: [] for key in analysis_keys}
    block_fragment_keys = set()
    block_keys: list[str] = []
    for fragment in fragments:
        if not isinstance(fragment, dict):
            continue
        key = fragment.get("fragment_key")
        finding_refs = fragment.get("finding_refs") or []
        analysis_refs = fragment.get("analysis_refs", [])
        if not isinstance(analysis_refs, list):
            analysis_refs = []
        if (
            not finding_refs
            and not analysis_refs
            or any(ref not in findings for ref in finding_refs)
            or any(ref not in analysis_keys for ref in analysis_refs)
        ):
            issues.append(
                {
                    "type": "CONTENT_PLAN_SOURCE_INVALID",
                    "severity": "BLOCK",
                    "target_fragment": key,
                }
            )
        if not isinstance(analysis_refs, list) or any(
            not isinstance(ref, str) or ref not in analysis_keys
            for ref in analysis_refs
        ):
            issues.append(
                {
                    "type": "CONTENT_PLAN_ANALYSIS_SOURCE_INVALID",
                    "severity": "BLOCK",
                    "target_fragment": key,
                }
            )
        else:
            for ref in analysis_refs:
                analysis_usage[ref] += 1
                analysis_coverage[ref].append(key)
        if any(ref not in finding_refs for ref in (fragment.get("action_refs") or [])):
            issues.append(
                {
                    "type": "CONTENT_PLAN_ACTION_SOURCE_INVALID",
                    "severity": "BLOCK",
                    "target_fragment": key,
                }
            )
        if not isinstance(fragment.get("must_cover"), list) or not fragment["must_cover"]:
            issues.append(
                {
                    "type": "CONTENT_PLAN_MUST_COVER_INVALID",
                    "severity": "BLOCK",
                    "target_fragment": key,
                }
            )
        assigned.update(ref for ref in finding_refs if isinstance(ref, str))
        for ref, role in (fragment.get("finding_roles") or {}).items():
            if role == "INTRODUCE":
                introductions[ref] += 1
        if fragment.get("block_key"):
            block_fragment_keys.add(fragment["block_key"])
            block_keys.append(fragment["block_key"])

    duplicate_blocks = sorted(
        key for key, count in Counter(block_keys).items() if count > 1
    )
    if duplicate_blocks:
        issues.append(
            {
                "type": "CONTENT_PLAN_BLOCK_KEYS_INVALID",
                "severity": "BLOCK",
                "block_keys": duplicate_blocks,
            }
        )
    repeated_analysis = sorted(
        key for key, count in analysis_usage.items() if count > 1
    )
    if repeated_analysis:
        issues.append(
            {
                "type": "CONTENT_PLAN_ANALYSIS_REPEATED",
                "severity": "BLOCK",
                "fragment_keys": repeated_analysis,
            }
        )
    if content_plan.get("analysis_coverage", analysis_coverage) != analysis_coverage:
        issues.append(
            {"type": "CONTENT_PLAN_ANALYSIS_COVERAGE_INVALID", "severity": "BLOCK"}
        )

    must_include = set(narrative_plan.get("must_include_findings") or [])
    missing = sorted(must_include - assigned)
    if missing:
        issues.append(
            {
                "type": "CONTENT_PLAN_MUST_INCLUDE_UNASSIGNED",
                "severity": "BLOCK",
                "finding_keys": missing,
            }
        )
    high_priority = {
        item.get("finding_key")
        for item in semantic_model.get("findings", [])
        if isinstance(item, dict)
        and item.get("importance") in {"HIGH", "CRITICAL"}
        and item.get("reportability") != "INTERNAL_ONLY"
    }
    uncovered_critical = sorted(high_priority - assigned)
    if uncovered_critical:
        issues.append(
            {
                "type": "CONTENT_PLAN_HIGH_PRIORITY_UNASSIGNED",
                "severity": "BLOCK",
                "finding_keys": uncovered_critical,
            }
        )
    repeated_introductions = sorted(
        key for key, count in introductions.items() if count > 1
    )
    if repeated_introductions:
        issues.append(
            {
                "type": "CONTENT_PLAN_MULTIPLE_INTRODUCTIONS",
                "severity": "BLOCK",
                "finding_keys": repeated_introductions,
            }
        )

    priority_blocks = narrative_plan.get("priority_blocks") or []
    planned_blocks = {
        item.get("block_key")
        for item in (content_plan.get("semantic_priorities") or {}).get(
            "candidate_blocks", []
        )
        if isinstance(item, dict)
    }
    for index, block in enumerate(priority_blocks, start=1):
        key = (
            block.get("block_key") or block.get("key") or f"block_{index:02d}"
            if isinstance(block, dict)
            else f"block_{index:02d}"
        )
        if key not in planned_blocks or key not in block_fragment_keys:
            issues.append(
                {
                    "type": "CONTENT_PLAN_PRIORITY_BLOCK_UNASSIGNED",
                    "severity": "BLOCK",
                    "block_key": key,
                }
            )
    for gap in content_plan.get("gaps") or []:
        issues.append(
            {
                "type": gap.get("type", "MISSING_SEMANTIC_SUPPORT"),
                "severity": "BLOCK",
                **gap,
            }
        )
    return issues
