"""Compatibility entry point and orchestration for Zi Wei chart calculation."""

from .ziwei_calendar import (
    hour_branch_for_time,
    julian_day_from_birth,
    lunar_date_from_julian_day,
)
from .ziwei_models import ZiweiChart
from .ziwei_rules import (
    _build_palaces,
    _compute_sanhe_groups,
    _compute_sihua,
    _get_ming_gong_branch,
    _get_ming_gong_stem,
    _get_shen_gong_branch,
    _get_wu_xing_ju,
    _get_year_branch,
    _get_year_stem,
    _get_ziwei_branch,
    _place_auxiliary_stars,
    _place_main_stars,
)
from .ziwei_tables import MING_ZHU_TABLE, SHEN_ZHU_TABLE


def compute_ziwei_chart(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    timezone: float,
    latitude: float,
    longitude: float,
    location_name: str = "",
    gender: str = "男",
    vietnam_mode: bool = False,
) -> ZiweiChart:
    """Calculate a Zi Wei chart from a local Gregorian birth date and time."""
    julian_day = julian_day_from_birth(year, month, day, hour, minute, timezone)
    lunar_year, lunar_month, lunar_day, is_leap_month = lunar_date_from_julian_day(
        julian_day
    )
    hour_branch = hour_branch_for_time(hour, minute)

    year_stem = _get_year_stem(lunar_year)
    year_branch = _get_year_branch(lunar_year)
    ming_gong_branch = _get_ming_gong_branch(lunar_month, hour_branch)
    shen_gong_branch = _get_shen_gong_branch(lunar_month, hour_branch)
    ming_gong_stem = _get_ming_gong_stem(year_stem, ming_gong_branch)
    wu_xing_ju = _get_wu_xing_ju(ming_gong_stem, ming_gong_branch)
    ziwei_branch = _get_ziwei_branch(lunar_day, wu_xing_ju)

    stars_by_branch = _place_main_stars(ziwei_branch)
    auxiliary_by_branch = _place_auxiliary_stars(
        year_stem, year_branch, lunar_month, hour_branch, lunar_day
    )

    yin_yang = "陽" if year_stem % 2 == 0 else "陰"
    is_yang_male_or_yin_female = (yin_yang == "陽" and gender == "男") or (
        yin_yang == "陰" and gender == "女"
    )
    sihua = _compute_sihua(year_stem)
    palaces = _build_palaces(
        ming_gong_branch,
        year_stem,
        stars_by_branch,
        auxiliary_by_branch,
        sihua,
        wu_xing_ju,
        is_yang_male_or_yin_female,
    )

    return ZiweiChart(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        julian_day=julian_day,
        gender=gender,
        lunar_year=lunar_year,
        lunar_month=lunar_month,
        lunar_day=lunar_day,
        is_leap_month=is_leap_month,
        lunar_year_stem=year_stem,
        lunar_year_branch=year_branch,
        hour_branch=hour_branch,
        ming_gong_branch=ming_gong_branch,
        shen_gong_branch=shen_gong_branch,
        wu_xing_ju=wu_xing_ju,
        ziwei_branch=ziwei_branch,
        yin_yang=yin_yang,
        ming_zhu=MING_ZHU_TABLE[ming_gong_branch],
        shen_zhu=SHEN_ZHU_TABLE[year_branch],
        sihua=sihua,
        palaces=palaces,
        sanhe_groups=_compute_sanhe_groups(ming_gong_branch),
        vietnam_mode=vietnam_mode,
    )
