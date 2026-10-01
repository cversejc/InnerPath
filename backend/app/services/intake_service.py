"""Shared profile and application-intake helpers.

The application layer stores a reusable user profile separately from the
short-lived context of a report or calendar request.  This module is the
single place where that distinction is converted into an immutable snapshot
for background jobs and downstream analysis.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Optional

from app.models.user import User


PROFILE_SNAPSHOT_FIELDS = (
    "name",
    "gender",
    "birth_year",
    "birth_month",
    "birth_day",
    "birth_hour",
    "birth_minute",
    "birth_place",
    "calendar_type",
    "birth_time_precision",
    "current_residence",
    "marital_status",
    "occupation_status",
    "highest_education",
    "mbti",
    "personality_keywords",
    "strengths",
    "limitations",
    "mingli_experience",
    "mingli_attitude",
    "preferred_content_depth",
    "default_usage_scenarios",
)

CONTEXT_FIELDS = (
    "focus_topics",
    "current_challenge",
    "expected_outcomes",
    "issue_duration",
    "impact_level",
    "decision_status",
    "decision_description",
    "decision_style",
    "additional_info",
)

LIST_CONTEXT_FIELDS = {"focus_topics", "expected_outcomes", "decision_style"}


def _list_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (tuple, list)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def profile_snapshot(user: User) -> dict[str, Any]:
    """Return the profile fields safe to store in an analysis snapshot.

    Contact credentials are intentionally excluded.  The snapshot contains
    only information required for the product's analytical workflows.
    """
    snapshot: dict[str, Any] = {}
    for field in PROFILE_SNAPSHOT_FIELDS:
        value = getattr(user, field, None)
        if field in {
            "personality_keywords",
            "mingli_experience",
            "default_usage_scenarios",
        }:
            value = _list_value(value)
        snapshot[field] = value
    return snapshot


def normalize_context(
    context: Optional[Mapping[str, Any]] = None,
    *,
    selected_topics: Optional[list[str]] = None,
    additional_info: Optional[str] = None,
) -> dict[str, Any]:
    """Normalize new context objects and legacy report fields alike."""
    source = dict(context or {})
    if selected_topics is not None and "focus_topics" not in source:
        source["focus_topics"] = selected_topics
    if additional_info is not None and "additional_info" not in source:
        source["additional_info"] = additional_info

    normalized: dict[str, Any] = {}
    for field in CONTEXT_FIELDS:
        value = source.get(field)
        if field in LIST_CONTEXT_FIELDS:
            normalized[field] = _list_value(value)
        elif isinstance(value, str):
            normalized[field] = value.strip() or None
        else:
            normalized[field] = value
    return normalized


def calculate_age(
    birth_year: Optional[int],
    birth_month: Optional[int],
    birth_day: Optional[int],
    today: Optional[date] = None,
) -> Optional[int]:
    if not all(value is not None for value in (birth_year, birth_month, birth_day)):
        return None
    try:
        current = today or date.today()
        birthday = date(int(birth_year), int(birth_month), int(birth_day))
        return max(
            0,
            current.year
            - birthday.year
            - ((current.month, current.day) < (birthday.month, birthday.day)),
        )
    except (TypeError, ValueError):
        return None


def build_intake_snapshot(
    user: User,
    context: Optional[Mapping[str, Any]] = None,
    *,
    request_type: str,
    profile_version: Optional[int] = None,
    source_report_id: Optional[int] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical immutable snapshot for a request or background job."""
    if profile_version is not None and int(profile_version) != int(
        user.profile_version or 1
    ):
        raise ValueError("profile_version_conflict")

    normalized_context = normalize_context(context)
    snapshot: dict[str, Any] = {
        "schema_version": 2,
        "request_type": request_type,
        "profile_version": int(user.profile_version or 1),
        "profile": profile_snapshot(user),
        "context": normalized_context,
        "derived": {
            "age_at_request": calculate_age(
                user.birth_year, user.birth_month, user.birth_day
            ),
        },
    }
    if source_report_id is not None:
        snapshot["source_report_id"] = source_report_id
    if extra:
        snapshot.update(dict(extra))
    return snapshot


def flatten_snapshot_for_ai(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Expose the legacy flat keys expected by the existing AI pipeline."""
    profile = dict(snapshot.get("profile") or {})
    context = normalize_context(snapshot.get("context") or {})
    flattened = dict(profile)
    flattened.update(
        {
            "schema_version": snapshot.get("schema_version", 2),
            "profile_version": snapshot.get("profile_version"),
            "request_type": snapshot.get("request_type", "report"),
            "context": context,
            "derived": snapshot.get("derived") or {},
            "selected_topics": context["focus_topics"],
            "additional_info": context.get("additional_info"),
        }
    )
    return flattened
