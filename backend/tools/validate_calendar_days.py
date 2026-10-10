"""Validate that a generated calendar covers its full date range once per day.

Usage:

    python report_calendar_operator.py get-json --user-id 5 \
        --path /calendar/me > /tmp/calendar.json
    python validate_calendar_days.py /tmp/calendar.json

Exits non-zero when days are missing, duplicated, empty or lack windows,
energy_awareness, tone_explanation or action_refs. The operator's
calendar-verify command performs the same checks directly against the API.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path


def iter_days(payload: dict) -> list[dict]:
    items = payload.get("items")
    if items is None:
        items = payload.get("calendars") or []
    return items


def main() -> int:
    raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    payload = json.loads(raw)
    items = iter_days(payload)
    exit_code = 0
    for item in items:
        start = dt.date.fromisoformat(item["start_date"])
        end = dt.date.fromisoformat(item["end_date"])
        expected = [
            (start + dt.timedelta(days=offset)).isoformat()
            for offset in range((end - start).days + 1)
        ]
        meta = item.get("meta_payload") or {}
        details = meta.get("daily_details") or {}
        keys = sorted(details.keys())
        missing = [day for day in expected if day not in details]
        unexpected = [day for day in keys if day not in expected]
        empty = [
            day
            for day in expected
            if day in details
            and not (details[day].get("windows") or details[day].get("suitable"))
        ]
        thin_windows = [
            day for day in expected if day in details and len(details[day].get("windows") or []) < 2
        ]
        missing_awareness = [
            day
            for day in expected
            if day in details and not str(details[day].get("energy_awareness") or "").strip()
        ]
        missing_tone = [
            day
            for day in expected
            if day in details
            and not str(details[day].get("tone_explanation") or "").strip()
        ]
        missing_refs = [
            day for day in expected if day in details and not (details[day].get("action_refs") or [])
        ]
        print(
            json.dumps(
                {
                    "calendar_id": item.get("id"),
                    "status": item.get("status"),
                    "start": item["start_date"],
                    "end": item["end_date"],
                    "expected_days": len(expected),
                    "actual_days": len(keys),
                    "first": keys[0] if keys else None,
                    "last": keys[-1] if keys else None,
                    "missing": missing,
                    "unexpected": unexpected,
                    "empty_days": empty,
                    "days_with_fewer_than_2_windows": thin_windows,
                    "days_missing_energy_awareness": missing_awareness,
                    "days_missing_tone_explanation": missing_tone,
                    "days_missing_action_refs": missing_refs,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if (
            len(keys) != len(expected)
            or missing
            or unexpected
            or empty
            or thin_windows
            or missing_awareness
            or missing_tone
            or missing_refs
        ):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
