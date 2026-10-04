import re
from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AISkillVersion, SkillExample, SkillRun
from .builtin_examples import EXAMPLES


RETRIEVAL_POLICY = "tag-scenario-quality-v2"
MINIMUM_PUBLISHED_QUALITY = 0.6
MAXIMUM_EXAMPLES = 3
_APPLICABILITY_KEYS = {"focus_topics", "usage_scenario", "decision_status"}
_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CHINA_ID = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?(?!\d)")
_SENSITIVE_FIELDS = {
    "name",
    "phone",
    "phone_number",
    "mobile",
    "email",
    "address",
    "birth_date",
    "birth_year",
    "birth_month",
    "birth_day",
    "birth_hour",
    "birth_minute",
    "birth_place",
    "birth_address",
    "birth_city",
    "birth_province",
    "birth_country",
    "current_address",
    "current_city",
    "current_residence",
    "home_address",
    "residence",
    "city",
    "province",
    "region",
    "district",
    "postal_code",
    "zip_code",
    "latitude",
    "longitude",
    "user_id",
    "report_case_id",
    "source_case_id",
    "source_report_id",
    "report_version_id",
    "source_report_version_id",
    "calendar_request_id",
    "id",
}


def _known_names(run: SkillRun | None) -> set[str]:
    if run is None:
        return set()
    names = set()
    for snapshot in (run.input_snapshot or {}, run.context_snapshot or {}):
        profile = snapshot.get("profile") or {}
        name = profile.get("name")
        if isinstance(name, str) and len(name.strip()) >= 2:
            names.add(name.strip())
    return names


def scrub_example_data(value: Any, *, known_names: set[str] | None = None) -> Any:
    names = known_names or set()
    if isinstance(value, dict):
        return {
            key: scrub_example_data(item, known_names=names)
            for key, item in value.items()
            if str(key).casefold() not in _SENSITIVE_FIELDS
        }
    if isinstance(value, list):
        return [scrub_example_data(item, known_names=names) for item in value]
    if isinstance(value, tuple):
        return [scrub_example_data(item, known_names=names) for item in value]
    if not isinstance(value, str):
        return value

    result = value
    for name in sorted(names, key=len, reverse=True):
        result = result.replace(name, "[用户]")
    result = _PHONE.sub("[手机号]", result)
    result = _EMAIL.sub("[邮箱]", result)
    result = _CHINA_ID.sub("[证件号]", result)
    result = _DATE.sub("[日期]", result)
    return result


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        value = re.sub(r"[^\w.-]", "_", str(tag).strip().casefold())[:40].strip("_.-")
        if value and value not in normalized:
            normalized.append(value)
    return normalized[:12]


async def create_example_candidate(
    db: AsyncSession,
    *,
    report_case_id: int | None,
    skill_run: SkillRun,
    example_type: str,
    scenario_tags: list[str],
    teaching_points: list[str],
    expected_output: dict[str, Any] | None,
    created_by: int,
) -> SkillExample:
    if skill_run.report_case_id != report_case_id:
        raise ValueError("skill_example_source_run_mismatch")
    if skill_run.status != "COMPLETED":
        raise ValueError("skill_example_source_run_not_completed")
    skill = await db.get(AISkillVersion, skill_run.skill_version_id)
    if skill is None:
        raise ValueError("skill_version_not_found")
    now = datetime.utcnow()
    known_names = _known_names(skill_run)
    input_context = scrub_example_data(skill_run.input_snapshot or {}, known_names=known_names)
    output = expected_output if expected_output is not None else (skill_run.output_parsed or {})
    row = SkillExample(
        skill_key=skill.skill_key,
        target_fragment_key=(
            skill_run.target_key if skill_run.target_type == "REPORT_FRAGMENT" else None
        ),
        example_key=uuid4().hex,
        version_no=1,
        status="CANDIDATE",
        example_type=example_type,
        scenario_tags=_normalize_tags(scenario_tags),
        applicability_json={},
        input_context=input_context,
        expected_output=scrub_example_data(output, known_names=known_names),
        teaching_points=scrub_example_data(teaching_points, known_names=known_names),
        anti_patterns=[],
        quality_score=None,
        source_case_id=report_case_id,
        source_skill_run_id=skill_run.id,
        deidentified=False,
        created_by=created_by,
        created_at=now,
    )
    db.add(row)
    await db.flush()
    return row


