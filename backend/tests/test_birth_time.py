from datetime import datetime
import pytest
from lunar_python import Solar

from app.domains.reports.generation.birth_time import resolve_birth_time, match_birth_place, gazetteer
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation


def profile(**overrides):
    return {"birth_year": 2000, "birth_month": 1, "birth_day": 1, "birth_hour": 12, "birth_minute": 0,
            "birth_time_precision": "exact", "birth_place": "山东济南", "gender": "female", "calendar_type": "solar", **overrides}


def place_near(longitude):
    return min((p for p in gazetteer()["places"] if p["feature"] == "ADM3"), key=lambda p: abs(p["longitude"] - longitude))


@pytest.mark.parametrize("month,day,hour,minute,longitude,date", [(2,29,0,6,75,"2020-02-28"),(11,3,23,54,135,"2020-11-04")])
def test_solar_time_crosses_calendar_day(month, day, hour, minute, longitude, date):
    p = place_near(longitude)
    time = resolve_birth_time(profile(birth_year=2020, birth_month=month, birth_day=day, birth_hour=hour, birth_minute=minute), {"place_id":p["id"], "utc_offset_hours":8, "reason":"核对登记为北京时间", "confirmed":True})
    assert time["adopted_datetime"].startswith(date)
    assert time["registered"]["birth_day"] == day
    assert -17 < time["equation_of_time_minutes"] < 17
    assert time["actual_utc"].endswith("Z")


def test_location_context_disambiguates_and_does_not_guess():
    assert match_birth_place("朝阳区")["status"] == "AMBIGUOUS"
    assert match_birth_place("北京市朝阳区")["status"] == "MATCHED"
    assert match_birth_place("山东济南")["status"] == "MATCHED"
    assert match_birth_place("未知地点")["status"] == "UNMATCHED"
    assert resolve_birth_time(profile(birth_place="未知地点"))["status"] == "NEEDS_CONFIRMATION"


def test_unknown_hour_never_fabricates_chart_or_precise_dayun():
    foundation = calculate_mingli_foundation(profile(birth_time_precision="unknown", review_time_policy=True))
    assert "hour" not in foundation["bazi"]
    assert "ziwei" not in foundation
    assert foundation["bazi_facts"]["dayun"] == []
    assert foundation["birth_time"]["actual_utc"] is None


def test_historical_and_civil_fallback_require_explicit_basis():
    p = profile(birth_year=1989)
    assert resolve_birth_time(p)["status"] == "NEEDS_CONFIRMATION"
    with pytest.raises(ValueError, match="downgrade_confirmation_required"):
        resolve_birth_time(p, {"basis":"CIVIL"})
    fallback = resolve_birth_time(p, {"basis":"CIVIL", "confirmed":True, "reason":"登记口径无法核实，仅采用登记钟表时间，不给精确起运"})
    assert fallback["basis"] == "CIVIL" and fallback["actual_utc"] is None
    verified = resolve_birth_time(p, {"basis":"TRUE_SOLAR", "utc_offset_hours":8, "reason":"已核对冬季登记时间为北京时间", "confirmed":True})
    assert verified["status"] == "READY"


def test_lunar_leap_month_and_two_charts_share_adopted_date():
    foundation = calculate_mingli_foundation(profile(birth_year=2020, birth_month=4, birth_day=1, calendar_type="lunar", birth_is_leap_month=True,
        review_time_policy=True, birth_time_confirmation={"confirmed":True}))
    assert foundation["birth_time"]["civil_datetime"].startswith("2020-05-23")
    adopted = datetime.fromisoformat(foundation["birth_time"]["adopted_datetime"])
    lunar = Solar.fromYmdHms(adopted.year, adopted.month, adopted.day, adopted.hour, adopted.minute, adopted.second).getLunar()
    assert foundation["ziwei"]["lunar_date"].startswith(f"{lunar.getYear()}年")
    assert foundation["bazi_facts"]["conventions"]["pillars"].endswith("sect=2")


def test_year_month_and_dayun_use_actual_instant_at_solar_term():
    p = profile(birth_year=2020, birth_month=2, birth_day=4, birth_hour=17, birth_minute=5, birth_place="北京市朝阳区")
    foundation = calculate_mingli_foundation({**p, "review_time_policy":True, "birth_time_confirmation":{"confirmed":True}})
    actual = Solar.fromYmdHms(2020,2,4,17,5,0).getLunar().getEightChar()
    actual.setSect(2)
    assert foundation["bazi"]["year"]["stem"] + foundation["bazi"]["year"]["branch"] == actual.getYear()
    assert foundation["bazi"]["month"]["stem"] + foundation["bazi"]["month"]["branch"] == actual.getMonth()
    assert foundation["birth_time"]["adopted_datetime"] != foundation["birth_time"]["civil_datetime"]
