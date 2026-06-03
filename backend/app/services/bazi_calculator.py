"""
八字和命理计算服务
使用 lunar-python 库进行确定性计算，替代AI随机生成
"""
from typing import Dict, Any, Optional
from lunar_python import Lunar, Solar
from datetime import datetime
import sys
import os

# Mock streamlit for ziwei calculation
class MockStreamlit:
    @staticmethod
    def cache_data(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

sys.modules['streamlit'] = MockStreamlit()

# Import ziwei calculator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tools.ziwei.ziwei import compute_ziwei_chart


class BaziCalculator:
    """八字计算器 - 使用lunar-python库"""

    # 十神关系映射 (基于日主与其他天干的关系)
    TEN_GODS_MAP = {
        # 日主为甲
        '甲': {'甲': '比肩', '乙': '劫财', '丙': '食神', '丁': '伤官', '戊': '偏财', '己': '正财', '庚': '七杀', '辛': '正官', '壬': '偏印', '癸': '正印'},
        # 日主为乙
        '乙': {'甲': '劫财', '乙': '比肩', '丙': '伤官', '丁': '食神', '戊': '正财', '己': '偏财', '庚': '正官', '辛': '七杀', '壬': '正印', '癸': '偏印'},
        # 日主为丙
        '丙': {'甲': '偏印', '乙': '正印', '丙': '比肩', '丁': '劫财', '戊': '食神', '己': '伤官', '庚': '偏财', '辛': '正财', '壬': '七杀', '癸': '正官'},
        # 日主为丁
        '丁': {'甲': '正印', '乙': '偏印', '丙': '劫财', '丁': '比肩', '戊': '伤官', '己': '食神', '庚': '正财', '辛': '偏财', '壬': '正官', '癸': '七杀'},
        # 日主为戊
        '戊': {'甲': '七杀', '乙': '正官', '丙': '偏印', '丁': '正印', '戊': '比肩', '己': '劫财', '庚': '食神', '辛': '伤官', '壬': '偏财', '癸': '正财'},
        # 日主为己
        '己': {'甲': '正官', '乙': '七杀', '丙': '正印', '丁': '偏印', '戊': '劫财', '己': '比肩', '庚': '伤官', '辛': '食神', '壬': '正财', '癸': '偏财'},
        # 日主为庚
        '庚': {'甲': '偏财', '乙': '正财', '丙': '七杀', '丁': '正官', '戊': '偏印', '己': '正印', '庚': '比肩', '辛': '劫财', '壬': '食神', '癸': '伤官'},
        # 日主为辛
        '辛': {'甲': '正财', '乙': '偏财', '丙': '正官', '丁': '七杀', '戊': '正印', '己': '偏印', '庚': '劫财', '辛': '比肩', '壬': '伤官', '癸': '食神'},
        # 日主为壬
        '壬': {'甲': '食神', '乙': '伤官', '丙': '偏财', '丁': '正财', '戊': '七杀', '己': '正官', '庚': '偏印', '辛': '正印', '壬': '比肩', '癸': '劫财'},
        # 日主为癸
        '癸': {'甲': '伤官', '乙': '食神', '丙': '正财', '丁': '偏财', '戊': '正官', '己': '七杀', '庚': '正印', '辛': '偏印', '壬': '劫财', '癸': '比肩'},
    }

    def __init__(self):
        pass

    def calculate_bazi(
        self,
        year: int,
        month: int,
        day: int,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        is_solar: bool = True
    ) -> Dict[str, Any]:
        """
        计算八字四柱

        Args:
            year: 年份
            month: 月份
            day: 日期
            hour: 小时 (可选)
            minute: 分钟 (可选)
            is_solar: 是否为公历 (True=公历, False=农历)

        Returns:
            包含八字信息的字典
        """
        try:
            # 创建日期对象
            if is_solar:
                if hour is not None and minute is not None:
                    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
                else:
                    solar = Solar.fromYmd(year, month, day)
                lunar = solar.getLunar()
            else:
                # 农历转换
                lunar = Lunar.fromYmd(year, month, day)
                solar = lunar.getSolar()

            # 获取四柱
            year_pillar = lunar.getYearInGanZhi()
            month_pillar = lunar.getMonthInGanZhi()
            day_pillar = lunar.getDayInGanZhi()

            # 日主 (日干)
            day_master = day_pillar[0] if day_pillar else ""

            # 时柱 (如果提供了时辰)
            hour_pillar = None
            if hour is not None:
                hour_pillar = lunar.getTimeInGanZhi()

            # 计算十神关系
            ten_gods = self._calculate_ten_gods(day_master, year_pillar, month_pillar, hour_pillar)

            # 获取其他信息
            zodiac = lunar.getYearShengXiao()
            nayin = lunar.getYearNaYin()

            result = {
                "year": {
                    "stem": year_pillar[0] if year_pillar else "",
                    "branch": year_pillar[1] if len(year_pillar) > 1 else "",
                    "pillar": year_pillar,
                    "ten_god": ten_gods.get("year", "")
                },
                "month": {
                    "stem": month_pillar[0] if month_pillar else "",
                    "branch": month_pillar[1] if len(month_pillar) > 1 else "",
                    "pillar": month_pillar,
                    "ten_god": ten_gods.get("month", "")
                },
                "day": {
                    "stem": day_pillar[0] if day_pillar else "",
                    "branch": day_pillar[1] if len(day_pillar) > 1 else "",
                    "pillar": day_pillar,
                    "ten_god": ""  # 日柱不标注十神
                },
                "hour": None,
                "day_master": day_master,
                "zodiac": zodiac,
                "nayin": nayin,
                "lunar_date": f"{lunar.getYear()}年{lunar.getMonth()}月{lunar.getDay()}日",
                "solar_date": f"{solar.getYear()}年{solar.getMonth()}月{solar.getDay()}日"
            }

            # 如果有时柱
            if hour_pillar:
                result["hour"] = {
                    "stem": hour_pillar[0] if hour_pillar else "",
                    "branch": hour_pillar[1] if len(hour_pillar) > 1 else "",
                    "pillar": hour_pillar,
                    "ten_god": ten_gods.get("hour", "")
                }

            return result

        except Exception as e:
            raise ValueError(f"八字计算失败: {str(e)}")

    def _calculate_ten_gods(
        self,
        day_master: str,
        year_pillar: str,
        month_pillar: str,
        hour_pillar: Optional[str]
    ) -> Dict[str, str]:
        """
        计算十神关系

        Args:
            day_master: 日主 (日干)
            year_pillar: 年柱
            month_pillar: 月柱
            hour_pillar: 时柱 (可选)

        Returns:
            十神关系字典
        """
        if day_master not in self.TEN_GODS_MAP:
            return {}

        ten_gods_for_day_master = self.TEN_GODS_MAP[day_master]
        result = {}

        # 年柱十神
        if year_pillar and len(year_pillar) > 0:
            year_stem = year_pillar[0]
            result["year"] = ten_gods_for_day_master.get(year_stem, "")

        # 月柱十神
        if month_pillar and len(month_pillar) > 0:
            month_stem = month_pillar[0]
            result["month"] = ten_gods_for_day_master.get(month_stem, "")

        # 时柱十神
        if hour_pillar and len(hour_pillar) > 0:
            hour_stem = hour_pillar[0]
            result["hour"] = ten_gods_for_day_master.get(hour_stem, "")

        return result

    def calculate_ziwei(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        gender: str,
        location: Optional[str] = None,
        latitude: float = 39.9,
        longitude: float = 116.4,
        is_solar: bool = True
    ) -> Dict[str, Any]:
        """
        计算紫微斗数命盘

        Args:
            year: 年份
            month: 月份
            day: 日期
            hour: 小时
            minute: 分钟
            gender: 性别 ('male' or 'female')
            location: 出生地点名称
            latitude: 纬度 (默认北京)
            longitude: 经度 (默认北京)
            is_solar: 是否为公历

        Returns:
            紫微斗数命盘信息
        """
        try:
            # 转换性别格式
            gender_cn = '男' if gender.lower() in ['male', '男'] else '女'

            # 如果是农历，先转换为公历
            if not is_solar:
                lunar = Lunar.fromYmd(year, month, day)
                solar = lunar.getSolar()
                year = solar.getYear()
                month = solar.getMonth()
                day = solar.getDay()

            # 调用紫微斗数计算
            chart = compute_ziwei_chart(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                timezone=8.0,  # 中国时区 UTC+8
                latitude=latitude,
                longitude=longitude,
                location_name=location or '中国',
                gender=gender_cn,
                vietnam_mode=False
            )

            # 地支和天干映射
            branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
            stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
            wu_xing_map = {2: '水二局', 3: '木三局', 4: '金四局', 5: '土五局', 6: '火六局'}
            palace_names = ['命宫', '兄弟宫', '夫妻宫', '子女宫', '财帛宫', '疾厄宫',
                           '迁移宫', '交友宫', '官禄宫', '田宅宫', '福德宫', '父母宫']
            main_stars = ['紫微', '天机', '太阳', '武曲', '天同', '廉贞',
                         '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军']

            # 提取关键宫位的主星
            def get_palace_main_stars(palace_index):
                if palace_index < len(chart.palaces):
                    palace = chart.palaces[palace_index]
                    return [s for s in palace.stars[:8] if s in main_stars]
                return []

            result = {
                "ming_zhu": chart.ming_zhu,
                "shen_zhu": chart.shen_zhu,
                "wu_xing_ju": wu_xing_map.get(chart.wu_xing_ju, '未知'),
                "ming_gong_branch": branches[chart.ming_gong_branch],
                "shen_gong_branch": branches[chart.shen_gong_branch],
                "ziwei_branch": branches[chart.ziwei_branch],
                "yin_yang": chart.yin_yang,
                "lunar_date": f"{chart.lunar_year}年{chart.lunar_month}月{chart.lunar_day}日",
                "lunar_year_stem_branch": f"{stems[chart.lunar_year_stem]}{branches[chart.lunar_year_branch]}",
                "life_palace": {
                    "branch": branches[chart.ming_gong_branch],
                    "main_stars": get_palace_main_stars(0)
                },
                "career_palace": {
                    "branch": branches[chart.palaces[8].branch] if len(chart.palaces) > 8 else "",
                    "main_stars": get_palace_main_stars(8)
                },
                "wealth_palace": {
                    "branch": branches[chart.palaces[4].branch] if len(chart.palaces) > 4 else "",
                    "main_stars": get_palace_main_stars(4)
                },
                "relationship_palace": {
                    "branch": branches[chart.palaces[2].branch] if len(chart.palaces) > 2 else "",
                    "main_stars": get_palace_main_stars(2)
                },
                "palaces": []
            }

            # 添加所有宫位信息
            for i, palace in enumerate(chart.palaces):
                palace_stars = [s for s in palace.stars[:8] if s in main_stars]
                result["palaces"].append({
                    "name": palace_names[i],
                    "branch": branches[palace.branch],
                    "main_stars": palace_stars
                })

            return result

        except Exception as e:
            raise ValueError(f"紫微斗数计算失败: {str(e)}")


# 全局实例
bazi_calculator = BaziCalculator()


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
        is_solar=is_solar
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
                is_solar=is_solar
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

    return result
