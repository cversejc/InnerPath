"""Versioned analytical coverage used by skills and workflow completion gates."""
SOP_VERSION = "product-analysis-2026-10-04-v1"

SOP_STAGES = {
    "S1": {
        "program": "lunar-python 计算节气四柱、藏干十神、干支关系与起运；项目紫微算法计算星曜和四化。次数不等于旺衰。",
        "ai": "逐项解释结构和待验证心理线索，判断格局与喜忌，列出反证及流派分歧。",
        "human": "核对历法/时区/时刻/地点、确认格局喜忌；按问卷决定调用其他宫位；审核全部条目。",
        "topics": [
            ("day_master", "1.1.1 日主", "日干、五行、阴阳、意象及待验证的自我核心线索。"),
            ("structure", "1.1.2 格局", "月令与全局生扶/克泄耗依据；身强弱、从格、化格候选及反证，不用出现次数代替旺衰。"),
            ("month", "1.1.3 月令", "月支、生克、本气及藏干十神、气候基调与待验证世界观。"),
            ("ten_gods", "1.1.4 十神", "透干/藏干、旺衰/缺失及十神交战，显隐资源；缺失不能证明人格缺陷。"),
            ("day_branch", "1.1.5 日支", "日支与日干生克、藏干十神、内在需求线索。"),
            ("hour", "1.1.6 时支", "时支五行/十神与价值排序；时间未知明确暂缓。"),
            ("year", "1.1.7 年柱", "年干支十神、集体印记和内在权威线索，不编造家庭经历。"),
            ("interactions", "1.1.8 刑冲合害", "六冲/三刑/自刑/六合/三合/三会/六害及干合克；合与合化分开，列出心理冲突线索。"),
            ("dayun", "1.1.9 大运", "按分析日期选择当前运，干支十神/五行及原局关系、顺逆势依据；沿真实起止年份保留后续每十年地图。"),
            ("useful_gods", "1.1.10 喜忌", "用神、喜神、忌神与取用理由/分歧；不是确定计算结论。"),
            ("ziwei_life", "1.2.1 命宫", "主星、吉煞/亮度与三方四正（命/财/官/迁）；人格面具线索。"),
            ("ziwei_body", "1.2.2 身宫", "身宫位置与组合，命身一致/背离及后天方向。"),
            ("ziwei_wellbeing", "1.2.3 福德", "主星、化忌、空劫、煞与面具张力；不能据此诊断。"),
            ("ziwei_transformations", "1.2.4 四化", "区分生年四化与宫干飞化，禄权科忌源宫/目标宫/星曜，重点忌流向；其他宫位须说明问卷依据及人工选择。"),
        ],
    },
}


def stage_contract(step_key):
    stage = SOP_STAGES.get(step_key)
    if stage is None:
        return None
    return {
        "version": SOP_VERSION,
        "responsibilities": {key: stage[key] for key in ("program", "ai", "human")},
        "topics": [{"fragment_key": f"analysis.{step_key.lower()}.{key}", "title": title, "task": task} for key, title, task in stage["topics"]],
        "missing_information_policy": "仍输出该条目，写明【暂缓】或【不适用】、缺失输入/理由与补充问题；引用现有资料以证明缺失边界。不得补造用户事实。",
    }


def sop_methodology(step_key):
    contract = stage_contract(step_key)
    if not contract:
        return []
    return [
        "命理为表，心理为里，哲学为根；帮助用户看见模式并保留选择权。",
        "必须为每个覆盖条目输出一个 analysis_fragments 对象，fragment_key 原样使用；资料不足也不可跳项。",
        contract["missing_information_policy"],
        *[f'{topic["fragment_key"]}｜{topic["title"]}：{topic["task"]}' for topic in contract["topics"]],
    ]
