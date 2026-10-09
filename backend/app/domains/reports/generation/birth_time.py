"""Physical birth instant and adopted chart clock are deliberately distinct."""
import json
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import swisseph as swe
from lunar_python import Lunar

TIME_POLICY = "birth-time-v1"


@lru_cache(maxsize=1)
def gazetteer():
    return json.loads((Path(__file__).parent / "data/birth_places_cn.json").read_text(encoding="utf-8"))


def _name(value):
    return re.sub(r"[\s,，·]", "", str(value or "")).casefold()


def match_birth_place(text, selected_id=None):
    catalog = gazetteer()
    query = _name(text)
    province_matches = [(p, n) for p in catalog["places"] if p["feature"] == "ADM1" for alias in p["aliases"] if len(n := _name(alias)) >= 2 and n in query]
    province = max(province_matches, key=lambda pair: len(pair[1]), default=None)
    local_query = query.replace(province[1], "", 1) if province else query
    if not local_query or local_query in {"省", "市", "自治区"}:
        local_query = query
    matches = []
    for place in catalog["places"]:
        if place["feature"] == "ADM1":
            continue
        if selected_id is not None:
            if place["id"] == selected_id:
                matches.append(place)
            continue
        if province and place["admin1"] != province[0]["admin1"]:
            continue
        aliases = [_name(n) for n in place["aliases"]]
        lengths = [len(n) for n in aliases if len(n) >= 2 and (n == local_query or n in local_query)]
        if lengths:
            matches.append({**place, "match_length": max(lengths)})
    if selected_id is None and matches:
        longest = max(p["match_length"] for p in matches)
        matches = [p for p in matches if p["match_length"] == longest]
        administrative = [p for p in matches if p["feature"] in {"ADM2", "ADM3"}]
        if administrative:
            matches = administrative
        # Administrative and populated-place records at the same point are equivalent.
        unique = {}
        for p in matches:
            unique.setdefault((p["admin1"], p["admin2"], round(p["latitude"], 2), round(p["longitude"], 2)), p)
        matches = list(unique.values())
    return {"status": "MATCHED" if len(matches) == 1 else "AMBIGUOUS" if matches else "UNMATCHED",
            "candidates": matches[:50], "version": catalog["version"], "attribution": catalog["attribution"]}


