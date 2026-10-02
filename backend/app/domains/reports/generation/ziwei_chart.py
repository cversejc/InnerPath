"""Pure Zi Wei chart calculation used by deterministic report generation."""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import swisseph as swe
from lunar_python import Solar

# ============================================================
# 常量 (Constants)
# ============================================================

EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

LUNAR_MONTH_NAMES = [
    "正月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]

HOUR_BRANCH_NAMES = [
    "子時(23-01)", "丑時(01-03)", "寅時(03-05)", "卯時(05-07)",
    "辰時(07-09)", "巳時(09-11)", "午時(11-13)", "未時(13-15)",
    "申時(15-17)", "酉時(17-19)", "戌時(19-21)", "亥時(21-23)",
]

# 五行局
WU_XING_JU_NAMES = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}

# 十二宮位名稱（從命宮起，逆時針地支方向排列）
# 命宮在某地支，兄弟宮在下一個地支，依此類推
PALACE_SEQUENCE = [
    "命宮", "兄弟宮", "夫妻宮", "子女宮", "財帛宮", "疾厄宮",
    "遷移宮", "交友宮", "官祿宮", "田宅宮", "福德宮", "父母宮",
]

# 紫微系：相對於紫微星地支的偏移（逆佈 mod 12）
ZIWEI_GROUP = {
    "紫微": 0,
    "天機": 11,   # -1 mod 12
    "太陽": 9,    # -3 mod 12
    "武曲": 8,    # -4 mod 12
    "天同": 7,    # -5 mod 12
    "廉貞": 4,    # -8 mod 12
}

# 天府系：相對於天府星地支的偏移（順佈 mod 12）
TIANFU_GROUP = {
    "天府": 0,
    "太陰": 1,
    "貪狼": 2,
    "巨門": 3,
    "天相": 4,
    "天梁": 5,
    "七殺": 6,
    "破軍": 10,
}

# ============================================================
# 納音五行局 (Nayin Wu Xing Ju)
# ============================================================
# 60 甲子納音五行對應局數，每兩組干支共用一個納音
# 索引 = 六十甲子序號 // 2 (0-29)
# 值 = 五行局數: 金4, 火6, 木3, 土5, 水2
NAYIN_WUXING_JU = [
    4, 6, 3, 5, 4,  # 甲子乙丑海中金, 丙寅丁卯爐中火, 戊辰己巳大林木, 庚午辛未路旁土, 壬申癸酉劍鋒金
    6, 2, 5, 4, 3,  # 甲戌乙亥山頭火, 丙子丁丑澗下水, 戊寅己卯城頭土, 庚辰辛巳白蠟金, 壬午癸未楊柳木
    2, 5, 6, 3, 2,  # 甲申乙酉泉中水, 丙戌丁亥屋上土, 戊子己丑霹靂火, 庚寅辛卯松柏木, 壬辰癸巳長流水
    4, 6, 3, 5, 4,  # 甲午乙未沙中金, 丙申丁酉山下火, 戊戌己亥平地木, 庚子辛丑壁上土, 壬寅癸卯金箔金
    6, 2, 5, 4, 3,  # 甲辰乙巳覆燈火, 丙午丁未天河水, 戊申己酉大驛土, 庚戌辛亥釵環金, 壬子癸丑桑柘木
    2, 5, 6, 3, 2,  # 甲寅乙卯大溪水, 丙辰丁巳沙中土, 戊午己未天上火, 庚申辛酉石榴木, 壬戌癸亥大海水
]

# ============================================================
# 四化表 (Four Transformations by Year Stem)
# ============================================================
# 索引 = 年干 (0=甲 ~ 9=癸)
# 值 = (化祿, 化權, 化科, 化忌) 的星曜名
SIHUA_TABLE = [
    ("廉貞", "破軍", "武曲", "太陽"),  # 甲
    ("天機", "天梁", "紫微", "太陰"),  # 乙
    ("天同", "天機", "文昌", "廉貞"),  # 丙
    ("太陰", "天同", "天機", "巨門"),  # 丁
    ("貪狼", "太陰", "右弼", "天機"),  # 戊
    ("武曲", "貪狼", "天梁", "文曲"),  # 己
    ("太陽", "武曲", "天府", "天同"),  # 庚
    ("巨門", "太陽", "文曲", "文昌"),  # 辛
    ("天梁", "紫微", "左輔", "武曲"),  # 壬
    ("破軍", "巨門", "太陰", "貪狼"),  # 癸
]

