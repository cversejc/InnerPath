from datetime import date
from types import SimpleNamespace

import pytest

from app.services.intake_service import (
    build_intake_snapshot,
    calculate_age,
    flatten_snapshot_for_ai,
    normalize_context,
    profile_snapshot,
)
from app.domains.users.service import apply_user_profile_update


def make_user(**overrides):
    values = {
        "name": "林一",
        "phone": "13800000000",
        "gender": "female",
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 15,
        "birth_is_leap_month": False,
        "birth_hour": 8,
        "birth_minute": 30,
        "birth_place": "广东省广州市",
        "calendar_type": "solar",
        "birth_time_precision": "exact",
        "current_residence": "上海市",
        "marital_status": "single",
        "occupation_status": "full_time",
        "highest_education": "bachelor",
        "mbti": "INFP",
        "personality_keywords": ["敏感", "好奇"],
        "strengths": "善于倾听",
        "limitations": "容易犹豫",
        "mingli_experience": [],
        "mingli_attitude": "reference",
        "preferred_content_depth": "balanced",
        "default_usage_scenarios": ["before_decision"],
        "profile_version": 3,
        "profile_last_confirmed_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_profile_snapshot_excludes_contact_fields():
    snapshot = profile_snapshot(make_user())

    assert snapshot["name"] == "林一"
    assert snapshot["birth_place"] == "广东省广州市"
    assert "phone" not in snapshot
    assert "password_hash" not in snapshot


def test_snapshot_contains_version_context_and_derived_age():
    user = make_user()
    snapshot = build_intake_snapshot(
        user,
        {
            "focus_topics": ["career"],
            "current_challenge": "想转行但还没有方向",
            "expected_outcomes": ["方向指引"],
        },
        request_type="report",
        profile_version=3,
    )

    assert snapshot["schema_version"] == 2
    assert snapshot["profile_version"] == 3
    assert snapshot["context"]["focus_topics"] == ["career"]
    assert snapshot["derived"]["age_at_request"] is not None
    assert "phone" not in snapshot["profile"]


def test_profile_version_conflict_is_rejected():
    with pytest.raises(ValueError, match="profile_version_conflict"):
        build_intake_snapshot(make_user(profile_version=4), {}, request_type="report", profile_version=3)


def test_flatten_snapshot_keeps_legacy_ai_keys_without_phone():
    snapshot = build_intake_snapshot(
        make_user(),
        {"focus_topics": ["health"], "additional_info": "希望节奏温和"},
        request_type="report",
    )
    flattened = flatten_snapshot_for_ai(snapshot)

    assert flattened["selected_topics"] == ["health"]
    assert flattened["additional_info"] == "希望节奏温和"
    assert "phone" not in flattened


def test_legacy_context_normalization_keeps_topics_and_additional_info():
    context = normalize_context(selected_topics=["career"], additional_info="希望节奏温和")

    assert context["focus_topics"] == ["career"]
    assert context["additional_info"] == "希望节奏温和"


def test_age_is_derived_from_birthday():
    assert calculate_age(2000, 9, 15, today=date(2026, 9, 14)) == 25
    assert calculate_age(2000, 9, 14, today=date(2026, 9, 14)) == 26


def test_profile_update_increments_version_and_unknown_time_clears_time():
    user = make_user(profile_version=1)

    changed = apply_user_profile_update(
        user,
        {
            "preferred_content_depth": "deep",
            "birth_time_precision": "unknown",
        },
    )

    assert "preferred_content_depth" in changed
    assert user.profile_version == 2
    assert user.birth_hour is None
    assert user.birth_minute is None
    assert user.profile_last_confirmed_at is not None


def test_partial_time_is_rejected():
    with pytest.raises(ValueError, match="birth_time_requires_hour_and_minute"):
        apply_user_profile_update(make_user(birth_minute=None), {"birth_time_precision": "exact", "birth_hour": 9})


def test_exact_precision_requires_existing_time():
    with pytest.raises(ValueError, match="birth_time_requires_hour_and_minute"):
        apply_user_profile_update(
            make_user(birth_hour=None, birth_minute=None),
            {"birth_time_precision": "exact"},
        )


def test_invalid_solar_date_is_rejected():
    with pytest.raises(ValueError, match="birth_date_invalid"):
        apply_user_profile_update(make_user(), {"birth_month": 2, "birth_day": 31})
