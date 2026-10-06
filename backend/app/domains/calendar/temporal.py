"""Calculate future calendar facts without recalculating the natal chart."""
from datetime import date, datetime, timedelta
from lunar_python import Solar


def calculate_temporal_facts(start: date, foundation: dict):
    facts = foundation.get("bazi_facts") or {}
    periods = [(6, 7), *[(hour, hour + 2) for hour in range(7, 23, 2)], (23, 24)]
    days = []
    for index in range(30):
        current = start + timedelta(days=index)
        def chart(hour, minute=0, second=0):
            ec = Solar.fromYmdHms(current.year, current.month, current.day, hour, minute, second).getLunar().getEightChar()
            ec.setSect(2)
            return ec
        ec = chart(12)
        solar_terms = Solar.fromYmdHms(current.year, current.month, current.day, 12, 0, 0).getLunar().getJieQiTable()
        transitions = []
        for name, solar in solar_terms.items():
            moment = datetime.fromisoformat(solar.toYmdHms())
            if moment.date() != current:
                continue
            before = Solar.fromDate(moment - timedelta(seconds=1)).getLunar().getEightChar()
            after = solar.getLunar().getEightChar()
            before.setSect(2)
            after.setSect(2)
            transitions.append({"solar_term": name, "at": moment.isoformat(),
                "before": {"year_pillar": before.getYear(), "month_pillar": before.getMonth()},
                "after": {"year_pillar": after.getYear(), "month_pillar": after.getMonth()}})
        dayun = next((d for d in facts.get("dayun", []) if d["start_year"] <= current.year <= d["end_year"]), None)
        days.append({
            "entry_date": current.isoformat(), "year_pillar": ec.getYear(),
            "month_pillar": ec.getMonth(), "day_pillar": ec.getDay(), "current_dayun": dayun,
            "reference_time": "12:00:00", "solar_term_transitions": transitions,
            "windows": [{"period": f"{a:02d}:00–{b:02d}:00", "time_pillar": chart(a).getTime(),
                         "year_pillar": chart(a).getYear(), "month_pillar": chart(a).getMonth(),
                         "day_pillar": chart(a).getDay()} for a, b in periods],
        })
    limitations = list(foundation.get("limitations") or [])
    if not foundation.get("bazi") or any(not day["current_dayun"] for day in days):
        limitations.append("部分日期缺少已审核本命或适用大运；相应日期使用校准色块，仅依据报告提供成长节奏参考")
    return {"version": "calendar-facts-v2", "timezone": "Asia/Shanghai", "day_boundary": "sect-2",
            "pillar_reference": "每日干支为当地12点；窗口干支为period起点。节气交接以solar_term_transitions的秒级时间为准，跨交接窗口不能将起点月柱用于整个时段。",
            "limitations": limitations,
            "natal_foundation": foundation, "days": days}
