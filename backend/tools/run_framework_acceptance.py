"""Real-model framework acceptance using explicitly synthetic users; no database writes."""
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domains.skills.analysis_sop import stage_contract
from app.domains.skills.bindings import specification_digest
from app.domains.skills.definitions import (
    default_analysis_skill_specifications, default_narrative_skill_specifications,
    default_validator_skill_specification,
)
from app.domains.skills.runtime import execute_skill, SkillExecutionError, DeepSeekGateway
from app.domains.skills.runtime import _validate_authoring_output, _validate_analysis_draft_output, build_context_envelope
from app.domains.content.product_framework import framework_snapshot
from app.domains.content.reasoning_contract import reasoning_snapshot, reasoning_issues
from app.domains.content.framework_coverage import report_coverage_issues, analysis_coverage_issues
from app.domains.content.report_content_plan import build_report_content_plan, validate_report_content_plan
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation
from app.domains.quality.scorecard import RUBRIC
from app.application.skill_runtime import _project_semantic_model
from app.application.report_generation import _advance_continuity

ROOT = Path(__file__).resolve().parents[2]
_PUBLICATIONS = {}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def sample_input(scenario):
    profile = dict(name=f"合成验收样本-{scenario}", gender="female", birth_year=1996,
        birth_month=6, birth_day=15, birth_hour=15, birth_minute=15, calendar_type="solar",
        birth_time_precision="exact", birth_place="山东济南", latitude=36.65, longitude=117.12,
        current_residence="杭州", occupation_status="项目运营", mbti=None,
        preferred_content_depth="深入详细")
    context = dict(analysis_date="2026-10-04", focus_topics=["personal_growth", "career", "relationships"],
        current_challenge="工作中答应额外任务后常熬夜；需要拒绝时拖到最后才生硬回应；朋友邀约也先答应后取消。",
        concrete_events=["上周同事临时请我代写方案，我本想休息却答应，熬夜后第二天不耐烦。",
                         "朋友连续两次临时改地点，我没有表达意见，最后直接取消聚会。",
                         "项目开头有许多想法，担心做不好反复修改，接近截止才急着交付。",
                         "下班后常查看消息怕漏事，独自散步时比较放松。"],
        self_description="我认为自己要靠谱、不能让人失望。拒绝后担心别人觉得我不够好。这是现在的感受，没有提供童年经历。",
        counterexample="面对熟悉同事且有明确截止时，我能够协商任务边界，并非每次都迁就。",
        available_time="工作日每晚5–10分钟，周末20分钟；不能增加大量写日记负担。",
        expected_outcomes=["理解反复出现的机制", "练习有余地的表达", "减少透支"],
        synthetic_notice="全部人物资料及经历为开发验收编写的合成数据，不是真实客户或专业评估。")
    if scenario == "caregiving_short":
        profile.update(
            name="合成验收样本-caregiving_short",
            gender="male",
            birth_year=1989,
            birth_month=11,
            birth_day=3,
            birth_hour=7,
            birth_minute=20,
            birth_place="四川成都",
            latitude=30.57,
            longitude=104.07,
            current_residence="成都",
            occupation_status="轮班物流主管，同时照顾长辈",
            mbti="ISTJ",
            preferred_content_depth="简洁清楚",
        )
        context.update(
            focus_topics=["career_transition", "family_responsibility"],
            current_challenge="轮班工作和照顾父亲挤压休息时间；想转岗，却总等到所有家庭安排都确定后才行动。",
            concrete_events=[
                "上个月想报名内部培训，担心父亲复诊时间变化，连续两周没有问清课程安排。",
                "姐姐临时请我替她陪诊，我先答应；后来和她说清轮班表后，我们改成轮流陪诊。",
                "夜班后我会继续查工作群，害怕漏掉交接；把手机交给同事保管半小时后能睡着。",
            ],
            self_description="我不觉得拒绝本身有错；事情一多时，我会先等规则和时间表更清楚。",
            counterexample="我曾与姐姐协商陪诊分工并达成轮换；不能把所有延迟都解释成讨好或害怕权威。",
            available_time="轮班工作日通常只有8分钟，休息日约25分钟；不接受每天写长日记。",
            expected_outcomes=["弄清转岗所需的下一步", "减少夜班后的消息检查", "维持可持续的家庭分工"],
        )
    if scenario == "missing_time":
        profile.pop("birth_hour")
        profile.pop("birth_minute")
        profile["birth_time_precision"] = "unknown"
    if scenario == "counterexample":
        context["self_description"] = "我不担心别人评价，答应任务是为了换取资源；不愿拒绝主要因为分工规则不清。"
        context["counterexample"] = "我曾明确拒绝领导并没有内疚。不能用命盘推断我有讨好信念或权威恐惧。"
    evidence = [{"evidence_key": f"input.{root}.{k}", "source_type": "USER_PROVIDED", "value": v}
                for root, values in (("profile", profile), ("context", context)) for k, v in values.items() if v is not None]
    foundation = calculate_mingli_foundation(profile)
    evidence.append({"evidence_key": "calculated.foundation", "source_type": "SYSTEM_CALCULATED", "value": foundation})
    return {"profile": profile, "context": context, "evidence": evidence, "foundation_data": foundation}