# ============================================================
# 祿存表 (Lu Cun by Year Stem)
# ============================================================
# 甲寅 乙卯 丙巳 丁午 戊巳 己午 庚申 辛酉 壬亥 癸子
LUCUN_TABLE = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]

# ============================================================
# 天魁天鉞表 (Tian Kui / Tian Yue by Year Stem)
# ============================================================
# (天魁branch, 天鉞branch) by year stem
TIANKUI_TIANYUE_TABLE = [
    (1, 7),   # 甲: 丑, 未
    (0, 8),   # 乙: 子, 申
    (11, 9),  # 丙: 亥, 酉
    (11, 9),  # 丁: 亥, 酉
    (1, 7),   # 戊: 丑, 未
    (0, 8),   # 己: 子, 申
    (1, 7),   # 庚: 丑, 未
    (6, 2),   # 辛: 午, 寅
    (3, 5),   # 壬: 卯, 巳
    (3, 5),   # 癸: 卯, 巳
]

# ============================================================
# 火星鈴星起始宮 (Huo Xing / Ling Xing base by year branch group)
# ============================================================
# 年支分四組: 寅午戌(火), 申子辰(水), 巳酉丑(金), 亥卯未(木)
# (火星base, 鈴星base)
HUOXING_LINGXING_BASE = {
    (2, 6, 10): (1, 3),   # 寅午戌: 火星起丑, 鈴星起卯
    (8, 0, 4):  (2, 10),  # 申子辰: 火星起寅, 鈴星起戌
    (5, 9, 1):  (3, 10),  # 巳酉丑: 火星起卯, 鈴星起戌
    (11, 3, 7): (9, 10),  # 亥卯未: 火星起酉, 鈴星起戌
}

# ============================================================
# 天馬表 (Tian Ma by Year Branch)
# ============================================================
TIANMA_TABLE = {
    0: 2, 1: 11, 2: 8, 3: 5, 4: 2, 5: 11,   # 子寅 丑亥 寅申 卯巳 辰寅 巳亥
    6: 8, 7: 5, 8: 2, 9: 11, 10: 8, 11: 5,   # 午申 未巳 申寅 酉亥 戌申 亥巳
}

# ============================================================
# 命主 / 身主表
# ============================================================
MING_ZHU_TABLE = ["貪狼", "巨門", "祿存", "文曲", "廉貞", "武曲",
                  "破軍", "武曲", "廉貞", "文曲", "祿存", "巨門"]
SHEN_ZHU_TABLE = ["火星", "天相", "天梁", "天同", "文昌", "天機",
                  "火星", "天相", "天梁", "天同", "文昌", "天機"]

# ============================================================
# 星曜亮度表 (Star Brightness)
# ============================================================
# 亮度等級: 廟=6, 旺=5, 得=4, 利=3, 平=2, 不=1, 陷=0
# 索引 = 地支 (0=子 ~ 11=亥), 值 = 亮度等級
BRIGHTNESS_TABLE = {
    "紫微": [5, 6, 1, 4, 1, 6, 5, 5, 5, 2, 6, 4],
    "天機": [4, 6, 5, 6, 2, 1, 4, 6, 5, 6, 2, 1],
    "太陽": [5, 6, 6, 6, 5, 4, 2, 1, 0, 0, 1, 2],
    "武曲": [6, 5, 2, 4, 6, 5, 6, 4, 2, 6, 5, 2],
    "天同": [2, 1, 5, 4, 1, 6, 5, 0, 2, 6, 4, 6],
    "廉貞": [2, 0, 6, 5, 2, 2, 6, 2, 6, 0, 2, 5],
    "天府": [6, 5, 6, 4, 6, 5, 6, 4, 6, 5, 6, 4],
    "太陰": [6, 6, 0, 0, 1, 2, 4, 5, 6, 6, 5, 6],
    "貪狼": [5, 6, 2, 6, 2, 6, 5, 6, 2, 6, 2, 6],
    "巨門": [6, 5, 4, 6, 2, 1, 6, 5, 4, 6, 2, 1],
    "天相": [6, 4, 6, 2, 4, 5, 6, 4, 6, 2, 4, 5],
    "天梁": [6, 5, 6, 4, 2, 4, 6, 5, 6, 4, 2, 4],
    "七殺": [6, 5, 6, 2, 4, 4, 6, 5, 6, 2, 4, 4],
    "破軍": [5, 6, 2, 4, 0, 2, 5, 6, 2, 4, 0, 2],
    "文昌": [4, 6, 5, 2, 4, 6, 4, 0, 4, 6, 5, 4],
    "文曲": [4, 2, 4, 6, 5, 6, 4, 0, 4, 2, 5, 6],
    "左輔": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
    "右弼": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
    "祿存": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
}
BRIGHTNESS_LABELS = {6: "廟", 5: "旺", 4: "得", 3: "利", 2: "平", 1: "不", 0: "陷"}

