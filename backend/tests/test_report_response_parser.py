import pytest

from app.domains.reports.generation.report_response_parser import (
    extract_chat_content,
    parse_ai_response,
)


def test_extract_chat_content_supports_text_and_content_parts():
    assert (
        extract_chat_content({"choices": [{"message": {"content": "  report text  "}}]})
        == "report text"
    )
    assert (
        extract_chat_content(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "first "},
                                "second",
                                {"type": "image", "image_url": "ignored"},
                            ]
                        }
                    }
                ]
            }
        )
        == "first second"
    )


@pytest.mark.parametrize(
    "response_data",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": "  "}, "finish_reason": "length"}]},
    ],
)
def test_extract_chat_content_rejects_missing_or_empty_content(response_data):
    with pytest.raises(ValueError):
        extract_chat_content(response_data)


def test_parse_ai_response_extracts_report_fields_and_keeps_defaults():
    content = """能量类型：稳步探索型
核心特质: 认真观察、逐步行动
## 五、总结与寄语
选择可以从小范围尝试开始。"""

    report = parse_ai_response(
        content,
        {
            "name": "林一",
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 15,
        },
    )

    assert report["basic_info"] == {
        "name": "林一",
        "birth_date": "1990-5-15",
        "report_date": None,
        "generated_by": "AI",
    }
    assert report["energy_profile"]["type"] == "稳步探索型"
    assert report["energy_profile"]["core_traits"] == "认真观察、逐步行动"
    assert report["summary"] == "选择可以从小范围尝试开始。"
    assert report["career_guidance"]["suitable_paths"]
