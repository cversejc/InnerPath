"""
Unit tests for report prompt construction.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.report_prompt import build_prompt


def test_build_prompt_requires_deterministic_foundation():
    with pytest.raises(ValueError, match="确定性命理基础"):
        build_prompt({
            "birth_year": 2002,
            "birth_month": 2,
            "birth_day": 4,
            "gender": "male",
        })


def test_build_prompt_instructs_ai_not_to_recalculate_chart():
    prompt = build_prompt({
        "birth_year": 2002,
        "birth_month": 2,
        "birth_day": 4,
        "birth_hour": 0,
        "birth_minute": 0,
        "gender": "male",
        "foundation_data": {
            "bazi": {
                "year": {"stem": "辛", "branch": "巳", "ten_god": "偏印"},
                "month": {"stem": "壬", "branch": "寅", "ten_god": "劫财"},
                "day": {"stem": "癸", "branch": "卯"},
                "hour": {"stem": "壬", "branch": "子", "ten_god": "劫财"},
                "day_master": "癸",
            },
            "calculation_method": "deterministic-mingli",
        },
    })

    assert "【确定性命理基础】" in prompt
    assert "不要重新排盘或改写四柱/宫位" in prompt
    assert "请实际推算八字和紫微命盘" not in prompt