class CapturingGateway:
    def __init__(self):
        self.raw = None

    async def complete(self, **kwargs):
        result = await DeepSeekGateway().complete(**kwargs)
        self.raw = result.content
        return result


async def execute_saved(spec, data, path, instruction):
    signature = digest({"specification": spec, "input": data, "instruction": instruction})
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("signature") == signature:
            context = build_context_envelope(data, spec)
            try:
                if spec["processor_policy"]["processor"] == "reports.analysis_draft":
                    _validate_analysis_draft_output(cached["output"], context)
                else:
                    _validate_authoring_output(cached["output"], context, spec["processor_policy"]["processor"])
            except ValueError as error:
                index = len(list(path.parent.glob(f"{path.stem}.invalidated-*.json"))) + 1
                save(path.with_suffix(f".invalidated-{index}.json"), {**cached, "invalidated_reason": str(error)})
                print(f"{path.name} cached result rejected: {error}", flush=True)
            else:
                return cached["output"]
        else:
            raise ValueError(f"Acceptance inputs changed; use a new output directory: {path.name}")
    pinned = _PUBLICATIONS.get(spec["identity"]["skill_key"]) or {}
    skill = SimpleNamespace(id=pinned.get("id", 0), version=pinned.get("version", 1),
        skill_key=spec["identity"]["skill_key"], specification_json=spec)
    previous_failures = list(path.parent.glob(f"{path.stem}.attempt-*.failure.json"))
    compact_instruction = "\n保持完整JSON并控制输出长度：summary不超过120字，Finding.claim每条40–100字，每个analysis片段content约150–250字，structured_analysis.details每个字段约25–60字；只有reasoning_contract列出的片段返回structured_analysis，其余不添加。只引用必要Evidence，不复制上游整段分析。quote只能逐字摘录同一对象刚生成的content中连续的一句话（10–40字），不能摘录未在本正文出现的问卷/上游/details。不要省掉规定片段或行动字段。"
    repair = compact_instruction if previous_failures else ""
    offset = max((int(p.name.split(".attempt-")[1].split(".")[0]) for p in previous_failures), default=0)
    for attempt in range(1, 3):
        gateway = CapturingGateway()
        try:
            result = await execute_skill(skill_version=skill, input_data=data,
                runtime_instruction=instruction + repair, gateway=gateway)
        except SkillExecutionError as error:
            save(path.with_suffix(f".attempt-{offset + attempt}.failure.json"), {
                "error": str(error), "trace": error.model_trace, "unvalidated_output": gateway.raw,
                "runtime_instruction": instruction + repair,
                "signature": signature})
            print(f"{path.name} attempt {attempt} failed: {error}", flush=True)
            if gateway.raw is None or attempt == 2:
                raise
            repair = compact_instruction + f"\n上一轮输出未通过程序校验：{error}。请重新生成完整JSON。reasoning_path.resource_refs只能引用指定角色资源，不能用PERSONA代替。"
            continue
        save(path, {"signature": signature, "skill_digest": specification_digest(spec),
            "runtime_instruction": instruction + repair,
            "output": result.output_parsed, "trace": result.model_trace,
            "review": "TECHNICAL_ACCEPTANCE_FOR_SYNTHETIC_SAMPLE; consultant review pending"})
        return result.output_parsed


