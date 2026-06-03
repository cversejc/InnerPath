#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
紫微斗数计算服务模块

提供紫微斗数命盘计算功能，用于报告生成系统。
"""
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Mock streamlit before importing ziwei
class MockStreamlit:
    @staticmethod
    def cache_data(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

sys.modules['streamlit'] = MockStreamlit()

# 添加tools目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tools.ziwei.ziwei import compute_ziwei_chart


def calculate_ziwei_from_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从用户数据计算紫微斗数命盘

    Args:
        user_data: 用户数据字典，包含：
            - birth_date: 出生日期 (YYYY-MM-DD)
            - birth_time: 出生时间 (HH:MM，可选)
            - gender: 性别 ("男" 或 "女")
            - location: 出生地点 (可选)
            - latitude: 纬度 (可选，默认北京)
            - longitude: 经度 (可选，默认北京)
            - timezone: 时区 (可选，默认UTC+8)

    Returns:
        紫微斗数命盘数据字典

    Raises:
        ValueError: 如果输入数据格式不正确
        Exception: 如果计算过程出错
    """
    # 解析出生日期
    birth_date_str = user_data.get('birth_date')
    if not birth_date_str:
        raise ValueError("缺少出生日期 (birth_date)")

    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"出生日期格式不正确: {birth_date_str}，应为 YYYY-MM-DD")

    year = birth_date.year
    month = birth_date.month
    day = birth_date.day

    # 解析出生时间（可选）
    birth_time_str = user_data.get('birth_time')
    if birth_time_str:
        try:
            birth_time = datetime.strptime(birth_time_str, '%H:%M')
            hour = birth_time.hour
            minute = birth_time.minute
        except ValueError:
            raise ValueError(f"出生时间格式不正确: {birth_time_str}，应为 HH:MM")
    else:
        # 默认子时开始 (00:00)
        hour = 0
        minute = 0

    # 获取性别
    gender = user_data.get('gender', '男')
    if gender not in ['男', '女']:
        raise ValueError(f"性别必须是'男'或'女'，当前值: {gender}")

    # 获取地理位置信息（默认北京）
    latitude = user_data.get('latitude', 39.9)
    longitude = user_data.get('longitude', 116.4)
    timezone = user_data.get('timezone', 8.0)
    location_name = user_data.get('location', '北京')

    # 计算紫微斗数命盘
    chart = compute_ziwei_chart(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        gender=gender,
        vietnam_mode=False
    )

    # 转换为字典格式
    result = _chart_to_dict(chart)

    return result


def _chart_to_dict(chart) -> Dict[str, Any]:
    """
    将ZiweiChart对象转换为字典格式

    Args:
        chart: ZiweiChart对象

    Returns:
        命盘数据字典
    """
    # 天干地支名称
    stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    palace_names = ["命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
                    "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"]
    wu_xing_ju_names = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}

    # 基本信息
    result = {
        "basic_info": {
            "solar_date": f"{chart.year}年{chart.month}月{chart.day}日",
            "solar_time": f"{chart.hour:02d}:{chart.minute:02d}",
            "lunar_date": f"{chart.lunar_year}年{chart.lunar_month}月{chart.lunar_day}日",
            "is_leap_month": chart.is_leap_month,
            "gender": chart.gender,
        },
        "core_info": {
            "year_stem": stems[chart.lunar_year_stem],
            "year_branch": branches[chart.lunar_year_branch],
            "year_ganzhi": f"{stems[chart.lunar_year_stem]}{branches[chart.lunar_year_branch]}",
            "hour_branch": branches[chart.hour_branch],
            "ming_gong_branch": branches[chart.ming_gong_branch],
            "shen_gong_branch": branches[chart.shen_gong_branch],
            "wu_xing_ju": wu_xing_ju_names[chart.wu_xing_ju],
            "ziwei_branch": branches[chart.ziwei_branch],
            "yin_yang": chart.yin_yang,
            "ming_zhu": chart.ming_zhu,
            "shen_zhu": chart.shen_zhu,
        },
        "palaces": [],
        "sihua": chart.sihua,
    }

    # 十二宫位信息
    for i, palace in enumerate(chart.palaces):
        palace_info = {
            "name": palace_names[i],
            "branch": branches[palace.branch],
            "stars": palace.stars[:10],  # 前10颗星
            "main_stars": [s for s in palace.stars if s in [
                "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
                "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"
            ]],
        }
        result["palaces"].append(palace_info)

    return result


def format_ziwei_for_display(ziwei_data: Dict[str, Any]) -> str:
    """
    格式化紫微斗数数据为可读文本

    Args:
        ziwei_data: 紫微斗数数据字典

    Returns:
        格式化的文本
    """
    lines = []

    # 基本信息
    basic = ziwei_data["basic_info"]
    lines.append("【基本信息】")
    lines.append(f"公历: {basic['solar_date']} {basic['solar_time']}")
    lines.append(f"农历: {basic['lunar_date']}")
    if basic['is_leap_month']:
        lines.append("闰月: 是")
    lines.append(f"性别: {basic['gender']}")
    lines.append("")

    # 命盘核心
    core = ziwei_data["core_info"]
    lines.append("【命盘核心】")
    lines.append(f"年干支: {core['year_ganzhi']}")
    lines.append(f"时辰: {core['hour_branch']}时")
    lines.append(f"命宫: {core['ming_gong_branch']}")
    lines.append(f"身宫: {core['shen_gong_branch']}")
    lines.append(f"五行局: {core['wu_xing_ju']}")
    lines.append(f"紫微星位置: {core['ziwei_branch']}")
    lines.append(f"命主: {core['ming_zhu']}")
    lines.append(f"身主: {core['shen_zhu']}")
    lines.append("")

    # 十二宫位
    lines.append("【十二宫位】")
    for palace in ziwei_data["palaces"]:
        if palace["main_stars"]:
            stars_str = "、".join(palace["main_stars"])
            lines.append(f"{palace['name']} ({palace['branch']}): {stars_str}")

    return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_data = {
        "birth_date": "2002-02-04",
        "birth_time": "00:00",
        "gender": "男",
        "location": "北京",
    }

    print("=" * 80)
    print("紫微斗数计算测试")
    print("=" * 80)

    try:
        result = calculate_ziwei_from_user_data(test_data)
        print("\n计算成功！\n")
        print(format_ziwei_for_display(result))

        print("\n" + "=" * 80)
        print("SUCCESS")
        print("=" * 80)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
