"""Lunar birth-date validation and options backed by lunar-python."""

from datetime import date
from typing import Optional

from lunar_python import Lunar, LunarYear, Solar


MIN_BIRTH_YEAR = 1900
MONTH_NAMES = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊")


def lunar_year_options(year: int, today: Optional[date] = None) -> dict:
    current_date = today or date.today()
    lunar_today = Solar.fromYmd(
        current_date.year, current_date.month, current_date.day
    ).getLunar()
    if year < MIN_BIRTH_YEAR or year > lunar_today.getYear():
        raise ValueError("birth_date_invalid")
    months = [
        month
        for month in LunarYear.fromYear(year).getMonths()
        if month.getYear() == year
    ]

    if year == lunar_today.getYear():
        latest_month = lunar_today.getMonth()
        latest_index = next(
            (index for index, month in enumerate(months) if month.getMonth() == latest_month),
            -1,
        )
        months = months[: latest_index + 1]

    options = []
    for month in months:
        value = month.getMonth()
        month_number = abs(value)
        selectable_day_count = month.getDayCount()
        if year == lunar_today.getYear() and value == lunar_today.getMonth():
            selectable_day_count = min(selectable_day_count, lunar_today.getDay())
        month_name = MONTH_NAMES[month_number - 1]
        options.append(
            {
                "value": value,
                "label": f"{'闰' if value < 0 else ''}{month_name}月",
                "day_count": month.getDayCount(),
                "max_day": selectable_day_count,
            }
        )

    return {"year": year, "months": options}


def lunar_calendar_options(today: Optional[date] = None) -> dict:
    current_date = today or date.today()
    current_lunar_year = Solar.fromYmd(
        current_date.year, current_date.month, current_date.day
    ).getLunar().getYear()
    return {
        "max_year": current_lunar_year,
        "years": [
            {
                "value": year,
                "label": f"{year}年",
                "months": lunar_year_options(year, current_date)["months"],
            }
            for year in range(MIN_BIRTH_YEAR, current_lunar_year + 1)
        ],
    }


def solar_date_for_birth(
    year: int,
    month: int,
    day: int,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    today: Optional[date] = None,
) -> date:
    current_date = today or date.today()
    if year < MIN_BIRTH_YEAR or year > current_date.year or not 1 <= month <= 12:
        raise ValueError("birth_date_invalid")

    if calendar_type == "solar":
        if is_leap_month:
            raise ValueError("birth_date_invalid")
        try:
            result = date(year, month, day)
        except (TypeError, ValueError) as error:
            raise ValueError("birth_date_invalid") from error
    elif calendar_type == "lunar":
        signed_month = -month if is_leap_month else month
        lunar_month = next(
            (
                item
                for item in LunarYear.fromYear(year).getMonths()
                if item.getYear() == year and item.getMonth() == signed_month
            ),
            None,
        )
        if lunar_month is None or day < 1 or day > lunar_month.getDayCount():
            raise ValueError("birth_date_invalid")
        solar = Lunar.fromYmd(year, signed_month, day).getSolar()
        result = date(solar.getYear(), solar.getMonth(), solar.getDay())
    else:
        raise ValueError("birth_date_invalid")

    if result > current_date:
        raise ValueError("birth_date_invalid")
    return result


def lunar_month_label(month: int) -> str:
    month_number = abs(month)
    if month_number < 1 or month_number > len(MONTH_NAMES):
        raise ValueError("birth_date_invalid")
    return f"{'闰' if month < 0 else ''}{MONTH_NAMES[month_number - 1]}月"