def resolve_birth_time(profile, confirmation=None):
    confirmation = confirmation or {}
    y, m, d = (int(profile[f"birth_{key}"]) for key in ("year", "month", "day"))
    if profile.get("calendar_type", "solar") == "lunar":
        solar = Lunar.fromYmd(y, -m if profile.get("birth_is_leap_month") else m, d).getSolar()
        y, m, d = solar.getYear(), solar.getMonth(), solar.getDay()
    unknown = profile.get("birth_hour") is None or profile.get("birth_time_precision") == "unknown"
    civil = datetime(y, m, d, 0 if unknown else int(profile["birth_hour"]), int(profile.get("birth_minute") or 0))
    registered_civil = civil
    correction = confirmation.get("civil_datetime")
    if correction:
        try:
            civil = datetime.fromisoformat(correction)
        except (TypeError, ValueError) as error:
            raise ValueError("birth_time_correction_invalid") from error
        if civil.tzinfo is not None or not 1800 <= civil.year <= 2100:
            raise ValueError("birth_time_correction_invalid")
        if civil != registered_civil or unknown:
            if not confirmation.get("confirmed") or not str(confirmation.get("reason") or "").strip():
                raise ValueError("birth_time_correction_reason_required")
            unknown = False
            y = civil.year
    place_text = confirmation.get("birth_place") or profile.get("birth_place")
    if place_text != profile.get("birth_place") and (not confirmation.get("confirmed") or not str(confirmation.get("reason") or "").strip()):
        raise ValueError("birth_time_correction_reason_required")
    location = match_birth_place(place_text, confirmation.get("place_id"))
    result = {"policy_version": TIME_POLICY, "registered": dict(profile), "civil_datetime": civil.isoformat(),
              "location": location, "sect": 2, "confirmed": False, "limitations": []}
    result["registered_civil_datetime"] = registered_civil.isoformat()
    if unknown:
        result.update(status="UNKNOWN_HOUR", basis="UNKNOWN", adopted_datetime=civil.date().isoformat(), actual_utc=None)
        result["limitations"] = ["出生时辰未知，不计算时柱、紫微与精确起运"]
        return result
    historical = y < 1949 or 1986 <= y <= 1991
    province_names = [p for p in gazetteer()["places"] if p["feature"] == "ADM1" and any("新疆" in n for n in p["aliases"])]
    xinjiang_codes = {p["admin1"] for p in province_names}
    xinjiang = any(p["admin1"] in xinjiang_codes for p in location["candidates"])
    unclear = historical or xinjiang or profile.get("birth_time_basis_uncertain") or profile.get("birth_time_precision") == "approximate"
    offset = confirmation.get("utc_offset_hours")
    if offset is not None and not -12 <= float(offset) <= 14:
        raise ValueError("birth_time_offset_invalid")
    reason = str(confirmation.get("reason") or "").strip()
    basis = confirmation.get("basis", "TRUE_SOLAR")
    if basis not in {"TRUE_SOLAR", "CIVIL"}:
        raise ValueError("birth_time_basis_invalid")
    if basis == "CIVIL":
        if not reason or not confirmation.get("confirmed"):
            raise ValueError("birth_time_downgrade_confirmation_required")
        result["limitations"].append(reason)
    elif location["status"] != "MATCHED" or (unclear and (offset is None or not reason)):
        result.update(status="NEEDS_CONFIRMATION", basis=basis, adopted_datetime=None, actual_utc=None)
        result["limitations"].append("请核对地点、历史夏令时或填报时间口径，或说明限制后明确采用民用时间")
        return result
    # A historical/unclear civil fallback can be recorded without inventing a UTC instant.
    known_offset = offset is not None or not unclear
    actual = civil - timedelta(hours=float(offset if offset is not None else 8)) if known_offset else None
    adopted = civil
    result.update(basis=basis, utc_offset_hours=float(offset if offset is not None else 8) if known_offset else None,
                  actual_utc=actual.isoformat() + "Z" if actual else None, confirmation_reason=reason or None)
    if basis == "TRUE_SOLAR":
        place = location["candidates"][0]
        jd = swe.julday(actual.year, actual.month, actual.day, actual.hour + actual.minute / 60 + actual.second / 3600)
        lmt = jd + place["longitude"] / 360
        lat = swe.lmt_to_lat(lmt, place["longitude"])
        adopted = actual + timedelta(days=lat - jd)
        result.update(actual_jd_ut=jd, longitude_correction_minutes=(place["longitude"] - 15 * result["utc_offset_hours"]) * 4,
                      equation_of_time_minutes=(lat - lmt) * 1440, coordinates=place,
                      conversion="pyswisseph 2.10.3.2 lmt_to_lat; east-positive longitude")
    result.update(status="READY", adopted_datetime=adopted.isoformat(), confirmed=bool(confirmation.get("confirmed")))
    if profile.get("birth_time_precision") == "approximate":
        result["limitations"].append("出生时间近似，临近时辰边界的结果须保留不确定性")
    return result


def adopted_profile(profile, time):
    if time["status"] == "NEEDS_CONFIRMATION":
        raise ValueError("birth_time_confirmation_required")
    adopted = datetime.fromisoformat(time["adopted_datetime"])
    unknown = time["status"] == "UNKNOWN_HOUR"
    return {**profile, "birth_year": adopted.year, "birth_month": adopted.month, "birth_day": adopted.day,
            "birth_hour": None if unknown else adopted.hour, "birth_minute": 0 if unknown else adopted.minute,
            "birth_second": 0 if unknown else adopted.second, "calendar_type": "solar", "birth_is_leap_month": False}
