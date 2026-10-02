"""Civil-time and lunar-calendar conversion for Zi Wei charts."""

from typing import Tuple

import swisseph as swe
from lunar_python import Solar


_CHINA_STANDARD_TIME_OFFSET = 8.0 / 24.0


def julian_day_from_birth(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    timezone: float,
) -> float:
    swe.set_ephe_path("")
    decimal_hour = hour + minute / 60.0 - timezone
    return swe.julday(year, month, day, decimal_hour)


def hour_branch_for_time(hour: int, minute: int) -> int:
    """Return the earthly-branch index for a local birth time."""
    total_minutes = hour * 60 + minute
    if total_minutes < 60 or total_minutes >= 23 * 60:
        return 0
    return (total_minutes + 60) // 120


def lunar_date_from_julian_day(julian_day: float) -> Tuple[int, int, int, bool]:
    """Return the China-standard-time lunar year, month, day, and leap flag."""
    solar_year, solar_month, solar_day, _ = swe.revjul(
        julian_day + _CHINA_STANDARD_TIME_OFFSET
    )
    lunar = Solar.fromYmd(int(solar_year), int(solar_month), int(solar_day)).getLunar()
    month = lunar.getMonth()
    return lunar.getYear(), abs(month), lunar.getDay(), month < 0
