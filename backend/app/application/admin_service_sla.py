"""Read-only report request timing metrics for the admin dashboard."""

from datetime import datetime
from math import ceil
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest


CONSULTATION_TYPES = ("metaphysics", "psychology", "integrated", "unspecified")
CLOSED_REQUEST_STATUSES = ("delivered", "withdrawn", "rejected")


def _elapsed_hours(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    if (start.tzinfo is None) != (end.tzinfo is None):
        return None
    elapsed = (end - start).total_seconds() / 3600
    return elapsed if elapsed >= 0 else None


def _percentile90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(ceil(len(ordered) * 0.9) - 1, 0)]


def summarize_report_request_sla(rows, *, now: datetime | None = None) -> dict:
    rows = list(rows)
    if not rows:
        return {"items": []}
    current_time = now or datetime.utcnow()
    grouped = {"overall": []}
    for row in rows:
        consultation_type = row[0] or "unspecified"
        grouped.setdefault(consultation_type, []).append(row)
        grouped["overall"].append(row)

    type_order = ["overall", *CONSULTATION_TYPES]
    type_order.extend(sorted(set(grouped) - set(type_order)))
    items = []
    for consultation_type in type_order:
        requests = grouped.get(consultation_type)
        if requests is None:
            continue

        response_hours = []
        delivery_hours = []
        responses_within_24h = 0
        response_sla_samples = 0
        overdue_unaccepted = 0
        for _kind, created_at, accepted_at, delivered_at, status in requests:
            response = _elapsed_hours(created_at, accepted_at)
            if response is not None:
                response_hours.append(response)
                response_sla_samples += 1
                responses_within_24h += response <= 24
            elif accepted_at is None and status not in CLOSED_REQUEST_STATUSES:
                request_age = _elapsed_hours(created_at, current_time)
                if request_age is not None and request_age >= 24:
                    response_sla_samples += 1
                    overdue_unaccepted += 1
            delivery = (
                _elapsed_hours(accepted_at, delivered_at)
                if response is not None
                else None
            )
            if delivery is not None:
                delivery_hours.append(delivery)

        response_samples = len(response_hours)
        items.append(
            {
                "consultation_type": consultation_type,
                "request_count": len(requests),
                "accepted_samples": response_samples,
                "response_sla_samples": response_sla_samples,
                "overdue_unaccepted": overdue_unaccepted,
                "response_within_24h_rate": (
                    round(responses_within_24h * 100 / response_sla_samples, 1)
                    if response_sla_samples
                    else None
                ),
                "response_p50_hours": round(median(response_hours), 1)
                if response_hours
                else None,
                "response_p90_hours": round(_percentile90(response_hours), 1)
                if response_hours
                else None,
                "delivery_samples": len(delivery_hours),
                "delivery_p50_hours": round(median(delivery_hours), 1)
                if delivery_hours
                else None,
                "delivery_p90_hours": round(_percentile90(delivery_hours), 1)
                if delivery_hours
                else None,
            }
        )
    return {"items": items}


async def get_admin_report_request_sla(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    now: datetime | None = None,
) -> dict:
    current_time = now or datetime.utcnow()
    result = await db.execute(
        select(
            ServiceRequest.consultation_type,
            ServiceRequest.created_at,
            ServiceRequest.accepted_at,
            ServiceRequest.delivered_at,
            ServiceRequest.status,
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.created_at >= start_at,
            ServiceRequest.created_at < end_at,
        )
    )
    return summarize_report_request_sla(result.all(), now=current_time)