async def update_example_redaction(
    db: AsyncSession,
    *,
    example_id: int,
    target_fragment_key: str | None,
    scenario_tags: list[str],
    applicability_json: dict[str, Any],
    input_context: dict[str, Any],
    expected_output: dict[str, Any],
    teaching_points: list[str],
    anti_patterns: list[str],
    quality_score: float,
    confirmed_deidentified: bool,
) -> SkillExample:
    row = await db.scalar(
        select(SkillExample).where(SkillExample.id == example_id).with_for_update()
    )
    if row is None:
        raise ValueError("skill_example_not_found")
    if row.status != "CANDIDATE":
        raise ValueError("skill_example_immutable")
    normalized_applicability = _normalize_applicability(applicability_json)
    source_run = (
        await db.get(SkillRun, row.source_skill_run_id)
        if row.source_skill_run_id is not None
        else None
    )
    known_names = _known_names(source_run)
    row.target_fragment_key = target_fragment_key
    row.scenario_tags = _normalize_tags(scenario_tags)
    row.applicability_json = scrub_example_data(
        normalized_applicability, known_names=known_names
    )
    row.input_context = scrub_example_data(input_context, known_names=known_names)
    row.expected_output = scrub_example_data(expected_output, known_names=known_names)
    row.teaching_points = scrub_example_data(teaching_points, known_names=known_names)
    row.anti_patterns = scrub_example_data(anti_patterns, known_names=known_names)
    row.quality_score = quality_score
    row.deidentified = bool(confirmed_deidentified)
    await db.flush()
    return row


