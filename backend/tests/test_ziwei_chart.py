import pytest

from app.domains.reports.generation.ziwei_chart import compute_ziwei_chart


@pytest.mark.parametrize(
    ("year", "month", "day", "hour", "expected_lunar_date"),
    [
        (2002, 2, 4, 0, (2001, 12, 23)),
        (2002, 2, 4, 7, (2001, 12, 23)),
        (2024, 2, 10, 0, (2024, 1, 1)),
    ],
)
def test_ziwei_lunar_date_uses_china_standard_time(
    year, month, day, hour, expected_lunar_date
):
    chart = compute_ziwei_chart(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=0,
        timezone=8.0,
        latitude=39.9,
        longitude=116.4,
        gender="男",
    )

    actual_lunar_date = (
        chart.lunar_year,
        chart.lunar_month,
        chart.lunar_day,
    )
    assert actual_lunar_date == expected_lunar_date
