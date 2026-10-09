"""Observable chart facts, not strength scores or psychological judgments."""
from collections import Counter
from itertools import combinations

from lunar_python import Solar, Lunar

from .bazi_calculator import BaziCalculator

STEMS = "甲乙丙丁戊己庚辛壬癸"
ELEMENTS = "木木火火土土金金水水"
BRANCH_ELEMENTS = dict(zip("子丑寅卯辰巳午未申酉戌亥", "水土木木土火火土金金土水"))
PAIR_RULES = {
    "六冲": ["子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"],
    "六合": ["子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"],
    "六害": ["子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌"],
    "相刑": ["子卯", "寅巳", "巳申", "申寅", "丑戌", "戌未", "未丑"],
}


def chart_interactions(pillars):
    interactions = []
    for (left, a), (right, b) in combinations(pillars.items(), 2):
        for kind, pairs in PAIR_RULES.items():
            if any(a["branch"] + b["branch"] in (pair, pair[::-1]) for pair in pairs):
                interactions.append({"type": kind, "pillars": [left, right], "symbols": a["branch"] + b["branch"]})
        if a["branch"] == b["branch"] and a["branch"] in "辰午酉亥":
            interactions.append({"type": "自刑", "pillars": [left, right], "symbols": a["branch"] * 2})
        if abs(STEMS.index(a["stem"]) - STEMS.index(b["stem"])) == 5:
            interactions.append({"type": "天干五合", "pillars": [left, right], "symbols": a["stem"] + b["stem"], "note": "有合不等于合化；成化条件由咨询师判断"})
        element_a = ELEMENTS[STEMS.index(a["stem"])]
        element_b = ELEMENTS[STEMS.index(b["stem"])]
        if element_a + element_b in ("木土", "土水", "水火", "火金", "金木") or element_b + element_a in ("木土", "土水", "水火", "火金", "金木"):
            interactions.append({"type": "天干相克", "pillars": [left, right], "symbols": a["stem"] + b["stem"]})
    branches = {p["branch"] for p in pillars.values()}
    for kind, groups in {"三合": ["申子辰", "亥卯未", "寅午戌", "巳酉丑"], "三会": ["寅卯辰", "巳午未", "申酉戌", "亥子丑"], "三刑": ["寅巳申", "丑戌未"]}.items():
        for group in groups:
            if set(group) <= branches:
                interactions.append({"type": kind, "symbols": group, "pillars": [k for k, p in pillars.items() if p["branch"] in group]})
    return interactions


def calculate_bazi_facts(profile, bazi, *, actual_birth=None):
    hour = profile.get("birth_hour")
    minute = int(profile.get("birth_minute") or 0)
    year, month, day = (int(profile[f"birth_{k}"]) for k in ("year", "month", "day"))
    if (profile.get("calendar_type") or profile.get("calendarType", "solar")) == "lunar":
        solar = Lunar.fromYmd(year, -month if profile.get("birth_is_leap_month") else month, day).getSolar()
        year, month, day = solar.getYear(), solar.getMonth(), solar.getDay()
    ec = Solar.fromYmdHms(year, month, day, int(hour or 0), minute, 0).getLunar().getEightChar()
    ec.setSect(2)
    physical_ec = Solar.fromYmdHms(**actual_birth).getLunar().getEightChar() if actual_birth else ec
    physical_ec.setSect(2)
    god_map = BaziCalculator.TEN_GODS_MAP[bazi["day_master"]]
    pillars = {}
    visible, hidden = Counter(), Counter()
    for key, prefix in (("year", "Year"), ("month", "Month"), ("day", "Day"), ("hour", "Time")):
        if key == "hour" and hour is None:
            continue
        p = dict(bazi[key])
        p["stem_element"] = ELEMENTS[STEMS.index(p["stem"])]
        p["branch_element"] = BRANCH_ELEMENTS[p["branch"]]
        source_ec = physical_ec if key in {"year", "month"} else ec
        p["hidden_stems"] = [{"stem": s, "element": ELEMENTS[STEMS.index(s)], "ten_god": god_map[s]} for s in getattr(source_ec, f"get{prefix}HideGan")()]
        p["branch_ten_god"] = p["hidden_stems"][0]["ten_god"]
        if key != "day":
            visible[god_map[p["stem"]]] += 1
        hidden.update(s["ten_god"] for s in p["hidden_stems"])
        pillars[key] = p
    master = bazi["day_master"]
    gender = profile.get("gender")
    dayun = []
    if hour is not None and gender in ("male", "female", "男", "女"):
        yun = physical_ec.getYun(1 if gender in ("male", "男") else 0, 2)
        for d in yun.getDaYun(10):
            if not d.getGanZhi():
                continue
            stem, branch = d.getGanZhi()
            dayun.append({"pillar": stem + branch, "start_year": d.getStartYear(), "end_year": d.getEndYear(), "start_age": d.getStartAge(), "end_age": d.getEndAge(), "ten_god": god_map[stem], "stem_element": ELEMENTS[STEMS.index(stem)], "branch_element": BRANCH_ELEMENTS[branch]})
    return {
        "pillars": pillars,
        "day_master": {"stem": master, "element": ELEMENTS[STEMS.index(master)], "polarity": "阳" if STEMS.index(master) % 2 == 0 else "阴"},
        "ten_god_counts": {"visible": dict(visible), "hidden": dict(hidden), "absent": sorted(set(god_map.values()) - set(visible) - set(hidden)), "note": "出现次数不代表旺衰，也不能证明心理面向缺失"},
        "interactions": chart_interactions(pillars),
        "dayun": dayun,
        "conventions": {"library": "lunar-python==1.4.8", "pillars": "节气年/月柱；晚子时不换日 sect=2", "dayun": "起运 sect=2，年龄为库的传统计龄", "time": "中国 UTC+8 民用钟表时间；未校正真太阳时", "strength_and_useful_gods": "解释性判断，必须由 AI 提候选并经咨询师确认"},
        "limitations": (["出生时间未知：不计算时柱、紫微和精确起运"] if hour is None else []) + (["性别缺失：不确定大运顺逆"] if gender not in ("male", "female", "男", "女") else []),
    }
