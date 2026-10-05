"""Real-model local acceptance; no writes to the production database or delivery.

Run one step, inspect the saved output, then explicitly approve it for the demo:
  .venv/Scripts/python.exe tools/run_qingniao_acceptance.py --step S1
  .venv/Scripts/python.exe tools/run_qingniao_acceptance.py --approve S1
Approval records are technical acceptance by the developer, not a human consultation.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domains.skills.analysis_sop import stage_contract
from app.domains.skills.definitions import default_analysis_skill_specifications, default_narrative_skill_specifications, default_validator_skill_specification
from app.domains.skills.runtime import execute_skill, SkillExecutionError, DeepSeekGateway
from app.domains.skills.builtin_examples import EXAMPLES
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation
from app.domains.content.report_content_plan import build_report_content_plan, validate_report_content_plan
from app.application.skill_runtime import _project_semantic_model
from app.application.report_generation import _advance_continuity
from app.domains.quality.scorecard import RUBRIC

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "acceptance" / "qingniao"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_input():
    source_path = ROOT / "docs" / "青鸟基本信息.txt"
    if source_path.exists():
        source = source_path.read_text(encoding="utf-8")
    else:
        saved_input = OUTPUT / "input.json"
        saved_case = json.loads(saved_input.read_text(encoding="utf-8"))
        source = (saved_case.get("context") or {}).get("source_questionnaire")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("qingniao_questionnaire_source_missing")
    assumptions = ["出生日期假设为公历2004-06-15（仅演示，与22岁一致，待本人提供）", "出生城市假设为山东济南；居住城市未补造，仍记录江苏", "分析日期为2026-10-04；未补造家庭、关系或心理经历"]
    profile = dict(name="青鸟", gender="female", birth_year=2004, birth_month=6, birth_day=15, birth_hour=15, birth_minute=15, calendar_type="solar", birth_time_precision="exact", birth_place="山东济南（演示假设）", latitude=36.65, longitude=117.12, current_residence="江苏", occupation_status="全职会计", highest_education="本科", marital_status="单身", mbti="ENFP（自报，未测八维）", personality_keywords=["无知的乐观主义", "权衡利弊", "急迫"], strengths="愿意听别人对自身性格的建议", limitations="太着急", preferred_content_depth="深入详细", demo_assumptions=assumptions)
    context = dict(focus_topics=["personal_growth", "relationships", "career"], current_challenge="不太会拒绝，拒绝时语言生硬，习惯迁就；有事才联系朋友，关系逐渐疏远", issue_duration="感觉一直存在", impact_level="有些影响", decision_status="no", decision_style=["直觉", "咨询家人朋友"], expected_outcomes=["解决当前问题", "验证已有判断", "方向性指引", "认识自己"], usage_scenario="每天晚上复盘；遇到困惑时查询", additional_info="每次困境会有女贵人出现（用户自述）", source_questionnaire=source, analysis_date="2026-10-04", demo_assumptions=assumptions)
    evidence = [{"evidence_key": f"input.profile.{k}", "source_type": "DEMO_ASSUMPTION" if k in {"birth_year", "birth_month", "birth_day", "birth_place", "latitude", "longitude", "demo_assumptions"} else "USER_PROVIDED", "value": v} for k, v in profile.items()]
    evidence += [{"evidence_key": f"input.context.{k}", "source_type": "USER_PROVIDED", "value": v} for k, v in context.items()]
    foundation = calculate_mingli_foundation(profile)
    evidence.append({"evidence_key": "calculated.mingli_foundation.v2", "source_type": "SYSTEM_CALCULATED", "value": foundation})
    return {"profile": profile, "context": context, "evidence": evidence, "foundation_data": foundation}


async def run(step):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    case = load_input()
    save(OUTPUT / "input.json", case)
    findings, fragments = [], []
    for key in ("S1", "S2", "S3", "S4"):
        if key == step:
            break
        prior = json.loads((OUTPUT / f"{key}.json").read_text(encoding="utf-8"))
        if prior.get("review", {}).get("status") != "DEVELOPER_ACCEPTED_FOR_DEMO":
            raise ValueError(f"Review and --approve {key} first")
        findings.extend(prior["output"]["findings"])
        fragments.extend(prior["output"]["analysis_fragments"])
    spec = next(s for s in default_analysis_skill_specifications() if s["instructions"]["stage_key"] == step)
    skill = SimpleNamespace(id=0, version=1, skill_key=spec["identity"]["skill_key"], specification_json=spec)
    example = EXAMPLES.get(skill.skill_key)
    examples = [{"example_type": "POSITIVE", "input_context": example[1], "expected_output": example[2], "teaching_points": example[3]}] if example else []
    analysis_context = {"step_key": step, "sop_contract": stage_contract(step), "evidence": case["evidence"], "upstream_confirmed_findings": findings, "upstream_confirmed_analysis_fragments": fragments}
    data = {"profile": case["profile"], "context": case["context"], "analysis_context": analysis_context, "foundation_data": case["foundation_data"] if step == "S1" else None, "few_shot_examples": examples}
    try:
        result = await execute_skill(skill_version=skill, input_data=data, runtime_instruction="这是开发者验收演示。出生日期/城市为假设，命理解读必须条件化且不得冒充用户真实命盘；心理分析只用真实问卷。分析日期2026-10-04。每个规定分析片段至少给出具体分析或明确暂缓依据。")
    except SkillExecutionError as error:
        save(OUTPUT / f"{step}-failure.json", {"error": str(error), "trace": error.model_trace})
        raise
    record = {"step": step, "skill_key": skill.skill_key, "specification": spec, "output": result.output_parsed, "trace": result.model_trace, "review": {"status": "AWAITING_DEVELOPER_REVIEW", "note": "非真实咨询师人工审核；未交付到客户账号"}}
    save(OUTPUT / f"{step}.json", record)
    (OUTPUT / f"{step}.md").write_text("\n\n".join([f"# {step} 分析验收候选", result.output_parsed["summary"], *[f'## {f["title"]}\n\n{f["content"]}' for f in result.output_parsed["analysis_fragments"]]]), encoding="utf-8")
    print(f'{step}: valid schema and coverage; {len(result.output_parsed["findings"])} findings, {len(result.output_parsed["analysis_fragments"])} fragments; saved {OUTPUT}')


def approved_semantics():
    case = load_input()
    model = {"findings": [], "analysis_fragments": [], "evidence": case["evidence"]}
    for step in ("S1", "S2", "S3", "S4"):
        record = json.loads((OUTPUT / f"{step}.json").read_text(encoding="utf-8"))
        if record.get("review", {}).get("status") != "DEVELOPER_ACCEPTED_FOR_DEMO":
            raise ValueError(f"Review {step} first")
        model["findings"].extend(record["output"]["findings"])
        for fragment in record["output"]["analysis_fragments"]:
            fragment = {**fragment, "source_snapshot": {"findings": [{"finding_key": k} for k in fragment["finding_refs"]], "evidence": [{"evidence_key": k} for k in fragment["evidence_refs"]]}}
            model["analysis_fragments"].append(fragment)
        (OUTPUT / f"{step}.md").write_text("\n\n".join([f"# {step} 开发验收分析", record["output"]["summary"], *[f'## {f["title"]}\n\n{f["content"]}' for f in record["output"]["analysis_fragments"]]]), encoding="utf-8")
    return case, model


async def execute_to_file(spec, data, path, instruction):
    skill = SimpleNamespace(id=0, version=1, skill_key=spec["identity"]["skill_key"], specification_json=spec)
    example = EXAMPLES.get(skill.skill_key)
    if example:
        data["few_shot_examples"] = [{"example_type": "POSITIVE", "input_context": example[1], "expected_output": example[2], "teaching_points": example[3]}]
    class CapturingGateway:
        async def complete(self, **kwargs):
            completion = await DeepSeekGateway().complete(**kwargs)
            self.completion = completion
            return completion
    gateway = CapturingGateway()
    try:
        result = await execute_skill(skill_version=skill, input_data=data, runtime_instruction=instruction, gateway=gateway)
    except SkillExecutionError as error:
        save(path.with_suffix(".failure.json"), {"error": str(error), "trace": error.model_trace, "unvalidated_output": getattr(getattr(gateway, "completion", None), "content", None)})
        raise
    record = {"skill_key": skill.skill_key, "output": result.output_parsed, "trace": result.model_trace, "review": {"status": "AWAITING_DEVELOPER_REVIEW"}}
    save(path, record)
    return record["output"]


async def write_report():
    case, model = approved_semantics()
    specs = default_narrative_skill_specifications()
    candidate_path = OUTPUT / "S5-candidates.json"
    if not candidate_path.exists():
        await execute_to_file(specs[0], {"profile": case["profile"], "context": {**case["context"], "semantic_model": model}}, candidate_path, "演示出生数据条件化；优先处理用户明确提出的拒绝、友谊维系和急迫。四项卡点必须使用S4已审核的卡点，不再扩充。")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))["output"]["candidates"][0]
    block_keys = {f["finding_key"] for f in model["findings"] if f["semantic_role"] == "BLOCK"}
    candidate["priority_blocks"] = [b for b in candidate["priority_blocks"] if block_keys.intersection(b["finding_refs"])]
    plan = {"version": 1, "core_theme": candidate["theme"], "selected_candidate": candidate["candidate_key"], "priority_blocks": candidate["priority_blocks"], "must_include_findings": candidate["supporting_findings"], "narrative_arc": candidate["narrative_arc"], "reader_profile": {"theory_density": "medium", "action_density": "high", "metaphor_density": "low"}}
    content_plan = build_report_content_plan(model, plan, user_context=case["context"])
    issues = validate_report_content_plan(content_plan, model, plan)
    save(OUTPUT / "S5-plan.json", {"plan": plan, "content_plan": content_plan, "programmatic_issues": issues, "review": "Developer selected first supported candidate for demo; not consultant approval"})
    if content_plan["status"] != "READY" or any(i["severity"] == "BLOCK" for i in issues):
        raise ValueError(f"Content plan blocked: {issues}")
    continuity, authored = {}, []
    fragment_dir = OUTPUT / "fragments"
    fragment_dir.mkdir(exist_ok=True)
    for allocation in content_plan["fragments"]:
        path = fragment_dir / f'{allocation["sequence_no"]:02d}-{allocation["fragment_key"]}.json'
        if path.exists():
            output = json.loads(path.read_text(encoding="utf-8"))["output"]
        else:
            data = {"profile": case["profile"], "context": {**case["context"], "semantic_model": _project_semantic_model(model, allocation), "narrative_plan": plan, "fragment_request": {"fragment_key": allocation["fragment_key"], "title": allocation["fragment_key"].rsplit(".", 1)[-1]}, "fragment_allocation": allocation, "continuity": continuity}}
            output = await execute_to_file(specs[1], data, path, "为青鸟写深入但紧凑的单个小节：通常250–500汉字，命盘旁注、阶段地图和实验可适当加长。四项卡点各只讲不同机制。用户想每天复盘，不代表已经有该习惯。未自述的感受/自动想法必须用‘可能、可以核对’。生日2004-06-15/济南只是演示假设，所有命盘/大运内容只能条件式。保留数据边界。不要复述内部来源编号。")
        if output["status"] != "READY_FOR_REVIEW":
            raise ValueError(f'Missing source for {allocation["fragment_key"]}')
        authored.append({"fragment_key": allocation["fragment_key"], "chapter": allocation["chapter"], **output})
        continuity = _advance_continuity(continuity, allocation, output)
        print(f'S5 {allocation["sequence_no"]}/{len(content_plan["fragments"])}: {output["title"]}', flush=True)
    save(OUTPUT / "S5-report.json", {"fragments": authored, "review": {"status": "AWAITING_DEVELOPER_REVIEW"}})
    render_report(authored)


def render_report(fragments):
    text = ["# 青鸟的人生说明书｜在连接中站稳自己", "> 演示报告，基于真实问卷；出生日期暂补为2004年6月15日，出生城市暂补为济南。所有命理和阶段地图均以该假设为前提，收到真实生日后需重新计算、分析和审核。开发验收不等同真实咨询师签字。", "22岁｜女性｜本科｜全职会计｜江苏｜自报ENFP。你关注个人成长、朋友关系和事业，希望获得详细逻辑、可实践的方法与方向。"]
    chapter = None
    for f in fragments:
        if f["chapter"] != chapter:
            chapter = f["chapter"]
            text.append({"identity": "# 第一章 · 你是谁", "challenge": "# 第二章 · 卡在哪", "direction": "# 第三章 · 往哪去"}.get(chapter, "# 寄语"))
        text.append(f'## {f["title"]}\n\n{f["content"]}')
    (OUTPUT / "report.md").write_text("\n\n".join(text) + "\n", encoding="utf-8")


async def validate_report():
    case, model = approved_semantics()
    report = json.loads((OUTPUT / "S5-report.json").read_text(encoding="utf-8"))
    plan = json.loads((OUTPUT / "S5-plan.json").read_text(encoding="utf-8"))
    reader_fragments = [{k: f[k] for k in ("fragment_key", "title", "content")} for f in report["fragments"]]
    qa = {"scorecard_required": True, "scoring_rubric": RUBRIC, "application_context": {"profile": case["profile"], "context": case["context"]}, "confirmed_semantics": model, "narrative_plan": plan["plan"], "content_plan": plan["content_plan"], "validation_scope": ["source_fidelity", "chapter_coherence", "report_coherence", "repetition", "block_to_action_link", "safety"], "report_fragments": reader_fragments}
    result = await execute_to_file(default_validator_skill_specification(), {"profile": {"name": "青鸟"}, "context": {"qa_input": qa}}, OUTPUT / "S6.json", "独立审核完整演示报告，严格评分，不因开发演示降低标准。区分不同小节的深化与三次以上重复展开。假设生日须条件化，未自述的心理机制须为假设。只输出明确可修复且有证据的问题。")
    print(f'S6 score={result["scorecard"]["total"]}; issues={len(result["issues"])}; threshold={result["scorecard"]["passes_threshold"]}', flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["S1", "S2", "S3", "S4", "S5", "S6"])
    parser.add_argument("--approve", choices=["S1", "S2", "S3", "S4"])
    args = parser.parse_args()
    if args.approve:
        path = OUTPUT / f"{args.approve}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["review"] = {"status": "DEVELOPER_ACCEPTED_FOR_DEMO", "note": "开发者核查演示覆盖/来源/边界，非真实咨询师审核，不写入生产或对客户交付"}
        save(path, record)
        print(f"{args.approve} developer acceptance recorded")
    elif args.step:
        asyncio.run(write_report() if args.step == "S5" else validate_report() if args.step == "S6" else run(args.step))
    else:
        parser.error("Choose --step or --approve")
