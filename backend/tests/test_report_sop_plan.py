from app.domains.content.report_content_plan import build_report_content_plan
from app.domains.content.report_content_plan import _contains, _ACTION_ROLE_TOKENS


def test_interaction_is_not_an_action_and_does_not_displace_an_experiment():
    assert not _contains("INTERACTION_TENSION", _ACTION_ROLE_TOKENS)
    assert _contains("ACTION_EXPERIMENT", _ACTION_ROLE_TOKENS)


def test_sop_routes_timeline_and_actions_to_direction_instead_of_identity():
    findings = [{"finding_key": key, "claim": key, "semantic_role": role, "importance": "HIGH", "reportability": "RECOMMENDED", "evidence_refs": ["questionnaire"]} for key, role in [("s1.foundation", "PERSONA"), ("block.1", "BLOCK"), ("block.2", "BLOCK"), ("direction.1", "STAGE_THEME"), ("action.1", "ACTION")]]
    analyses = [{"fragment_key": key, "source_snapshot": {"evidence": [{"evidence_key": "questionnaire"}]}} for key in ["analysis.s1.day_master", "analysis.s3.timeline", "analysis.s4.experiments"]]
    plan = build_report_content_plan({"findings": findings, "analysis_fragments": analyses}, {"must_include_findings": ["block.1"]})
    assert plan["status"] == "READY"
    specs = {s["fragment_key"]: s for s in plan["fragments"]}
    assert "analysis.s3.timeline" in specs["report.direction.life_map"]["analysis_refs"]
    assert "analysis.s4.experiments" in specs["report.direction.growth_experiments"]["analysis_refs"]
    assert "analysis.s1.day_master" in specs["report.identity.foundation_notes"]["analysis_refs"]
    assert "过去保护了什么" in specs["report.blocks.block_01"]["must_cover"]