async def create_example_revision(
    db: AsyncSession, example_id: int, *, created_by: int
) -> SkillExample:
    source = await db.scalar(
        select(SkillExample).where(SkillExample.id == example_id).with_for_update()
    )
    if source is None:
        raise ValueError("skill_example_not_found")
    if source.status not in {"PUBLISHED", "RETIRED"}:
        raise ValueError("skill_example_revision_requires_published_source")
    latest_version = await db.scalar(
        select(func.max(SkillExample.version_no)).where(
            SkillExample.example_key == source.example_key
        )
    )
    row = SkillExample(
        skill_key=source.skill_key,
        target_fragment_key=source.target_fragment_key,
        example_key=source.example_key,
        version_no=(latest_version or source.version_no) + 1,
        status="CANDIDATE",
        example_type=source.example_type,
        scenario_tags=deepcopy(source.scenario_tags or []),
        applicability_json=deepcopy(source.applicability_json or {}),
        input_context=deepcopy(source.input_context or {}),
        expected_output=deepcopy(source.expected_output or {}),
        teaching_points=deepcopy(source.teaching_points or []),
        anti_patterns=deepcopy(source.anti_patterns or []),
        quality_score=source.quality_score,
        source_case_id=source.source_case_id,
        source_skill_run_id=source.source_skill_run_id,
        deidentified=False,
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def publish_skill_example(
    db: AsyncSession, example_id: int, *, reviewed_by: int
) -> SkillExample:
    row = await db.scalar(
        select(SkillExample).where(SkillExample.id == example_id).with_for_update()
    )
    if row is None:
        raise ValueError("skill_example_not_found")
    if row.status != "CANDIDATE":
        raise ValueError("skill_example_not_candidate")
    if not row.deidentified:
        raise ValueError("skill_example_deidentification_required")
    if (row.quality_score or 0) < MINIMUM_PUBLISHED_QUALITY:
        raise ValueError("skill_example_quality_too_low")
    if not row.expected_output or not row.teaching_points:
        raise ValueError("skill_example_content_required")
    _normalize_applicability(row.applicability_json or {})
    bundled = EXAMPLES.get(row.skill_key)
    is_synthetic_builtin = bundled is not None and bundled[0] == row.example_key
    if not is_synthetic_builtin and row.source_skill_run_id is None:
        raise ValueError("skill_example_source_required")
    source_run = await db.get(SkillRun, row.source_skill_run_id) if row.source_skill_run_id else None
    if not is_synthetic_builtin and (
        source_run is None
        or source_run.status != "COMPLETED"
        or source_run.report_case_id != row.source_case_id
        or (row.source_case_id is None and source_run.target_type != "CALENDAR_PRODUCTION")
    ):
        raise ValueError("skill_example_source_invalid")

    previous = await db.scalars(
        select(SkillExample)
        .where(
            SkillExample.example_key == row.example_key,
            SkillExample.status == "PUBLISHED",
        )
        .with_for_update()
    )
    now = datetime.utcnow()
    for version in previous:
        version.status = "RETIRED"
    await db.flush()
    row.status = "PUBLISHED"
    row.reviewed_by = reviewed_by
    row.published_at = now
    await db.flush()
    return row


async def retire_skill_example(db: AsyncSession, example_id: int) -> SkillExample:
    row = await db.scalar(
        select(SkillExample).where(SkillExample.id == example_id).with_for_update()
    )
    if row is None:
        raise ValueError("skill_example_not_found")
    if row.status == "RETIRED":
        raise ValueError("skill_example_already_retired")
    row.status = "RETIRED"
    await db.flush()
    return row


async def list_skill_examples(
    db: AsyncSession,
    *,
    skill_key: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[SkillExample]:
    query = select(SkillExample)
    if skill_key:
        query = query.where(SkillExample.skill_key == skill_key)
    if status:
        query = query.where(SkillExample.status == status)
    rows = await db.scalars(
        query.order_by(SkillExample.created_at.desc(), SkillExample.id.desc()).limit(limit)
    )
    return list(rows)


async def retrieve_skill_examples(
    db: AsyncSession,
    *,
    skill_key: str,
    target_key: str | None,
    context: dict[str, Any],
    max_examples: int = MAXIMUM_EXAMPLES,
) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    focus_topics = {
        str(topic).casefold()
        for topic in (context.get("focus_topics") or [])
        if isinstance(topic, str)
    }
    rows = await db.scalars(
        select(SkillExample)
        .where(
            SkillExample.skill_key == skill_key,
            SkillExample.status == "PUBLISHED",
            SkillExample.deidentified.is_(True),
            SkillExample.quality_score >= MINIMUM_PUBLISHED_QUALITY,
        )
        .order_by(SkillExample.quality_score.desc(), SkillExample.published_at.desc())
        .limit(100)
    )
    ranked = []
    for row in rows:
        if row.target_fragment_key and row.target_fragment_key != target_key:
            continue
        if not _matches_applicability(row.applicability_json or {}, context):
            continue
        tags = set(row.scenario_tags or [])
        matching_tags = tags & focus_topics
        if tags and focus_topics and not matching_tags:
            continue
        score = (row.quality_score or 0) * 0.5
        if row.target_fragment_key == target_key and target_key:
            score += 0.3
        if matching_tags:
            score += min(0.2, 0.1 * len(matching_tags))
        reasons = []
        if row.target_fragment_key == target_key and target_key:
            reasons.append("fragment_match")
        if matching_tags:
            reasons.append("scenario_tag_match")
        if not reasons:
            reasons.append("quality_fallback")
        ranked.append((score, row, reasons))
    ranked.sort(key=lambda item: (item[0], item[1].published_at or datetime.min), reverse=True)

    selected = []
    seen_scenarios = set()
    for score, row, reasons in ranked:
        scenario = tuple(sorted(row.scenario_tags or []))
        if scenario and scenario in seen_scenarios:
            continue
        seen_scenarios.add(scenario)
        snapshot = {
            "example_type": row.example_type,
            "target_fragment_key": row.target_fragment_key,
            "scenario_tags": row.scenario_tags or [],
            "input_context": row.input_context or {},
            "expected_output": row.expected_output or {},
            "teaching_points": row.teaching_points or [],
            "anti_patterns": row.anti_patterns or [],
        }
        selected.append(
            {
                "example_id": row.id,
                "example_key": row.example_key,
                "version_no": row.version_no,
                "retrieval_score": round(score, 4),
                "retrieval_policy": RETRIEVAL_POLICY,
                "selection_reasons": reasons,
                "example_snapshot": snapshot,
            }
        )
        if len(selected) >= min(max_examples, MAXIMUM_EXAMPLES):
            break
    return selected


def _matches_applicability(
    requirements: dict[str, Any], context: dict[str, Any]
) -> bool:
    """Match the small, explicit applicability contract used during review."""
    for key, expected in requirements.items():
        if key == "focus_topics":
            actual = {
                str(value).casefold()
                for value in context.get("focus_topics") or []
                if isinstance(value, str)
            }
            wanted_values = expected if isinstance(expected, list) else [expected]
            if not all(isinstance(value, str) for value in wanted_values):
                return False
            wanted = {value.casefold() for value in wanted_values}
            if wanted and not actual.intersection(wanted):
                return False
            continue
        if key in {"usage_scenario", "decision_status"}:
            actual = context.get(key)
        else:
            return False
        if isinstance(expected, list):
            if not all(isinstance(value, str) for value in expected):
                return False
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _normalize_applicability(requirements: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(requirements, dict):
        raise ValueError("skill_example_applicability_invalid")
    if any(not isinstance(key, str) or key not in _APPLICABILITY_KEYS for key in requirements):
        raise ValueError("skill_example_applicability_key_unsupported")

    normalized: dict[str, Any] = {}
    for key, raw_value in requirements.items():
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        if (
            not values
            or len(values) > 20
            or any(not isinstance(value, str) or not value.strip() for value in values)
        ):
            raise ValueError("skill_example_applicability_value_invalid")
        cleaned = [value.strip() for value in values]
        normalized[key] = cleaned if isinstance(raw_value, list) else cleaned[0]
    return normalized
