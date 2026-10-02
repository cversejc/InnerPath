"""Pure Zi Wei star placement and palace construction rules."""

from typing import Dict, List, Tuple

from .ziwei_models import ZiweiPalace
from .ziwei_tables import (
    BRIGHTNESS_LABELS,
    BRIGHTNESS_TABLE,
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    HUOXING_LINGXING_BASE,
    LUCUN_TABLE,
    NAYIN_WUXING_JU,
    PALACE_SEQUENCE,
    SIHUA_TABLE,
    TIANFU_GROUP,
    TIANMA_TABLE,
    TIANKUI_TIANYUE_TABLE,
    ZIWEI_GROUP,
)


def _get_year_stem(lunar_year: int) -> int:
    """Return the heavenly-stem index for a lunar year."""
    return (lunar_year - 4) % 10


def _get_year_branch(lunar_year: int) -> int:
    """Return the earthly-branch index for a lunar year."""
    return (lunar_year - 4) % 12


def _get_ming_gong_branch(lunar_month: int, hour_branch: int) -> int:
    """Calculate the life-palace branch using the tiger-month rule."""
    return (1 + lunar_month - hour_branch) % 12


def _get_shen_gong_branch(lunar_month: int, hour_branch: int) -> int:
    """Calculate the body-palace branch."""
    return (1 + lunar_month + hour_branch) % 12


def _get_ming_gong_stem(year_stem: int, ming_gong_branch: int) -> int:
    """Return the heavenly stem assigned to the life-palace branch."""
    yin_stem = (2 * (year_stem % 5) + 2) % 10
    steps = (ming_gong_branch - 2 + 12) % 12
    return (yin_stem + steps) % 10


def _get_wu_xing_ju(ming_gong_stem: int, ming_gong_branch: int) -> int:
    """Return the five-element bureau number from the palace's nayin."""
    sexagenary = (6 * ming_gong_stem - 5 * ming_gong_branch) % 60
    pair_idx = sexagenary // 2
    return NAYIN_WUXING_JU[pair_idx]


def _get_ziwei_branch(lunar_day: int, wu_xing_ju: int) -> int:
    """Calculate Zi Wei's branch from lunar day and the five-element bureau."""
    quotient, remainder = divmod(lunar_day, wu_xing_ju)
    if remainder == 0:
        return quotient % 12
    return (quotient + 3 - remainder) % 12


def _get_tianfu_branch(ziwei_branch: int) -> int:
    """Return Tian Fu's branch, reflected across the Yin palace."""
    return (4 - ziwei_branch + 12) % 12


def _place_main_stars(ziwei_branch: int) -> Dict[int, List[str]]:
    """Map the fourteen main stars to their earthly branches."""
    stars: Dict[int, List[str]] = {index: [] for index in range(12)}
    tianfu_branch = _get_tianfu_branch(ziwei_branch)

    for name, offset in ZIWEI_GROUP.items():
        stars[(ziwei_branch + offset) % 12].append(name)

    for name, offset in TIANFU_GROUP.items():
        stars[(tianfu_branch + offset) % 12].append(name)

    return stars


