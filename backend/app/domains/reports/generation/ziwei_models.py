"""Data structures returned by Zi Wei chart calculation."""

from dataclasses import dataclass, field


@dataclass
class ZiweiPalace:
    """紫微斗數宮位資料"""

    index: int
    name: str
    branch: int
    branch_name: str
    stem: int
    stem_name: str
    stars: list = field(default_factory=list)
    aux_stars: list = field(default_factory=list)
    brightness: dict = field(default_factory=dict)
    sihua: dict = field(default_factory=dict)
    da_xian: str = ""
    da_xian_start: int = 0
    liu_nian_ages: list = field(default_factory=list)
    xiao_xian_ages: list = field(default_factory=list)


@dataclass
class ZiweiChart:
    """紫微斗數命盤資料"""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    timezone: float
    latitude: float
    longitude: float
    location_name: str
    julian_day: float
    gender: str
    lunar_year: int
    lunar_month: int
    lunar_day: int
    is_leap_month: bool
    lunar_year_stem: int
    lunar_year_branch: int
    hour_branch: int
    ming_gong_branch: int
    shen_gong_branch: int
    wu_xing_ju: int
    ziwei_branch: int
    yin_yang: str
    ming_zhu: str
    shen_zhu: str
    sihua: dict = field(default_factory=dict)
    palaces: list = field(default_factory=list)
    sanhe_groups: list = field(default_factory=list)
    vietnam_mode: bool = False
