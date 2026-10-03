from lunar_python import Solar
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation
from app.domains.reports.generation.bazi_calculator import bazi_calculator
from app.domains.skills.analysis_sop import stage_contract
from app.application.report_analysis import build_analysis_completion_gate
from app.domains.skills.definitions import default_analysis_skill_specifications
from app.domains.skills.runtime import build_context_envelope


def test_pillars_follow_jieqi_not_lunar_new_year():
    lunar = Solar.fromYmdHms(2024, 2, 4, 12, 0, 0).getLunar()
    ec = lunar.getEightChar()
    result = bazi_calculator.calculate_bazi(2024, 2, 4, 12, 0)
    assert result["year"]["pillar"] == ec.getYear()
    assert result["month"]["pillar"] == ec.getMonth()
    before = bazi_calculator.calculate_bazi(2024, 2, 4, 12, 0)
    after = bazi_calculator.calculate_bazi(2024, 2, 4, 18, 0)
    assert before["year"]["pillar"] != after["year"]["pillar"]


def test_lunar_time_matches_solar_and_full_foundation():
    profile = dict(birth_year=2004, birth_month=6, birth_day=15, birth_hour=15, birth_minute=15, gender="female")
    foundation = calculate_mingli_foundation(profile)
    l = Solar.fromYmdHms(2004, 6, 15, 15, 15, 0).getLunar()
    lunar_result = bazi_calculator.calculate_bazi(l.getYear(), abs(l.getMonth()), l.getDay(), 15, 15, False, l.getMonth() < 0)
    assert lunar_result["hour"]["pillar"] == foundation["bazi"]["hour"]["stem"] + foundation["bazi"]["hour"]["branch"]
    assert len(foundation["bazi_facts"]["dayun"]) == 9
    assert all(p["hidden_stems"] for p in foundation["bazi_facts"]["pillars"].values())
    assert len(foundation["ziwei"]["flying_transformations"]) == 48
    assert foundation["ziwei"]["body_palace"] and foundation["ziwei"]["wellbeing_palace"]


def test_unknown_hour_does_not_invent_chart():
    result = calculate_mingli_foundation(dict(birth_year=2004, birth_month=6, birth_day=15, gender="female"))
    assert "hour" not in result["bazi"]
    assert "ziwei" not in result
    assert result["bazi_facts"]["dayun"] == []


def test_full_sop_coverage_is_required_for_completion():
    topics = stage_contract("S1")["topics"]
    gate = build_analysis_completion_gate(finding_statuses=["CONFIRMED"], fragment_statuses=["CONFIRMED"], required_topics=topics, confirmed_fragment_keys=[topics[0]["fragment_key"]])
    assert not gate["can_complete"]
    assert len(gate["missing_topics"]) == 13
    assert build_analysis_completion_gate(finding_statuses=[], fragment_statuses=["CONFIRMED"] * len(topics), required_topics=topics, confirmed_fragment_keys=[t["fragment_key"] for t in topics])["can_complete"]


def test_s2_knowledge_is_versioned_and_projected_for_runtime():
    spec = default_analysis_skill_specifications()[1]
    context = build_context_envelope({"profile": {}, "analysis_context": {"step_key": "S2"}}, spec)
    knowledge = context["skill_knowledge"][0]
    assert len(knowledge["ten_gods"]) == 10
    assert len(knowledge["stars"]) == 14
    assert len(stage_contract("S2")["topics"]) == 8
