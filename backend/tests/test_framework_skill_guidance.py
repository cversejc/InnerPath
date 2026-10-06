"""Human skill guidance covers the designated sources, independently of I/O."""
from copy import deepcopy

import pytest

from app.domains.calendar.skill_definitions import default_calendar_skill_specifications
from app.domains.skills.definitions import (
    REASONING_GUIDANCE_SKILL_KEYS,
    compile_reasoning_guidance_specification,
    default_analysis_skill_specifications,
    default_narrative_skill_specifications,
    default_validator_skill_specification,
    validate_skill_specification,
)
from app.domains.skills.framework_guidance import (
    framework_reasoning_guidance,
    framework_reference,
    framework_source,
)
from app.domains.skills.schemas import SkillReasoningGuidanceUpdate


def specifications():
    return [*default_analysis_skill_specifications(),
            *default_narrative_skill_specifications(),
            default_validator_skill_specification(),
            *(spec for _, spec in default_calendar_skill_specifications())]


@pytest.mark.parametrize("spec", specifications(), ids=lambda s: s["identity"]["skill_key"])
def test_all_current_defaults_use_complete_document_guidance_and_compile(spec):
    key = spec["identity"]["skill_key"]
    guidance = framework_reasoning_guidance(key)
    assert spec["reasoning_guidance"] == guidance
    # The complete defaults can still be edited and saved through the admin API.
    assert SkillReasoningGuidanceUpdate(**guidance).model_dump() == guidance
    assert "methodology" not in spec["instructions"]
    before = deepcopy(spec)
    compiled = compile_reasoning_guidance_specification(spec)
    assert validate_skill_specification(compiled) == compiled
    assert spec == before
    assert compiled["instructions"]["objective"] == guidance["objective"]
    assert compiled["instructions"]["methodology"][:len(guidance["methodology"])] == guidance["methodology"]
    assert compiled["instructions"]["methodology"][len(guidance["methodology"]):] == spec["runtime_contract"]["system_requirements"]
    for field in ("input_contract", "output_contract", "context_policy", "processor_policy", "model_policy"):
        assert compiled[field] == spec[field]
    source = framework_source(key)
    assert source["source"] == (
        "docs/日历生成思路.md" if key.startswith("calendar.") else "docs/产品分析框架.md"
    )
    assert len(source["sha256"]) == 64
    assert not any(technical in "\n".join(guidance["methodology"])
                   for technical in ("analysis_fragments", "fragment_key", "output_contract", "JSON Schema", "scorecard.dimensions"))


def test_all_eleven_skills_and_every_report_section_are_mapped():
    assert {s["identity"]["skill_key"] for s in specifications()} == REASONING_GUIDANCE_SKILL_KEYS
    sections = {section for s in specifications() if s["identity"]["skill_key"].startswith("report.")
                for section in framework_source(s["identity"]["skill_key"])["sections"]}
    assert {"核心总领", "第六步", "第五步", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4",
            "3.1", "3.2", "3.3", "3.4", "3.5", "4.1", "4.2", "4.3", "4.4", "4.5",
            "5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7"} <= sections


def test_symbolic_tables_are_complete_source_rows_in_both_editor_and_runtime():
    guidance = "\n".join(framework_reasoning_guidance("report.s2_psychology_mapping")["methodology"])
    for kind, count in (("ten_gods", 10), ("stars", 14)):
        table = framework_reference(kind)
        assert len(table) == count
        for name, columns in table.items():
            assert name in guidance
            assert all(value in guidance for value in columns.values())
    assert "用知识/思考建立心理防御" in guidance
    assert "主权交接" in guidance
    assert "触发→阴影浮现→情结激活→防御反应→结果→重复" in guidance


def test_calendar_analysis_covers_the_five_steps_conditions_and_four_color_reasoning():
    text = "\n".join(framework_reasoning_guidance("calendar.temporal_analysis")["methodology"])
    assert all(token in text for token in (
        "STEP 1", "STEP 2", "STEP 3", "STEP 4", "STEP 5",
        "甲己合土", "子丑合土", "申子辰水", "开库不是见冲就开", "无争合",
        "推进", "探索", "校准", "收束", "依靠制衡更多还是流通更多", "实际反馈",
    ))
    monthly = "\n".join(framework_reasoning_guidance("calendar.monthly_tone")["methodology"])
    assert all(token in monthly for token in (
        "整体能量方向", "最重要的成长任务", "最值得利用的力量",
        "哪一种旧模式", "最重要的一条原则", "明显的节奏变化",
    ))
    daily = "\n".join(framework_reasoning_guidance("calendar.daily_authoring")["methodology"])
    assert "长期课题" in daily and "问题必须来自用户人生说明书中的真实模式" in daily
    calibration = "\n".join(framework_reasoning_guidance("calendar.calibration")["methodology"])
    assert "连续10天" in calibration and "同一个缺点" in calibration
    assert "觉察→ 尝试→ 行动→ 反馈→ 校准→ 再行动" in calibration


def test_editable_limit_does_not_include_compiled_program_rules():
    spec = default_narrative_skill_specifications()[1]
    compiled = compile_reasoning_guidance_specification(spec)
    assert len(compiled["instructions"]["methodology"]) > 40
    validate_skill_specification(compiled)
    spec["reasoning_guidance"]["methodology"] = ["人工维护的思路"] * 41
    with pytest.raises(ValueError, match="skill_reasoning_guidance_invalid"):
        validate_skill_specification(spec)