# 主星屬性（五行、別稱、顏色）
STAR_ATTRIBUTES = {
    "紫微": ("土", "帝王星", "#C62828"),
    "天機": ("木", "謀略星", "#2E7D32"),
    "太陽": ("火", "官祿星", "#E65100"),
    "武曲": ("金", "財星", "#F9A825"),
    "天同": ("水", "福星", "#1565C0"),
    "廉貞": ("火", "囚星", "#AD1457"),
    "天府": ("土", "財帛星", "#6A1B9A"),
    "太陰": ("水", "田宅星", "#37474F"),
    "貪狼": ("木/水", "桃花星", "#4A148C"),
    "巨門": ("水", "是非星", "#004D40"),
    "天相": ("水", "印星", "#0D47A1"),
    "天梁": ("土", "蔭星", "#33691E"),
    "七殺": ("金/火", "將星", "#B71C1C"),
    "破軍": ("水", "耗星", "#311B92"),
}

# 農曆新年公曆日期查找表 1900–2050（月, 日）
# 資料來源：天文計算（公開領域）
_CHINESE_NEW_YEAR: Dict[int, Tuple[int, int]] = {
    1900: (1, 31), 1901: (2, 19), 1902: (2,  8), 1903: (1, 29), 1904: (2, 16),
    1905: (2,  4), 1906: (1, 25), 1907: (2, 13), 1908: (2,  2), 1909: (1, 22),
    1910: (2, 10), 1911: (1, 30), 1912: (2, 18), 1913: (2,  6), 1914: (1, 26),
    1915: (2, 14), 1916: (2,  3), 1917: (1, 23), 1918: (2, 11), 1919: (2,  1),
    1920: (2, 20), 1921: (2,  8), 1922: (1, 28), 1923: (2, 16), 1924: (2,  5),
    1925: (1, 25), 1926: (2, 13), 1927: (2,  2), 1928: (1, 23), 1929: (2, 10),
    1930: (1, 30), 1931: (2, 17), 1932: (2,  6), 1933: (1, 26), 1934: (2, 14),
    1935: (2,  4), 1936: (1, 24), 1937: (2, 11), 1938: (1, 31), 1939: (2, 19),
    1940: (2,  8), 1941: (1, 27), 1942: (2, 15), 1943: (2,  5), 1944: (1, 25),
    1945: (2, 13), 1946: (2,  2), 1947: (1, 22), 1948: (2, 10), 1949: (1, 29),
    1950: (2, 17), 1951: (2,  6), 1952: (1, 27), 1953: (2, 14), 1954: (2,  3),
    1955: (1, 24), 1956: (2, 12), 1957: (1, 31), 1958: (2, 18), 1959: (2,  8),
    1960: (1, 28), 1961: (2, 15), 1962: (2,  5), 1963: (1, 25), 1964: (2, 13),
    1965: (2,  2), 1966: (1, 21), 1967: (2,  9), 1968: (1, 30), 1969: (2, 17),
    1970: (2,  6), 1971: (1, 27), 1972: (2, 15), 1973: (2,  3), 1974: (1, 23),
    1975: (2, 11), 1976: (1, 31), 1977: (2, 18), 1978: (2,  7), 1979: (1, 28),
    1980: (2, 16), 1981: (2,  5), 1982: (1, 25), 1983: (2, 13), 1984: (2,  2),
    1985: (2, 20), 1986: (2,  9), 1987: (1, 29), 1988: (2, 17), 1989: (2,  6),
    1990: (1, 27), 1991: (2, 15), 1992: (2,  4), 1993: (1, 23), 1994: (2, 10),
    1995: (1, 31), 1996: (2, 19), 1997: (2,  7), 1998: (1, 28), 1999: (2, 16),
    2000: (2,  5), 2001: (1, 24), 2002: (2, 12), 2003: (2,  1), 2004: (1, 22),
    2005: (2,  9), 2006: (1, 29), 2007: (2, 18), 2008: (2,  7), 2009: (1, 26),
    2010: (2, 14), 2011: (2,  3), 2012: (1, 23), 2013: (2, 10), 2014: (1, 31),
    2015: (2, 19), 2016: (2,  8), 2017: (1, 28), 2018: (2, 16), 2019: (2,  5),
    2020: (1, 25), 2021: (2, 12), 2022: (2,  1), 2023: (1, 22), 2024: (2, 10),
    2025: (1, 29), 2026: (2, 17), 2027: (2,  6), 2028: (1, 26), 2029: (2, 13),
    2030: (2,  3), 2031: (1, 23), 2032: (2, 11), 2033: (1, 31), 2034: (2, 19),
    2035: (2,  8), 2036: (1, 28), 2037: (2, 15), 2038: (2,  4), 2039: (1, 24),
    2040: (2, 12), 2041: (2,  1), 2042: (1, 22), 2043: (2, 10), 2044: (1, 30),
    2045: (2, 17), 2046: (2,  6), 2047: (1, 26), 2048: (2, 14), 2049: (2,  2),
    2050: (1, 23),
}