def _place_auxiliary_stars(
    year_stem: int,
    year_branch: int,
    lunar_month: int,
    hour_branch: int,
    lunar_day: int,
) -> Dict[int, List[str]]:
    """Map auxiliary stars to their earthly branches."""
    auxiliary: Dict[int, List[str]] = {index: [] for index in range(12)}

    wen_chang = (10 - hour_branch + 12) % 12
    wen_qu = (4 + hour_branch) % 12
    zuo_fu = (3 + lunar_month) % 12
    you_bi = (11 - lunar_month + 12) % 12
    auxiliary[wen_chang].append("文昌")
    auxiliary[wen_qu].append("文曲")
    auxiliary[zuo_fu].append("左輔")
    auxiliary[you_bi].append("右弼")

    lu_cun_branch = LUCUN_TABLE[year_stem]
    auxiliary[lu_cun_branch].append("祿存")
    auxiliary[(lu_cun_branch + 1) % 12].append("擎羊")
    auxiliary[(lu_cun_branch - 1 + 12) % 12].append("陀羅")

    kui_branch, yue_branch = TIANKUI_TIANYUE_TABLE[year_stem]
    auxiliary[kui_branch].append("天魁")
    auxiliary[yue_branch].append("天鉞")

    huo_base, ling_base = 1, 3
    for branches, bases in HUOXING_LINGXING_BASE.items():
        if year_branch in branches:
            huo_base, ling_base = bases
            break
    auxiliary[(huo_base + hour_branch) % 12].append("火星")
    auxiliary[(ling_base + hour_branch) % 12].append("鈴星")

    auxiliary[(hour_branch + 11) % 12].append("地劫")
    auxiliary[(11 - hour_branch + 12) % 12].append("天空")
    auxiliary[TIANMA_TABLE.get(year_branch, 2)].append("天馬")

    auxiliary[(8 + lunar_month) % 12].append("天刑")
    auxiliary[lunar_month % 12].append("天姚")
    auxiliary[(10 - year_branch + 12) % 12].append("天喜")
    auxiliary[(4 - year_branch + 12) % 12].append("紅鸞")
    auxiliary[(6 + year_branch) % 12].append("天哭")
    auxiliary[(6 - year_branch + 12) % 12].append("天虛")
    auxiliary[(4 + year_branch) % 12].append("龍池")
    auxiliary[(10 - year_branch + 12) % 12].append("鳳閣")

    auxiliary[(wen_chang + lunar_day - 1) % 12].append("恩光")
    auxiliary[(wen_qu + lunar_day - 1) % 12].append("天貴")
    auxiliary[(zuo_fu + lunar_day - 1) % 12].append("三台")
    auxiliary[(you_bi - lunar_day + 1 + 12) % 12].append("八座")
    auxiliary[(6 + hour_branch) % 12].append("台輔")
    auxiliary[(2 + hour_branch) % 12].append("封誥")

    tian_guan_by_stem = [7, 4, 5, 11, 3, 9, 11, 6, 3, 9]
    tian_fu_by_stem = [9, 8, 0, 11, 3, 6, 11, 2, 3, 6]
    auxiliary[tian_guan_by_stem[year_stem]].append("天官")
    auxiliary[tian_fu_by_stem[year_stem]].append("天福")

    return auxiliary


def _compute_sihua(year_stem: int) -> Dict[str, str]:
    """Return the four transformations for a year stem."""
    lu, quan, ke, ji = SIHUA_TABLE[year_stem]
    return {lu: "祿", quan: "權", ke: "科", ji: "忌"}


def _compute_sanhe_groups(_ming_gong_branch: int) -> List[Tuple[int, int, int]]:
    """Return the four earthly-branch trines."""
    return [
        tuple((start + offset * 4) % 12 for offset in range(3)) for start in range(4)
    ]


def _compute_feixing(palace_stem: int) -> Dict[str, str]:
    """Return the four transformations associated with a palace stem."""
    lu, quan, ke, ji = SIHUA_TABLE[palace_stem]
    return {lu: "祿", quan: "權", ke: "科", ji: "忌"}


def _build_palaces(
    ming_gong_branch: int,
    year_stem: int,
    stars_by_branch: Dict[int, List[str]],
    aux_by_branch: Dict[int, List[str]],
    sihua: Dict[str, str],
    wu_xing_ju: int,
    is_yang_male_or_yin_female: bool,
) -> List[ZiweiPalace]:
    """Build the twelve palaces, including brightness and decade ranges."""
    yin_stem = (2 * (year_stem % 5) + 2) % 10
    palaces = []

    for index in range(12):
        branch = (ming_gong_branch - index + 12) % 12
        steps = (branch - 2 + 12) % 12
        stem = (yin_stem + steps) % 10
        all_stars = stars_by_branch.get(branch, []) + aux_by_branch.get(branch, [])

        brightness = {
            star: BRIGHTNESS_LABELS.get(BRIGHTNESS_TABLE[star][branch], "")
            for star in all_stars
            if star in BRIGHTNESS_TABLE
        }
        palace_sihua = {star: sihua[star] for star in all_stars if star in sihua}
        da_xian_num = (
            (12 - index) % 12 if is_yang_male_or_yin_female and index > 0 else index
        )
        da_xian_start = wu_xing_ju + da_xian_num * 10

        palaces.append(
            ZiweiPalace(
                index=index,
                name=PALACE_SEQUENCE[index],
                branch=branch,
                branch_name=EARTHLY_BRANCHES[branch],
                stem=stem,
                stem_name=HEAVENLY_STEMS[stem],
                stars=list(stars_by_branch.get(branch, [])),
                aux_stars=list(aux_by_branch.get(branch, [])),
                brightness=brightness,
                sihua=palace_sihua,
                da_xian=f"{da_xian_start}~{da_xian_start + 9}",
                da_xian_start=da_xian_start,
            )
        )

    return palaces