async def published_specifications():
    """Read and freeze actual publications; never change a production record."""
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal, engine
    from app.domains.skills.models import AISkillVersion
    engine.echo = False
    defaults = [*default_analysis_skill_specifications(), *default_narrative_skill_specifications(), default_validator_skill_specification()]
    specs = []
    async with AsyncSessionLocal() as db:
        for default in defaults:
            key = default["identity"]["skill_key"]
            row = await db.scalar(select(AISkillVersion).where(
                AISkillVersion.skill_key == key, AISkillVersion.status == "PUBLISHED"
            ).order_by(AISkillVersion.version.desc()).limit(1))
            if row is None:
                raise ValueError(f"Published skill missing: {key}")
            spec = deepcopy(row.specification_json)
            _PUBLICATIONS[key] = {"id": row.id, "version": row.version,
                "specification_digest": specification_digest(row.specification_json)}
            specs.append(spec)
    await engine.dispose()
    return specs


async def run(output, scenario, *, published=False, analysis_date=None):
    case = sample_input(scenario)
    if analysis_date:
        case["context"]["analysis_date"] = analysis_date
        for evidence in case["evidence"]:
            if evidence["evidence_key"] == "input.context.analysis_date":
                evidence["value"] = analysis_date
    current_specs = (await published_specifications() if published else
        [*default_analysis_skill_specifications(), *default_narrative_skill_specifications(), default_validator_skill_specification()])
    manifest_path = output / "manifest.json"
    manifest = {"notice": "真实模型＋合成用户；本地技术验收，无生产写入，无客户交付，待咨询师审核。",
        "skill_source": "LATEST_PUBLISHED_DATABASE_SNAPSHOT" if published else "CODE_DEFAULTS",
        "framework_contract": framework_snapshot(), "reasoning_contract": reasoning_snapshot(),
        "input_digest": digest(case), "skills": {s["identity"]["skill_key"]: {
            "digest": specification_digest(s), "specification": s,
            "publication": _PUBLICATIONS.get(s["identity"]["skill_key"])} for s in current_specs}}
    if manifest_path.exists():
        frozen = json.loads(manifest_path.read_text(encoding="utf-8"))
        if frozen["input_digest"] != manifest["input_digest"]:
            raise ValueError("Acceptance input changed; use a new output directory")
        manifest = frozen
    else:
        save(manifest_path, manifest)
    _PUBLICATIONS.update({key: value.get("publication") or {} for key, value in manifest["skills"].items()})
    specs = {k: v["specification"] for k, v in manifest["skills"].items()}
    save(output / "input.json", case)
    model = {"findings": [], "analysis_fragments": [], "evidence": case["evidence"],
        "framework_contract": manifest["framework_contract"], "reasoning_contract": manifest["reasoning_contract"]}
    instruction = "全部资料为合成验收数据。不得冒充真实客户；未给出的经历不可补造。心理假设必须接受自述和反证校正。只用已提供依据。"
    for stage in ("S1", "S2", "S3", "S4"):
        spec = next(s for s in specs.values() if s["instructions"].get("stage_key") == stage)
        context = {"step_key": stage, "sop_contract": stage_contract(stage),
            "framework_contract": model["framework_contract"], "reasoning_contract": model["reasoning_contract"],
            "evidence": case["evidence"], "upstream_confirmed_findings": deepcopy(model["findings"]),
            "upstream_confirmed_analysis_fragments": deepcopy(model["analysis_fragments"])}
        result = await execute_saved(spec, {"profile": case["profile"], "context": case["context"],
            "analysis_context": context, "foundation_data": case["foundation_data"] if stage == "S1" else None},
            output / f"{stage}.json", instruction + "每个规定分析片段都须有framework_coverage；structured_analysis/details严格使用当前reasoning_contract字段。Action的reasoning_path逐项具体，不用通用空话。")
        model["findings"].extend(result["findings"])
        for f in result["analysis_fragments"]:
            model["analysis_fragments"].append({**f, "source_snapshot": {
                "findings": [{"finding_key": k} for k in f["finding_refs"]],
                "evidence": [{"evidence_key": k} for k in f["evidence_refs"]],
                "framework_coverage": f.get("framework_coverage"), "structured_analysis": f.get("structured_analysis")}})
        print(f"{scenario} {stage}: {len(result['findings'])} findings, {len(result['analysis_fragments'])} analyses", flush=True)
    issues = analysis_coverage_issues(model["framework_contract"], model["analysis_fragments"]) + reasoning_issues(model)
    save(output / "analysis-validation.json", {"issues": issues})
    if issues:
        raise ValueError(f"Analysis blocked: {issues}")
    candidates = await execute_saved(specs["report.narrative_plan"], {"profile": case["profile"],
        "context": {**case["context"], "semantic_model": model}}, output / "S5-candidates.json", instruction + "只用已确认BLOCK，不新增卡点。INTERNAL_ONLY仅为推导依据，不选为核心结论。")
    candidate = candidates["candidates"][0]
    plan = {"core_theme": candidate["theme"], "must_include_findings": candidate["supporting_findings"],
        "priority_blocks": candidate["priority_blocks"], "narrative_arc": candidate["narrative_arc"],
        "reader_profile": {"theory_density": "medium", "action_density": "high", "metaphor_density": "low"}}
    content_plan = build_report_content_plan(model, plan, user_context=case["context"])
    issues = validate_report_content_plan(content_plan, model, plan)
    save(output / "S5-plan.json", {"plan": plan, "content_plan": content_plan, "issues": issues})
    if any(i.get("severity") == "BLOCK" for i in issues):
        raise ValueError(f"Content plan blocked: {issues}")
    authored, continuity = [], {}
    for spec in content_plan["fragments"]:
        result = await execute_saved(specs["report.fragment_authoring"], {"profile": case["profile"], "context": {
            **case["context"], "semantic_model": _project_semantic_model(model, spec), "narrative_plan": plan,
            "fragment_request": {"fragment_key": spec["fragment_key"], "title": spec["purpose"]},
            "fragment_allocation": spec, "continuity": continuity}},
            output / "fragments" / f"{spec['sequence_no']:02d}-{spec['fragment_key']}.json",
            instruction + "每段通常300–600汉字，阶段地图/实验可适当加长。全部分配analysis_refs和required_finding_refs须实际使用。requirement_coverage逐项返回，不用一句空泛摘要宣称完成。暂缓内容须有具体可回答补问。")
        if result["status"] != "READY_FOR_REVIEW":
            raise ValueError(f"Fragment needs source revision: {spec['fragment_key']}")
        authored.append({**result, "fragment_key": spec["fragment_key"], "chapter": spec["chapter"], "source_snapshot": {
            "findings": [{"finding_key": k} for k in result["used_findings"]],
            "fragments": [{"fragment_key": k} for k in result.get("used_analysis_fragments", [])],
            "requirement_coverage": result.get("requirement_coverage")}})
        continuity = _advance_continuity(continuity, spec, result)
        print(f"{scenario} S5: {spec['sequence_no']}/{len(content_plan['fragments'])}", flush=True)
    issues = report_coverage_issues(content_plan, authored)
    save(output / "report-validation.json", {"issues": issues})
    save(output / "S5-report.json", {"fragments": authored})
    (output / "report.md").write_text("\n\n".join([
        "# 产品框架真实模型验收报告", "> 合成用户样稿，非真实客户；待咨询师审核，不可交付。",
        *[f"## {f['title']}\n\n{f['content']}" for f in authored]]) + "\n", encoding="utf-8")
    if issues:
        raise ValueError(f"Report coverage blocked: {issues}")
    qa = {"framework_contract": model["framework_contract"], "scorecard_required": True, "scoring_rubric": RUBRIC,
        "application_context": {"profile": case["profile"], "context": case["context"]}, "confirmed_semantics": model,
        "narrative_plan": plan, "content_plan": content_plan,
        "validation_scope": ["source_fidelity", "report_coherence", "repetition", "block_to_action_link", "safety"],
        "report_fragments": [{k: f[k] for k in ("fragment_key", "title", "content")} for f in authored]}
    review = await execute_saved(specs["report.final_validator"], {"profile": {"name": case["profile"]["name"]},
        "context": {"qa_input": qa}}, output / "S6.json", instruction + "独立严审16项内容职责。framework_review每项fragment_keys必须列出content_plan中全部归属（卡点要求包括所有卡点），quote必须是其中某段的逐字摘录。结构齐全不等于语义成立。")
    save(output / "summary.json", {"scenario": scenario, "analysis_count": len(model["analysis_fragments"]),
        "report_count": len(authored), "framework_review": review["framework_review"],
        "scorecard": review["scorecard"], "issues": review["issues"], "consultant_review": "PENDING"})
    print(f"{scenario} S6: score={review['scorecard']['total']}, issues={len(review['issues'])}", flush=True)