# 平均朔望月長度（天）。此常數用於逼近下次朔望的初始估算；
# 精確朔日時刻由 pyswisseph 的日月黃經迭代法確定。
_SYNODIC_MONTH = 29.5305891

# 北京時間（CST = UTC+8）偏移量（以 JD 天為單位）。
# 農曆以北京時間為準，日期邊界為午夜零時。
_CST_OFFSET = 8.0 / 24.0

# ============================================================
# 資料類 (Data Classes)
# ============================================================

@dataclass
class ZiweiPalace:
    """紫微斗數宮位資料"""
    index: int                      # 宮位序號 0-11（從命宮算起）
    name: str                       # 宮位名稱
    branch: int                     # 地支索引 0-11（子=0）
    branch_name: str                # 地支名稱
    stem: int                       # 天干索引 0-9
    stem_name: str                  # 天干名稱
    stars: list = field(default_factory=list)       # 主星名稱
    aux_stars: list = field(default_factory=list)   # 輔助星名稱
    brightness: dict = field(default_factory=dict)  # {星名: 亮度標籤}
    sihua: dict = field(default_factory=dict)       # {星名: 四化類型}
    da_xian: str = ""               # 大限年齡範圍 e.g. "3~12"
    da_xian_start: int = 0          # 大限起始年齡
    liu_nian_ages: list = field(default_factory=list)  # 流年年齡列表
    xiao_xian_ages: list = field(default_factory=list) # 小限年齡列表


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
    gender: str                    # "男" or "女"

    # 農曆資訊
    lunar_year: int
    lunar_month: int
    lunar_day: int
    is_leap_month: bool
    lunar_year_stem: int       # 天干索引
    lunar_year_branch: int     # 地支索引

    # 時辰
    hour_branch: int           # 0-11

    # 命盤關鍵資訊
    ming_gong_branch: int      # 命宮地支索引
    shen_gong_branch: int      # 身宮地支索引
    wu_xing_ju: int            # 五行局（2-6）
    ziwei_branch: int          # 紫微星地支索引
    yin_yang: str              # "陰" or "陽"
    ming_zhu: str              # 命主星名
    shen_zhu: str              # 身主星名

    # 四化
    sihua: dict = field(default_factory=dict)  # {星名: 四化類型}

    # 宮位資料
    palaces: list = field(default_factory=list)  # List[ZiweiPalace]

    # 三合組
    sanhe_groups: list = field(default_factory=list)  # List of (branch1, branch2, branch3)

    # 越南模式
    vietnam_mode: bool = False  # True = 越南 Tử Vi 模式（以貓代兔）


# ============================================================
# 輔助函數 (Helper Functions)
# ============================================================

def _normalize(deg: float) -> float:
    return deg % 360.0


def _get_hour_branch(hour: int, minute: int) -> int:
    """
    根據出生時間取得時辰地支索引（子=0, 丑=1, ..., 亥=11）。
    子時跨越午夜：23:00-01:00 為子時。
    """
    total_minutes = hour * 60 + minute
    if total_minutes < 60 or total_minutes >= 23 * 60:
        return 0   # 子時 (23:00–01:00)
    return (total_minutes + 60) // 120  # 每 2 小時一個時辰


