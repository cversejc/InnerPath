from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.admin_service_sla import (
    get_admin_report_request_sla,
    summarize_report_request_sla,
)


def test_report_request_sla_reports_response_and_delivery_percentiles_by_direction():
    created = datetime(2026, 9, 1)
    now = created + timedelta(days=2)
    rows = [
        ("metaphysics", created, created + timedelta(hours=2), created + timedelta(hours=10), "delivered"),
        ("metaphysics", created, created + timedelta(hours=30), created + timedelta(hours=54), "delivered"),
        ("psychology", created, created + timedelta(hours=4), None, "accepted"),
        ("integrated", created, None, None, "submitted"),
        ("psychology", now - timedelta(hours=12), None, None, "submitted"),
    ]

    metrics = summarize_report_request_sla(rows, now=now)
    overall = metrics["items"][0]
    metaphysics = next(item for item in metrics["items"] if item["consultation_type"] == "metaphysics")
    psychology = next(item for item in metrics["items"] if item["consultation_type"] == "psychology")
    integrated = next(item for item in metrics["items"] if item["consultation_type"] == "integrated")

    assert overall["request_count"] == 5
    assert overall["accepted_samples"] == 3
    assert overall["response_sla_samples"] == 4
    assert overall["overdue_unaccepted"] == 1
    assert overall["response_within_24h_rate"] == 50
    assert overall["response_p50_hours"] == 4
    assert overall["response_p90_hours"] == 30
    assert overall["delivery_samples"] == 2
    assert overall["delivery_p50_hours"] == 16
    assert overall["delivery_p90_hours"] == 24
    assert metaphysics["delivery_samples"] == 2
    assert psychology["delivery_samples"] == 0
    assert integrated["response_within_24h_rate"] == 0
    assert integrated["response_sla_samples"] == 1


def test_report_request_sla_ignores_negative_or_timezone_inconsistent_durations():
    created = datetime(2026, 9, 1)
    aware = datetime(2026, 9, 1, tzinfo=timezone.utc)
    metrics = summarize_report_request_sla(
        [
            ("metaphysics", created, created - timedelta(hours=1), created, "delivered"),
            ("psychology", created, aware, None, "accepted"),
        ],
        now=created + timedelta(days=2),
    )

    assert metrics["items"][0]["accepted_samples"] == 0
    assert metrics["items"][0]["delivery_samples"] == 0
    assert metrics["items"][0]["response_within_24h_rate"] is None


def test_report_request_sla_returns_no_groups_for_an_empty_period():
    assert summarize_report_request_sla([]) == {"items": []}


@pytest.mark.asyncio
async def test_admin_report_request_sla_queries_only_report_requests_in_period():
    class Result:
        def all(self):
            return [("metaphysics", datetime(2026, 9, 1), None, None, "submitted")]

    db = SimpleNamespace(execute=AsyncMock(return_value=Result()))
    start_at = datetime(2026, 9, 1)
    end_at = datetime(2026, 10, 1)

    metrics = await get_admin_report_request_sla(db, start_at=start_at, end_at=end_at)

    assert metrics["items"][0]["request_count"] == 1
    statement = db.execute.await_args.args[0]
    assert "service_requests.service_type =" in str(statement)
    assert "service_requests.created_at >=" in str(statement)
    assert "service_requests.created_at <" in str(statement)
