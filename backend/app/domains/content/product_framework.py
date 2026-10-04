"""Versioned product requirements; symbolic analysis never creates user facts."""
from copy import deepcopy
import hashlib
import json

FRAMEWORK_VERSION = "product-analysis-2026-10-04-v2"
FRAMEWORK_SOURCE = "docs/产品分析框架.md"

# Stable analysis keys are shared with the existing 38-topic SOP.
ANALYSIS_SECTIONS = {
    "S1": [("day_master", "1.1.1"), ("structure", "1.1.2"), ("month", "1.1.3"),
           ("ten_gods", "1.1.4"), ("day_branch", "1.1.5"), ("hour", "1.1.6"),
           ("year", "1.1.7"), ("interactions", "1.1.8"), ("dayun", "1.1.9"),
           ("useful_gods", "1.1.10"), ("ziwei_life", "1.2.1"), ("ziwei_body", "1.2.2"),
           ("ziwei_wellbeing", "1.2.3"), ("ziwei_transformations", "1.2.4")],
    "S2": [("mapping", "2.1"), ("ten_gods", "2.2"), ("stars", "2.3"),
           ("persona", "2.4.1"), ("shadow", "2.4.2"), ("complex", "2.4.3"),
           ("cycle", "2.4.4"), ("authority", "2.4.5")],
    "S3": [("self", "3.1"), ("quadrant", "3.2"), ("timeline", "3.3"),
           ("yijing", "3.3"), ("bridge", "3.4"), ("integration", "3.5")],
    "S4": [("defense", "4.1.1"), ("energy", "4.1.2"), ("shadow_practice", "4.1.3"),
           ("complex_practice", "4.1.4"), ("timing_self", "4.1.5–6"), ("blocks", "4.2"),
           ("breakthrough", "4.2"), ("functions", "4.3"), ("relationships", "4.4"),
           ("experiments", "4.5")],
}


def _requirement(key, title, section, target, analysis, checks):
    return {"requirement_id": f"R.{key}", "title": title, "source_section": section,
            "target_fragment": target, "analysis_sources": analysis, "checks": checks,
            "required": True, "allow_not_applicable": False}