def _find_new_moon_near(jd_approx: float) -> float:
    """
    以迭代法（牛頓法）找出最接近 jd_approx 的朔（新月）Julian Day。
    收斂至誤差 < 0.0001° 的日食相角。
    """
    jd = jd_approx
    for _ in range(50):
        sun_lon = _normalize(swe.calc_ut(jd, swe.SUN)[0][0])
        moon_lon = _normalize(swe.calc_ut(jd, swe.MOON)[0][0])
        diff = moon_lon - sun_lon
        if diff > 180:
            diff -= 360.0
        elif diff < -180:
            diff += 360.0
        # 月球相對太陽速度約 12.19°/天
        correction = diff / (360.0 / _SYNODIC_MONTH)
        jd -= correction
        if abs(diff) < 0.0001:
            break
    return jd


def _get_cny_jd(year: int) -> float:
    """取得農曆新年的 Julian Day。僅支援 1900–2050；超出範圍時回傳近似值。"""
    if year in _CHINESE_NEW_YEAR:
        m, d = _CHINESE_NEW_YEAR[year]
        return swe.julday(year, m, d, 12.0)
    # 超出查找表範圍：以鄰近端點外推（精度不佳，僅作 fallback）
    if year < 1900:
        m, d = _CHINESE_NEW_YEAR[1900]
        base_jd = swe.julday(1900, m, d, 12.0)
        return base_jd - (1900 - year) * 365.2425
    m, d = _CHINESE_NEW_YEAR[2050]
    base_jd = swe.julday(2050, m, d, 12.0)
    return base_jd + (year - 2050) * 365.2425


def _solar_to_lunar(jd: float) -> Tuple[int, int, int, bool]:
    """
    將 Julian Day 轉換為農曆日期。

    使用 lunar-python 進行準確的農曆轉換，避免閏月判斷錯誤。

    Returns:
        (lunar_year, lunar_month, lunar_day, is_leap_month)
        lunar_month: 1-12（閏月與正常月同編號，is_leap_month=True 區分）
    """
    # 將 JD 轉換為公曆日期
    gd = swe.revjul(jd)  # (year, month, day, hour)
    year = int(gd[0])
    month = int(gd[1])
    day = int(gd[2])

    # 使用 lunar-python 進行農曆轉換
    solar = Solar.fromYmd(year, month, day)
    lunar = solar.getLunar()

    lunar_year = lunar.getYear()
    lunar_month_raw = lunar.getMonth()
    lunar_day = lunar.getDay()

    # lunar-python 中，閏月用負數表示（如 -5 表示閏五月）
    if lunar_month_raw < 0:
        is_leap = True
        lunar_month = abs(lunar_month_raw)
    else:
        is_leap = False
        lunar_month = lunar_month_raw

    return lunar_year, lunar_month, lunar_day, is_leap


def _get_year_stem(lunar_year: int) -> int:
    """
    取得農曆年的天干索引（甲=0, 乙=1, ..., 癸=9）。
    公式：(year - 4) % 10
    """
    return (lunar_year - 4) % 10


def _get_year_branch(lunar_year: int) -> int:
    """
    取得農曆年的地支索引（子=0, 丑=1, ..., 亥=11）。
    公式：(year - 4) % 12
    """
    return (lunar_year - 4) % 12


def _get_ming_gong_branch(lunar_month: int, hour_branch: int) -> int:
    """
    計算命宮地支索引。

    規則（虎月法）：
      以寅宮（地支索引2）為正月所在，逐月順數；
      再由出生時辰逆數。
    公式：(1 + lunar_month - hour_branch) % 12
    """
    return (1 + lunar_month - hour_branch) % 12


def _get_shen_gong_branch(lunar_month: int, hour_branch: int) -> int:
    """
    計算身宮地支索引。

    規則：以寅宮起，逐月順數，再順數時辰。
    公式：(1 + lunar_month + hour_branch) % 12
    """
    return (1 + lunar_month + hour_branch) % 12


def _get_ming_gong_stem(year_stem: int, ming_gong_branch: int) -> int:
    """
    取得命宮天干索引（用於判斷五行局）。

    步驟：
      1. 以年天干推算寅宮天干（虎年起法）：
         寅宮天干 = (2 * (year_stem % 5) + 2) % 10
      2. 命宮天干 = (寅宮天干 + (命宮地支 - 2 + 12) % 12) % 10
    """
    yin_stem = (2 * (year_stem % 5) + 2) % 10
    steps = (ming_gong_branch - 2 + 12) % 12
    return (yin_stem + steps) % 10


def _get_wu_xing_ju(ming_gong_stem: int, ming_gong_branch: int) -> int:
    """
    由命宮天干地支的納音五行判斷五行局號（2-6）。

    使用六十甲子納音五行查表法：
      1. 由天干地支計算六十甲子序號
      2. 每兩組共用一個納音五行
      3. 納音五行對應局數：金4 木3 水2 火6 土5
    """
    sexagenary = (6 * ming_gong_stem - 5 * ming_gong_branch) % 60
    pair_idx = sexagenary // 2
    return NAYIN_WUXING_JU[pair_idx]


