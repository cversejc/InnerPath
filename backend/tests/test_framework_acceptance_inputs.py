from tools.run_framework_acceptance import sample_input


def test_caregiving_case_varies_profile_goals_and_realistic_time_constraints():
    baseline = sample_input("full")
    case = sample_input("caregiving_short")
    evidence = {item["evidence_key"]: item["value"] for item in case["evidence"]}

    assert case["profile"]["gender"] == "male"
    assert case["profile"]["birth_year"] != baseline["profile"]["birth_year"]
    assert case["profile"]["mbti"] == "ISTJ"
    assert case["profile"]["preferred_content_depth"] == "简洁清楚"
    assert case["context"]["focus_topics"] == ["career_transition", "family_responsibility"]
    assert case["context"]["available_time"].startswith("轮班工作日通常只有8分钟")
    assert "不能把所有延迟都解释成讨好或害怕权威" in case["context"]["counterexample"]
    assert evidence["input.profile.mbti"] == "ISTJ"
    assert evidence["input.context.available_time"] == case["context"]["available_time"]
    assert case["profile"]["birth_time_precision"] == "exact"
    assert case["context"]["synthetic_notice"]