REPORT_REQUIREMENTS = [
    _requirement("psychic_structure", "整体心灵结构", "5.4", "report.overview.psychic_structure",
                 ["analysis.s2.persona", "analysis.s2.authority", "analysis.s2.shadow", "analysis.s3.self"],
                 ["向世界展示的我→以为的自己→潜意识层面的自己→整合后的方向", "概览暗线，不重复展开卡点"]),
    _requirement("persona", "世界看到的你", "5.4", "report.identity.outer_self", ["analysis.s2.persona"],
                 ["用户可识别的外在角色", "自述与符号解释分开"]),
    _requirement("self_belief", "眼中的自己", "5.4", "report.identity.self_perception",
                 ["analysis.s2.mapping", "analysis.s2.authority"],
                 ["意识自我与底层信念", "应该/必须/不能及权威内化", "用户自我感受、反证或待补问"]),
    _requirement("hidden_self", "隐藏的自己", "2.4、5.4", "report.identity.hidden_self",
                 ["analysis.s2.shadow", "analysis.s2.complex", "analysis.s4.defense"],
                 ["情结、阴影、防御的区别与关系", "情绪和信念假设", "保护功能与现实核对"]),
    _requirement("self_direction", "通往完整的方向", "3.1、4.1.6、5.4", "report.identity.self_direction",
                 ["analysis.s3.self", "analysis.s3.integration"], ["当前倾向的一端", "被排除的另一端", "两端整合而非完美人格"]),
    _requirement("energy", "能量与加工路径", "4.1.2、4.3、5.4", "report.identity.energy_pattern",
                 ["analysis.s4.energy", "analysis.s4.functions"], ["充电/耗电与实际反馈", "探索→价值→执行→反馈路径及张力", "无自报不推MBTI或八维分数"]),
    _requirement("relationships", "关系循环", "4.4、5.4", "report.identity.relationship_pattern",
                 ["analysis.s4.relationships"], ["请求/回应/感受/反馈循环", "真实场景或明确暂缓", "反例与待核对部分"]),
    _requirement("blocks", "核心卡点", "4.2、5.4", "report.blocks.block_*", ["analysis.s4.blocks"],
                 ["场景→触发→运作→过去保护→长期代价→整合邀请", "标准报告优先4–5项，证据不足记录理由", "本节不展开解决步骤"]),
    _requirement("common_pattern", "共性机制", "2.4.4、4.2、5.4", "report.blocks.common_pattern",
                 ["analysis.s2.cycle", "analysis.s4.blocks"], ["综合多个卡点", "触发→情绪/信念→防御→短期保护→长期重复", "不把相关性写成因果"]),
    _requirement("breakthrough", "破局推导", "4.2、5.4", "report.blocks.breakthrough", ["analysis.s4.breakthrough"],
                 ["用神/资源→调节功能→能力→现实缺口→工具→实验", "能力回应共性机制", "动作指向第三章"]),
    _requirement("archetype", "中式原型与学习资源", "3.2、5.4", "report.blocks.breakthrough", ["analysis.s3.quadrant"],
                 ["中式人物意象具象化", "可学习的能力及适用边界", "不作史实或人格诊断"]),
    _requirement("life_map", "人生阶段地图", "3.3、5.4", "report.direction.life_map",
                 ["analysis.s3.timeline", "analysis.s4.timing_self"],
                 ["真实大运起止", "原局互动依据或暂缓", "每阶段基调/放大主题/能力/旧模式", "条件式未来与积极资源"]),
    _requirement("timing_wisdom", "当下时义", "3.3、5.4", "report.direction.current_stage", ["analysis.s3.yijing"],
                 ["当下境遇与卦象比喻为何匹配", "不适用边界", "不是起卦证明"]),
    _requirement("experiments", "成长实验", "4.1.3–4、5.4", "report.direction.growth_experiments",
                 ["analysis.s4.shadow_practice", "analysis.s4.complex_practice", "analysis.s4.experiments"],
                 ["3–5项已确认Action", "对应卡点/能力/工具", "动作/频率/耗时/观察/退出", "适合现实条件"]),
    _requirement("practice_rhythm", "实践节奏", "4.5", "report.direction.growth_experiments", ["analysis.s4.experiments"],
                 ["每日能量/每周阴影/每月触发链/每季方向复盘", "可选菜单与时间不足减量"]),
    _requirement("ending", "哲学收束与寄语", "3.4、5.4", "report.ending", ["analysis.s3.bridge"],
                 ["以哲学贯通认识→理解→行动", "个性化温暖寄语", "署名引用仅用核验库，无匹配可不用"]),
]

POLICY_REQUIREMENTS = {
    "P.narrative": "三章首页关键句与概览路径；一条暗线，理解→整合→行动，避免重复完整解释。",
    "P.style": "第二人称、现实语言；按明确阅读偏好调节，不改变事实；避免模板、空泛安慰和术语堆叠。",
    "P.fidelity": "只消费已确认来源，不新增经历、心理判断或行动；问卷反馈校正符号解释。",
    "P.safety": "无诊断、无单信号强人格结论、无必然未来；保留多系统冲突及用户主体性。",
}


def framework_snapshot():
    data = {"version": FRAMEWORK_VERSION, "source": FRAMEWORK_SOURCE,
            "analysis_requirements": [
                {"requirement_id": f"A.{stage}.{key}", "stage": stage,
                 "fragment_key": f"analysis.{stage.lower()}.{key}", "source_section": section}
                for stage, topics in ANALYSIS_SECTIONS.items() for key, section in topics],
            "report_requirements": deepcopy(REPORT_REQUIREMENTS),
            "policies": deepcopy(POLICY_REQUIREMENTS)}
    data["digest"] = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return data


def validate_framework(contract):
    # Add explicitly supported frozen versions here when the product baseline evolves.
    if contract != framework_snapshot():
        raise ValueError("product_framework_version_invalid")
    return deepcopy(contract)