def _get_ziwei_branch(lunar_day: int, wu_xing_ju: int) -> int:
    """
    由農曆生日與五行局計算紫微星所在地支索引。

    安紫微法：以局數 N 分組，每 N 天為一組。
    組內第一天（餘數=N-1）在最高位，之後逐日降低。
    整除時為組底。

    公式（使用整數除法）：
      q, r = divmod(lunar_day, wu_xing_ju)
      若 r == 0: branch = q % 12
      若 r > 0: branch = (q + 3 - r) % 12
    """
    n = wu_xing_ju
    q, r = divmod(lunar_day, n)
    if r == 0:
        return q % 12
    return (q + 3 - r) % 12


def _get_tianfu_branch(ziwei_branch: int) -> int:
    """
    由紫微星地支計算天府星地支索引。
    天府與紫微關於寅宮對稱。
    公式：(4 - ziwei_branch + 12) % 12
    """
    return (4 - ziwei_branch + 12) % 12


def _place_main_stars(ziwei_branch: int) -> Dict[int, List[str]]:
    """
    計算所有 14 顆主星的地支索引，返回 {branch_index: [star_names]} 映射。
    """
    stars: Dict[int, List[str]] = {i: [] for i in range(12)}
    tianfu_branch = _get_tianfu_branch(ziwei_branch)

    for name, offset in ZIWEI_GROUP.items():
        b = (ziwei_branch + offset) % 12
        stars[b].append(name)

    for name, offset in TIANFU_GROUP.items():
        b = (tianfu_branch + offset) % 12
        stars[b].append(name)

    return stars


def _place_auxiliary_stars(
    year_stem: int, year_branch: int,
    lunar_month: int, hour_branch: int,
    lunar_day: int,
) -> Dict[int, List[str]]:
    """
    計算輔助星的地支索引，返回 {branch_index: [star_names]} 映射。
    """
    aux: Dict[int, List[str]] = {i: [] for i in range(12)}

    # 文昌 (based on hour branch, reverse from 戌)
    wen_chang = (10 - hour_branch + 12) % 12
    aux[wen_chang].append("文昌")

    # 文曲 (based on hour branch, forward from 辰)
    wen_qu = (4 + hour_branch) % 12
    aux[wen_qu].append("文曲")

    # 左輔 (based on lunar month, forward from 辰)
    zuo_fu = (3 + lunar_month) % 12
    aux[zuo_fu].append("左輔")

    # 右弼 (based on lunar month, reverse from 戌)
    you_bi = (11 - lunar_month + 12) % 12
    aux[you_bi].append("右弼")

    # 祿存 (by year stem)
    lu_cun_branch = LUCUN_TABLE[year_stem]
    aux[lu_cun_branch].append("祿存")

    # 擎羊 = 祿存 + 1
    qing_yang = (lu_cun_branch + 1) % 12
    aux[qing_yang].append("擎羊")

    # 陀羅 = 祿存 - 1
    tuo_luo = (lu_cun_branch - 1 + 12) % 12
    aux[tuo_luo].append("陀羅")

    # 天魁 / 天鉞
    kui_branch, yue_branch = TIANKUI_TIANYUE_TABLE[year_stem]
    aux[kui_branch].append("天魁")
    aux[yue_branch].append("天鉞")

    # 火星 / 鈴星 (by year branch group + hour branch)
    huo_base, ling_base = 1, 3  # default
    for branches, bases in HUOXING_LINGXING_BASE.items():
        if year_branch in branches:
            huo_base, ling_base = bases
            break
    huo_xing = (huo_base + hour_branch) % 12
    ling_xing = (ling_base + hour_branch) % 12
    aux[huo_xing].append("火星")
    aux[ling_xing].append("鈴星")

    # 地劫 / 天空
    di_jie = (hour_branch + 11) % 12
    tian_kong = (11 - hour_branch + 12) % 12
    aux[di_jie].append("地劫")
    aux[tian_kong].append("天空")

    # 天馬
    tian_ma = TIANMA_TABLE.get(year_branch, 2)
    aux[tian_ma].append("天馬")

    # 天刑 (based on lunar month, forward from 酉)
    tian_xing = (8 + lunar_month) % 12
    aux[tian_xing].append("天刑")

    # 天姚 (based on lunar month, forward from 丑)
    tian_yao = (0 + lunar_month) % 12
    aux[tian_yao].append("天姚")

    # 天喜 (by year branch: 戌起子 reverse)
    tian_xi = (10 - year_branch + 12) % 12
    aux[tian_xi].append("天喜")

    # 紅鸞 (by year branch)
    hong_luan = (4 - year_branch + 12) % 12
    aux[hong_luan].append("紅鸞")

    # 天哭 / 天虛 (by year branch)
    tian_ku = (6 + year_branch) % 12
    tian_xu = (6 - year_branch + 12) % 12
    aux[tian_ku].append("天哭")
    aux[tian_xu].append("天虛")

    # 龍池 / 鳳閣 (by year branch)
    long_chi = (4 + year_branch) % 12
    feng_ge = (10 - year_branch + 12) % 12
    aux[long_chi].append("龍池")
    aux[feng_ge].append("鳳閣")

    # 恩光 / 天貴 (by day: from 文昌/文曲 forward by day)
    en_guang = (wen_chang + lunar_day - 1) % 12
    tian_gui = (wen_qu + lunar_day - 1) % 12
    aux[en_guang].append("恩光")
    aux[tian_gui].append("天貴")

    # 三台 / 八座 (by month + day, adjusted from 左輔/右弼)
    san_tai = (zuo_fu + lunar_day - 1) % 12
    ba_zuo = (you_bi - lunar_day + 1 + 12) % 12
    aux[san_tai].append("三台")
    aux[ba_zuo].append("八座")

    # 台輔 / 封誥 (by hour)
    tai_fu = (6 + hour_branch) % 12
    feng_gao = (2 + hour_branch) % 12
    aux[tai_fu].append("台輔")
    aux[feng_gao].append("封誥")

    # 天官 / 天福 (by year stem)
    _TIANGUAN = [7, 4, 5, 11, 3, 9, 11, 6, 3, 9]
    _TIANFU_AUX = [9, 8, 0, 11, 3, 6, 11, 2, 3, 6]
    aux[_TIANGUAN[year_stem]].append("天官")
    aux[_TIANFU_AUX[year_stem]].append("天福")

    return aux


