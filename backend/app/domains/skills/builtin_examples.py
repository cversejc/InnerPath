"""Synthetic teaching examples, reviewable through the existing skill studio."""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .models import SkillExample

EXAMPLES = {
    "report.s4_mechanism_block_action": ("boundary-experiment-v1", {"confirmed_block": "未留思考时间就承诺"}, {"method": "ACT价值澄清+行为实验", "steps": ["收到低风险请求先说：我看看安排，晚些回复你", "稍后选择同意、部分帮忙或拒绝"], "frequency": "weekly", "duration_minutes": 5, "observation": "记录对方实际反应与自己的紧张程度", "stop_rule": "出现权力威胁或明显不适时暂停，先选择安全情境"}, ["行动回应具体卡点", "理解卡点的段落不重复给解法", "有观察与退出条件"]),
    "report.s3_integration": ("integration-opposites-v1", {"confirmed": "重视友谊，常压下拒绝需要"}, {"tension": "连接与自主", "direction": "保留关心，同时让请求有选择空间", "metaphor": "有门的庭院，能邀请也能休息", "phase": "尝试对立面整合的探索假设，不能据此断定成熟程度"}, ["整合两端", "哲学意象不替代用户证据", "大运按库计算年份"]),
    "report.s1_foundation_analysis": ("chart-boundaries-v1", {"known": "有四柱但缺少能支持格局的流派判断"}, {"interpretation": "传统结构线索待咨询师判定，不用十神计数给出身强或身弱。", "missing": "核查月令、通根与生扶克泄耗"}, ["程序事实与解释分开", "无证据时明确暂缓"]),
    "report.s2_psychology_mapping": ("boundary-cycle-v1", {"self_report": "经常先答应请求，后来不舒服，拒绝时又太生硬"}, {"cycle": "请求→可能担心关系变差（假设）→先答应（自述）→不舒服→急切拒绝→下次又迁就（待访谈）", "shadow": "可能被压下的边界需要", "counter_question": "是否也有温和拒绝且关系继续的经历？"}, ["每一环区分事实和假设", "不虚构家庭成因", "现实反证可推翻解释"]),
}


async def ensure_builtin_examples(db, skill_key):
    data = EXAMPLES.get(skill_key)
    if data is None:
        return
    key, input_context, expected_output, teaching_points = data
    # Once edited or retired in the studio, never recreate the bundled version.
    if await db.scalar(select(SkillExample.id).where(SkillExample.example_key == key)):
        return
    now = datetime.utcnow()
    row = SkillExample(skill_key=skill_key, example_key=key, version_no=1, status="PUBLISHED", example_type="POSITIVE", scenario_tags=[], applicability_json={}, input_context=input_context, expected_output=expected_output, teaching_points=teaching_points, anti_patterns=["复制样例事实到当前用户", "未审核候选当作事实"], quality_score=0.9, deidentified=True, created_at=now, published_at=now)
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        if not await db.scalar(select(SkillExample.id).where(SkillExample.example_key == key)):
            raise
