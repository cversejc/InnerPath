from app.domains.reports.generation.report_prompt import build_prompt


def test_prompt_uses_current_context_and_never_includes_phone():
    prompt = build_prompt(
        {
            "name": "林一",
            "phone": "13800000000",
            "gender": "female",
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 15,
            "birth_hour": None,
            "birth_minute": None,
            "mbti": "INFP",
            "selected_topics": ["career"],
            "context": {
                "focus_topics": ["career"],
                "current_challenge": "想转行但不确定方向",
                "expected_outcomes": ["找到方向"],
                "issue_duration": "近半年",
            },
            "foundation_data": {"bazi": {"day_master": "甲"}},
        }
    )

    assert "想转行但不确定方向" in prompt
    assert "近半年" in prompt
    assert "MBTI：INFP" in prompt
    assert "13800000000" not in prompt
