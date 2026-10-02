from datetime import date

import pytest

from app.domains.reports.generation.bazi_calculator import BaziCalculator
from app.domains.service_requests.schemas import ServiceProfileSnapshot
from app.domains.users.lunar_calendar import (
    lunar_calendar_options,
    lunar_year_options,
    solar_date_for_birth,
)
from app.domains.users.service import apply_user_profile_update
from app.services.intake_service import calculate_age


def make_user(**overrides):
    values = {
        "name": "林一",
        "gender": "female",
        "birth_year": 2023,
        "birth_month": 2,
        "birth_day": 1,
        "birth_is_leap_month": False,
        "birth_hour": None,
        "birth_minute": None,
        "birth_place": None,
        "calendar_type": "lunar",
        "birth_time_precision": "unknown",
        "profile_version": 1,
        "profile_last_confirmed_at": None,
    }
    values.update(overrides)
    return type("UserStub", (), values)()


def test_lunar_options_identify_leap_month_and_valid_day_count():
    options = lunar_year_options(2023, today=date(2024, 1, 1))
    leap_month = next(month for month in options["months"] if month["value"] == -2)

    assert leap_month == {
        "value": -2,
        "label": "闰二月",
        "day_count": 29,
        "max_day": 29,
    }


def test_lunar_options_cap_current_month_to_today():
    options = lunar_year_options(2023, today=date(2023, 3, 1))
    month_two = next(month for month in options["months"] if month["value"] == 2)

    assert month_two["max_day"] < month_two["day_count"]
    assert all(month["value"] != -2 for month in options["months"])


def test_lunar_calendar_options_include_years_through_current_lunar_year():
    options = lunar_calendar_options(today=date(2023, 3, 1))

    assert options["max_year"] == 2023
    assert options["years"][-1]["value"] == 2023
    assert not any(month["value"] == -2 for month in options["years"][-1]["months"])


def test_lunar_leap_date_converts_to_solar_date_and_rejects_invalid_months():
    assert solar_date_for_birth(
        2023, 2, 1, "lunar", is_leap_month=True, today=date(2024, 1, 1)
    ) == date(2023, 3, 22)

    with pytest.raises(ValueError, match="birth_date_invalid"):
        solar_date_for_birth(
            2022, 2, 1, "lunar", is_leap_month=True, today=date(2024, 1, 1)
        )


def test_lunar_profile_update_tracks_leap_month_and_rejects_invalid_days():
    user = make_user()
    changed = apply_user_profile_update(user, {"birth_is_leap_month": True})

    assert "birth_is_leap_month" in changed
    assert user.birth_is_leap_month is True
    assert user.profile_version == 2

    with pytest.raises(ValueError, match="birth_date_invalid"):
        apply_user_profile_update(
            make_user(birth_year=2022, birth_is_leap_month=False),
            {"birth_is_leap_month": True},
        )

    solar_user = make_user(birth_is_leap_month=True)
    apply_user_profile_update(solar_user, {"calendar_type": "solar"})
    assert solar_user.birth_is_leap_month is False


def test_age_uses_solar_equivalent_of_lunar_birthday():
    assert calculate_age(
        2023,
        2,
        1,
        today=date(2024, 3, 21),
        calendar_type="lunar",
        birth_is_leap_month=True,
    ) == 0
    assert calculate_age(
        2023,
        2,
        1,
        today=date(2024, 3, 22),
        calendar_type="lunar",
        birth_is_leap_month=True,
    ) == 1


def test_service_profile_schema_accepts_real_lunar_leap_date():
    profile = ServiceProfileSnapshot.model_validate(
        {
            "gender": "female",
            "birth_year": 2023,
            "birth_month": 2,
            "birth_day": 1,
            "birth_is_leap_month": True,
            "calendar_type": "lunar",
        }
    )

    assert profile.birth_is_leap_month is True


def test_bazi_calculation_uses_and_formats_lunar_leap_month():
    result = BaziCalculator().calculate_bazi(
        2023, 2, 1, is_solar=False, is_leap_month=True
    )

    assert result["lunar_date"] == "2023年闰二月1日"
    assert result["solar_date"] == "2023年3月22日"
