"""Route confirmed SOP analyses to their reader-facing purpose."""
TOPIC_TARGETS = {
    "analysis.s2.persona": "report.identity.outer_self",
    "analysis.s2.mapping": "report.identity.self_perception",
    "analysis.s2.authority": "report.identity.self_perception",
    "analysis.s2.shadow": "report.identity.hidden_self",
    "analysis.s2.complex": "report.identity.hidden_self",
    "analysis.s2.cycle": "report.blocks.common_pattern",
    "analysis.s3.self": "report.identity.self_direction",
    "analysis.s3.quadrant": "report.blocks.breakthrough",
    "analysis.s3.timeline": "report.direction.life_map",
    "analysis.s3.yijing": "report.direction.current_stage",
    "analysis.s3.bridge": "report.ending",
    "analysis.s3.integration": "report.identity.self_direction",
    "analysis.s4.defense": "report.identity.hidden_self",
    "analysis.s4.energy": "report.identity.energy_pattern",
    "analysis.s4.functions": "report.identity.energy_pattern",
    "analysis.s4.relationships": "report.identity.relationship_pattern",
    "analysis.s4.blocks": "report.blocks.common_pattern",
    "analysis.s4.breakthrough": "report.blocks.breakthrough",
    "analysis.s4.timing_self": "report.direction.life_map",
    "analysis.s4.shadow_practice": "report.direction.growth_experiments",
    "analysis.s4.complex_practice": "report.direction.growth_experiments",
    "analysis.s4.experiments": "report.direction.growth_experiments",
}


def enrich_sop_plan(specs, semantic_model, by_key, ranked):
    analyses = semantic_model.get("analysis_fragments") or []
    if not any(str(a.get("fragment_key", "")).startswith("analysis.s") for a in analyses):
        return
    foundation_refs = [a["fragment_key"] for a in analyses if a["fragment_key"].startswith("analysis.s1.")]
    if foundation_refs and ranked:
        refs = [key for key in ranked if str(key).startswith("s1.")] or ranked[:1]
        specs.insert(2, {
            "fragment_key": "report.identity.foundation_notes", "chapter": "identity",
            "purpose": "把已审核命盘逻辑转译为可理解的旁注，注明出生信息/流派不确定性；不把符号当心理证据。",
            "finding_refs": refs, "analysis_refs": foundation_refs,
            "evidence_refs": list(dict.fromkeys(e for key in refs for e in by_key[key].get("evidence_refs", []))),
            "action_refs": [], "must_cover": ["八字十项及紫微重点的已确认内容或暂缓边界", "心理含义只是待验证线索"],
            "must_not_repeat": ["后续心理章节不要重复逐条命盘解释"],
            "new_information_role": "DEEPEN", "finding_roles": {key: "REFERENCE" for key in refs}, "block_key": None, "required": True,
        })
    by_fragment = {s["fragment_key"]: s for s in specs}
    for analysis in analyses:
        key = analysis["fragment_key"]
        target = by_fragment.get(TOPIC_TARGETS.get(key))
        if key == "analysis.s3.yijing" and target is None:
            target = by_fragment.get("report.direction.life_map")
        if target is not None:
            if key not in target["analysis_refs"]:
                target["analysis_refs"].append(key)
            if semantic_model.get("framework_contract"):
                # Copy only confirmed source identities, never manufacture a Finding.
                snapshot = analysis.get("source_snapshot") or {}
                for ref in snapshot.get("findings", []):
                    finding_key = ref.get("finding_key")
                    if finding_key in by_key and finding_key not in target["finding_refs"]:
                        target["finding_refs"].append(finding_key)
                        target["finding_roles"][finding_key] = "REFERENCE"
                target["evidence_refs"] = list(dict.fromkeys(target["evidence_refs"] + [r["evidence_key"] for r in snapshot.get("evidence", [])]))
    first_by_chapter = {}
    for spec in specs:
        chapter = spec["chapter"]
        first_by_chapter.setdefault(chapter, spec)
        if spec is first_by_chapter[chapter]:
            spec["chapter_opening"] = True
            spec["must_cover"].extend(["一句关键结论", "本章简短系统路径图（箭头文本即可）"])
        if spec["fragment_key"].startswith("report.blocks.block_"):
            spec["must_cover"] = list(dict.fromkeys(["常见现实场景", "运作机制", "过去保护了什么", "长期代价", "整合邀请", *spec["must_cover"]]))
            spec["must_not_repeat"].append("本段不列解决步骤，行动集中在第三章")
        if spec["fragment_key"] == "report.direction.life_map":
            spec["must_cover"].extend(["已确认的每个大运真实起止年份", "阶段基调/放大主题/能力/旧模式"])
        if spec["fragment_key"] == "report.direction.growth_experiments":
            spec["must_cover"].extend(["3–5个已确认成长实验", "频率/耗时/观察/退出条件", "日/周/月/季复盘节奏"])
        if spec["fragment_key"] == "report.ending":
            spec["must_cover"].extend(["哲学收束与温暖寄语", "已核验金句或不署名原创句"])
        if spec["fragment_key"] != "report.direction.growth_experiments":
            spec["must_not_repeat"].append("不展开实验动作/频率/退出条件，具体实践统一在成长实验节")
        if spec["fragment_key"] != "report.ending":
            spec["must_not_repeat"].append("不引用收束金句，金句仅在寄语出现一次")
