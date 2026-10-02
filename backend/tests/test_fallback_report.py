from app.domains.reports.generation.fallback_report import generate_basic_report


def test_basic_report_is_deterministic_and_includes_selected_topics():
    report = generate_basic_report(
        {
            "name": "林一",
            "birth_year": 2000,
            "birth_month": 1,
            "birth_day": 1,
            "selected_topics": ["career", "relationships"],
        }
    )

    assert report["basic_info"]["name"] == "林一"
    assert report["basic_info"]["generated_by"] == "Basic Algorithm"
    assert report["energy_profile"]["type"] == "稳定承载型"
    assert report["personal_growth"]["current_issues"] == [
        "关注career相关议题",
        "关注relationships相关议题",
    ]
    assert report["ai_generated_content"] is None