def _compute_sihua(year_stem: int, stars_by_branch: Dict[int, List[str]],
                   aux_by_branch: Dict[int, List[str]]) -> Dict[str, str]:
    """
    計算四化：化祿、化權、化科、化忌。
    Returns {star_name: transformation_type}
    """
    lu, quan, ke, ji = SIHUA_TABLE[year_stem]
    return {lu: "祿", quan: "權", ke: "科", ji: "忌"}


def _compute_sanhe_groups(ming_gong_branch: int) -> List[Tuple[int, int, int]]:
    """
    計算三合組（每組三個宮位，間隔4個地支）。
    Returns list of (branch1, branch2, branch3) tuples.
    """
    groups = []
    for start in range(4):
        group = tuple((start + i * 4) % 12 for i in range(3))
        groups.append(group)
    return groups


def _compute_feixing(palace_stem: int) -> Dict[str, str]:
    """
    計算飛星四化（由宮位天干決定）。
    Returns {star_name: transformation_type}
    """
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
    """
    建立十二宮位資料。
    命宮在 ming_gong_branch，依地支逆序（counter-clockwise）排列。
    宮位天干由虎年起法推算。
    大限方向：陽男陰女順行（地支增加），陰男陽女逆行（地支減少）。
    """
    # 寅宮天干
    yin_stem = (2 * (year_stem % 5) + 2) % 10

    palaces = []
    for idx in range(12):
        # 宮位按逆時針排列（地支遞減）
        branch = (ming_gong_branch - idx + 12) % 12
        palace_name = PALACE_SEQUENCE[idx]
        steps = (branch - 2 + 12) % 12
        stem = (yin_stem + steps) % 10

        # 星曜亮度
        brightness = {}
        all_stars = stars_by_branch.get(branch, []) + aux_by_branch.get(branch, [])
        for star in all_stars:
            if star in BRIGHTNESS_TABLE:
                level = BRIGHTNESS_TABLE[star][branch]
                brightness[star] = BRIGHTNESS_LABELS.get(level, "")

        # 宮位四化（本命四化）
        palace_sihua = {}
        for star in all_stars:
            if star in sihua:
                palace_sihua[star] = sihua[star]

        # 大限：陰男陽女逆行（palace idx直接對應），陽男陰女順行（反轉idx）
        if is_yang_male_or_yin_female:
            da_xian_num = (12 - idx) % 12 if idx > 0 else 0
        else:
            da_xian_num = idx
        da_xian_start = wu_xing_ju + da_xian_num * 10
        da_xian_end = da_xian_start + 9
        da_xian = f"{da_xian_start}~{da_xian_end}"

        palaces.append(ZiweiPalace(
            index=idx,
            name=palace_name,
            branch=branch,
            branch_name=EARTHLY_BRANCHES[branch],
            stem=stem,
            stem_name=HEAVENLY_STEMS[stem],
            stars=list(stars_by_branch.get(branch, [])),
            aux_stars=list(aux_by_branch.get(branch, [])),
            brightness=brightness,
            sihua=palace_sihua,
            da_xian=da_xian,
            da_xian_start=da_xian_start,
        ))
    return palaces


