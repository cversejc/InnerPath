from app.services.intake_prompt_context import (
    context_for_prompt,
    profile_context_for_prompt,
)


def test_prompt_context_renders_only_relevant_context_and_profile_fields():
    context = context_for_prompt(
        {
            "current_challenge": "想换工作",
            "expected_outcomes": ["方向指引", "行动建议"],
            "phone": "13800000000",
        }
    )
    profile = profile_context_for_prompt(
        {
            "mbti": "INFP",
            "personality_keywords": ["敏感", "好奇"],
            "phone": "13800000000",
        }
    )

    assert "当前困惑：想换工作" in context
    assert "期望获得：方向指引、行动建议" in context
    assert "MBTI：INFP" in profile
    assert "性格关键词：敏感、好奇" in profile
    assert "13800000000" not in context + profile