async def repair_report(output, scenario, round_no):
    """Draft local, source-limited repairs; original report and QA are never overwritten."""
    source = output if round_no == 1 else output / "repairs" / f"round-{round_no - 1}"
    destination = output / "repairs" / f"round-{round_no}"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    _PUBLICATIONS.update({key: value.get("publication") or {} for key, value in manifest["skills"].items()})
    case = json.loads((output / "input.json").read_text(encoding="utf-8"))
    specs = {k: v["specification"] for k, v in manifest["skills"].items()}
    model = {"findings": [], "analysis_fragments": [], "evidence": case["evidence"],
             "framework_contract": manifest["framework_contract"], "reasoning_contract": manifest["reasoning_contract"]}
    for stage in ("S1", "S2", "S3", "S4"):
        result = json.loads((output / f"{stage}.json").read_text(encoding="utf-8"))["output"]
        model["findings"].extend(result["findings"])
        for f in result["analysis_fragments"]:
            model["analysis_fragments"].append({**f, "source_snapshot": {
                "findings": [{"finding_key": k} for k in f["finding_refs"]],
                "evidence": [{"evidence_key": k} for k in f["evidence_refs"]],
                "framework_coverage": f.get("framework_coverage"), "structured_analysis": f.get("structured_analysis")}})
    plan_record = json.loads((output / "S5-plan.json").read_text(encoding="utf-8"))
    plan, content_plan = plan_record["plan"], plan_record["content_plan"]
    original = json.loads((source / "S5-report.json").read_text(encoding="utf-8"))["fragments"]
    qa_record = json.loads((source / "S6.json").read_text(encoding="utf-8"))["output"]
    by_key = {f["fragment_key"]: f for f in original}
    targets = {}
    for issue in qa_record["issues"]:
        key = issue.get("target_fragment_key")
        if key in by_key:
            targets.setdefault(key, []).append(issue)
    if round_no == 3 and any(i.get("issue_type") == "repetition" for i in qa_record["issues"]):
        # Cross-section repetition cannot be repaired solely at the validator's single locator.
        for fragment in original:
            key = fragment["fragment_key"]
            if key != "report.direction.growth_experiments":
                targets.setdefault(key, []).append({"issue_type": "editorial_scope", "severity": "MINOR",
                    "message": "跨节去重：保留本节独有内容，不再重述完整承诺—透支—撤退链或同一反例。",
                    "suggestion": "完整场景机制留卡点，共性节只综合差异；其他节各完成其职责。"})
    authored, continuity = [], {}
    for index, allocation in enumerate(content_plan["fragments"]):
        key = allocation["fragment_key"]
        current = by_key[key]
        if key in targets:
            data = {"profile": case["profile"], "context": {**case["context"],
                "semantic_model": _project_semantic_model(model, allocation), "narrative_plan": plan,
                "fragment_request": {"fragment_key": key, "title": current["title"],
                    "current_content": current["content"], "review_issues": targets[key],
                    "next_fragment": content_plan["fragments"][index + 1]["purpose"] if index + 1 < len(content_plan["fragments"]) else None},
                "fragment_allocation": allocation, "continuity": continuity}}
            instruction = (
                "修订合成用户验收样稿，只修当前小节，不改变上游已确认语义、Action动作/频率/耗时。"
                "独立核对review_issues：用户明确自述（例如散步放松）仍作为自述事实；新增的因果解释才是假设，不将事实降格。"
                "假设在介绍时清楚限定，后续承接保留条件与反证，避免保护功能成为断言。无家庭资料不补造。"
                "正文不重复完整触发链，概览约250–400字只概览四层，机制展开留卡点；其他节约300–600字。"
                "不在每节预告卡点，不写与实际顺序错误的‘下一节’。原型须有可学习能力及适用边界。"
                "实验工具须逐项指向实际卡点，保留已确认Action的全部条件，再说明时间预算与减量菜单。"
                "用神/符号的能力转译须明确为解释视角，行动取舍以现实自述和反馈为依据。"
                "只用当前分配来源，全部analysis_refs/action_refs/required_finding_refs实际使用并记入输出；"
                "requirement_coverage逐项如实声明，quote从本输出content逐字连续摘录。不要为提高评分删核心内容。"
            )
            if round_no == 3:
                instruction += (
                    "本轮必须执行编辑职责分工，不复制旧稿：概览只给4层各一句和主线，共150–250字，绝不写完整触发链、保护与代价。"
                    "外在自我只讲可识别的外在角色；自我信念只讲意识自我与现实规则核对，保留一个可回答反证问题。"
                    "隐藏自我只解释情结/阴影/防御区别与关系，不重述完整事件链；能量只讲充耗电与加工路径；"
                    "关系节只讲朋友改约这一关系场景及请求—回应—感受—反馈，不重复同事临时任务。"
                    "卡点各讲一个不同具体情境的机制、保护、代价与邀请，完整工作请求故事只在相应卡点节。"
                    "共性节综合多个不同卡点之间的规则优先于需要，不复述各节故事。"
                    "同一反例完整表述只出现一次；其他必要处用‘前文的反例’承接。符号能力转译每次明确为比喻性解释。"
                    "命盘旁注约350–550字，保留结构、分歧、时辰边界与资料限制，把详细心理解释留后文。"
                    "时序地图按当前/近两期/远期分别成段或表，保留所有已确认年份和各阶段字段，条件式观察而非事件预测。"
                    "原型用一句说明人物意象的学习能力和适用边界，不把历史人物当诊断标签。"
                    "结尾约120–200字，不重述循环或动作；其他章节通常250–450字，不反复预告下一节。"
                )
            result = await execute_saved(specs["report.fragment_authoring"], data,
                destination / "fragments" / f"{allocation['sequence_no']:02d}-{key}.json", instruction)
            if result["status"] != "READY_FOR_REVIEW":
                raise ValueError(f"Repair needs source revision: {key}")
            current = {**result, "fragment_key": key, "chapter": allocation["chapter"], "source_snapshot": {
                "findings": [{"finding_key": k} for k in result["used_findings"]],
                "fragments": [{"fragment_key": k} for k in result.get("used_analysis_fragments", [])],
                "requirement_coverage": result.get("requirement_coverage")}}
            print(f"{scenario} repair {round_no}: {key}", flush=True)
        authored.append(current)
        continuity = _advance_continuity(continuity, allocation, current)
    issues = report_coverage_issues(content_plan, authored)
    save(destination / "report-validation.json", {"issues": issues})
    save(destination / "S5-report.json", {"fragments": authored})
    (destination / "report.md").write_text("\n\n".join([
        "# 产品框架真实模型验收修订稿", "> 合成用户样稿，待咨询师审核，不可交付。",
        *[f"## {f['title']}\n\n{f['content']}" for f in authored]]) + "\n", encoding="utf-8")
    if issues:
        raise ValueError(f"Repair coverage blocked: {issues}")
    # The validator is pinned to the original specification, plus explicit calibration notes.
    qa = {"framework_contract": model["framework_contract"], "scorecard_required": True, "scoring_rubric": RUBRIC,
        "application_context": {"profile": case["profile"], "context": case["context"]}, "confirmed_semantics": model,
        "narrative_plan": plan, "content_plan": content_plan,
        "validation_scope": ["source_fidelity", "report_coherence", "repetition", "block_to_action_link", "safety"],
        "report_fragments": [{k: f[k] for k in ("fragment_key", "title", "content")} for f in authored]}
    review = await execute_saved(specs["report.final_validator"], {"profile": {"name": case["profile"]["name"]},
        "context": {"qa_input": qa}}, destination / "S6.json",
        "独立审核修订稿，不因已修订而加分。framework_review全16项，fragment_keys须全部归属，quote在正文中。"
        "明确区分原始自述与解释：用户说散步放松，可陈述为自我观察，不因为资源Finding是假设而否定它。"
        "明确的可能/或许/假如加上边界或反证是有效限定，不要求每句叠加‘假设可能’。"
        "不要把明确否定确定论的句子误读为确定论。引用可识别且准确的出处即可，不要求正文暴露核验流程。"
        "不同章节完成不同内容职责的必要呼应不等于完整重复：概览简述、卡点具体事件、关系反馈及共性综合需分开判断。只有同一场景、保护和代价再次完整展开才报重复；不能仅凭同一关键词出现扣分。"
        "只报实际越过来源的断言、缺内容、冲突、重复或行动错配；若仍存在这些缺陷按真实程度扣分。")
    save(destination / "summary.json", {"scenario": scenario, "round": round_no,
        "analysis_count": len(model["analysis_fragments"]), "report_count": len(authored),
        "scorecard": review["scorecard"], "framework_review": review["framework_review"],
        "issues": review["issues"], "consultant_review": "PENDING"})
    print(f"{scenario} repair {round_no} S6: score={review['scorecard']['total']}, issues={len(review['issues'])}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=["full", "missing_time", "counterexample", "caregiving_short"],
        default="full",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repair", type=int, choices=[1, 2, 3])
    parser.add_argument("--published-skills", action="store_true")
    parser.add_argument("--analysis-date")
    args = parser.parse_args()
    asyncio.run(repair_report(args.output.resolve(), args.scenario, args.repair) if args.repair else
        run(args.output.resolve(), args.scenario, published=args.published_skills, analysis_date=args.analysis_date))