# ============================================================
# 計算函數 (Computation)
# ============================================================

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
    """
    計算紫微斗數命盤。

    Parameters:
        year, month, day: 公曆出生日期
        hour, minute:     出生時間（24 小時制）
        timezone:         時區偏移（UTC+N）
        latitude:         緯度（排盤資訊用途）
        longitude:        經度（排盤資訊用途）
        location_name:    地點名稱
        gender:           性別（"男" or "女"）
        vietnam_mode:     是否啟用越南 Tử Vi 模式（以貓代兔等越南特色）

    Returns:
        ZiweiChart: 命盤資料
    """
    swe.set_ephe_path("")

    decimal_hour = hour + minute / 60.0 - timezone
    jd = swe.julday(year, month, day, decimal_hour)

    # 農曆轉換
    lunar_year, lunar_month, lunar_day, is_leap = _solar_to_lunar(jd)

    # 時辰地支
    hour_branch = _get_hour_branch(hour, minute)

    # 農曆年天干地支
    year_stem = _get_year_stem(lunar_year)
    year_branch = _get_year_branch(lunar_year)

    # 命宮 / 身宮
    ming_gong_branch = _get_ming_gong_branch(lunar_month, hour_branch)
    shen_gong_branch = _get_shen_gong_branch(lunar_month, hour_branch)

    # 五行局（使用納音五行）
    mg_stem = _get_ming_gong_stem(year_stem, ming_gong_branch)
    wu_xing_ju = _get_wu_xing_ju(mg_stem, ming_gong_branch)

    # 紫微星位置
    ziwei_branch = _get_ziwei_branch(lunar_day, wu_xing_ju)

    # 安主星
    stars_by_branch = _place_main_stars(ziwei_branch)

    # 安輔助星
    aux_by_branch = _place_auxiliary_stars(
        year_stem, year_branch, lunar_month, hour_branch, lunar_day
    )

    # 陰陽判斷
    yin_yang = "陽" if year_stem % 2 == 0 else "陰"
    is_yang_male_or_yin_female = (
        (yin_yang == "陽" and gender == "男") or
        (yin_yang == "陰" and gender == "女")
    )

    # 四化
    sihua = _compute_sihua(year_stem, stars_by_branch, aux_by_branch)

    # 命主 / 身主
    ming_zhu = MING_ZHU_TABLE[ming_gong_branch]
    shen_zhu = SHEN_ZHU_TABLE[year_branch]

    # 三合組
    sanhe_groups = _compute_sanhe_groups(ming_gong_branch)

    # 建立宮位
    palaces = _build_palaces(
        ming_gong_branch, year_stem, stars_by_branch, aux_by_branch,
        sihua, wu_xing_ju, is_yang_male_or_yin_female,
    )

    return ZiweiChart(
        year=year, month=month, day=day, hour=hour, minute=minute,
        timezone=timezone, latitude=latitude, longitude=longitude,
        location_name=location_name, julian_day=jd,
        gender=gender,
        lunar_year=lunar_year, lunar_month=lunar_month, lunar_day=lunar_day,
        is_leap_month=is_leap,
        lunar_year_stem=year_stem, lunar_year_branch=year_branch,
        hour_branch=hour_branch,
        ming_gong_branch=ming_gong_branch, shen_gong_branch=shen_gong_branch,
        wu_xing_ju=wu_xing_ju, ziwei_branch=ziwei_branch,
        yin_yang=yin_yang, ming_zhu=ming_zhu, shen_zhu=shen_zhu,
        sihua=sihua, palaces=palaces, sanhe_groups=sanhe_groups,
        vietnam_mode=vietnam_mode,
    )
