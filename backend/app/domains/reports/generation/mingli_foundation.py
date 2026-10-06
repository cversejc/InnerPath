from typing import Any, Dict, Optional

from .bazi_calculator import bazi_calculator
from .bazi_facts import calculate_bazi_facts

def calculate_bazi_from_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从用户数据计算八字和紫微斗数

    Args:
        user_data: 用户输入数据

    Returns:
        包含八字和紫微信息的字典
    """
    def _optional_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        if value in (None, ""):
            return default
        return int(value)

    year = int(user_data.get("birth_year"))
    month = int(user_data.get("birth_month"))
    day = int(user_data.get("birth_day"))
    hour = _optional_int(user_data.get("birth_hour"))
    minute = _optional_int(user_data.get("birth_minute"), 0)
    gender = user_data.get("gender", "male")
    calendar_type = user_data.get("calendar_type") or user_data.get("calendarType", "solar")
    location = user_data.get("birth_place") or user_data.get("birth_location")

    # 获取地理坐标（如果有）
    latitude = user_data.get("latitude", 39.9)  # 默认北京
    longitude = user_data.get("longitude", 116.4)

    is_solar = calendar_type == "solar"

    # 计算八字
    bazi_result = bazi_calculator.calculate_bazi(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        is_solar=is_solar,
        is_leap_month=bool(user_data.get("birth_is_leap_month", False)),
    )

    # 计算紫微斗数 (如果有时辰)
    ziwei_result = None
    if hour is not None:
        try:
            ziwei_result = bazi_calculator.calculate_ziwei(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                gender=gender,
                location=location,
                latitude=latitude,
                longitude=longitude,
                is_solar=is_solar,
                is_leap_month=bool(user_data.get("birth_is_leap_month", False)),
            )
        except Exception as e:
            # 紫微斗数计算失败不影响八字结果
            print(f"紫微斗数计算失败: {str(e)}")
            ziwei_result = None

    return {
        "bazi": bazi_result,
        "ziwei": ziwei_result
    }


def calculate_mingli_foundation(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate report-ready mingli foundation data.

    This is the single source of truth for chart calculation. AI services should
    consume this result for interpretation only, never calculate charts.
    """
    foundation_data = calculate_bazi_from_user_data(user_data)
    bazi = foundation_data.get("bazi", {})
    ziwei = foundation_data.get("ziwei")

    result = {
        "bazi": {
            "year": {
                "stem": bazi["year"]["stem"],
                "branch": bazi["year"]["branch"],
                "ten_god": bazi["year"]["ten_god"],
            },
            "month": {
                "stem": bazi["month"]["stem"],
                "branch": bazi["month"]["branch"],
                "ten_god": bazi["month"]["ten_god"],
            },
            "day": {
                "stem": bazi["day"]["stem"],
                "branch": bazi["day"]["branch"],
            },
            "day_master": bazi["day_master"],
        },
        "calculation_method": "deterministic-mingli",
        "lunar_date": bazi.get("lunar_date", ""),
        "solar_date": bazi.get("solar_date", ""),
        "zodiac": bazi.get("zodiac", ""),
        "nayin": bazi.get("nayin", ""),
    }

    if bazi.get("hour"):
        result["bazi"]["hour"] = {
            "stem": bazi["hour"]["stem"],
            "branch": bazi["hour"]["branch"],
            "ten_god": bazi["hour"]["ten_god"],
        }

    if ziwei:
        result["ziwei"] = ziwei

    result["bazi_facts"] = calculate_bazi_facts(user_data, bazi)
    result["calculation_version"] = "mingli-v2"
    result["input_assumptions"] = user_data.get("demo_assumptions") or []
    result["limitations"] = result["bazi_facts"]["limitations"] + ([] if ziwei else ["紫微未计算，不能补造宫位星曜"])

    return result
