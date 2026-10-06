import re
from datetime import datetime, time as dt_time
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, exists, func, select
from app.config import settings
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest
from app.domains.users.lunar_calendar import solar_date_for_birth
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def delivered_report_clause():
    return Report.reviewed_at.is_not(None) & exists(
        select(ServiceRequest.id).where(
            ServiceRequest.id == Report.request_id,
            ServiceRequest.user_id == Report.user_id,
            ServiceRequest.service_type == "report",
            ServiceRequest.status == "delivered",
            ServiceRequest.result_type == "report",
            ServiceRequest.result_id == Report.id,
        )
    )


async def create_report(
    db: AsyncSession,
    user_id: int,
    report_data: Dict[str, Any],
    generation_time_ms: int,
    input_data: Optional[Dict[str, Any]] = None,
) -> Report:
    """Create a new report"""
    logger.info(f"创建报告 | 用户ID: {user_id} | 生成耗时: {generation_time_ms}ms")

    # Extract birth date and time
    birth_profile = (input_data or {}).get("profile") or (input_data or {})
    birth_date_str = report_data["basic_info"]["birth_date"]
    if all(
        birth_profile.get(field) is not None
        for field in ("birth_year", "birth_month", "birth_day")
    ):
        birth_date = solar_date_for_birth(
            int(birth_profile["birth_year"]),
            int(birth_profile["birth_month"]),
            int(birth_profile["birth_day"]),
            calendar_type=birth_profile.get("calendar_type", "solar"),
            is_leap_month=bool(birth_profile.get("birth_is_leap_month", False)),
        )
    else:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()

    logger.debug(f"出生日期: {birth_date}")

    birth_time = None
    if birth_profile.get("birth_hour") is not None:
        birth_time = dt_time(
            int(birth_profile["birth_hour"]),
            int(birth_profile.get("birth_minute") or 0),
        )

    report = Report(
        user_id=user_id,
        title="辰鉴·人生说明书",
        birth_date=birth_date,
        birth_time=birth_time,
        birth_calendar_type=birth_profile.get("calendar_type", "solar"),
        birth_place=birth_profile.get("birth_place"),
        input_snapshot=input_data,
        energy_profile=report_data["energy_profile"],
        career_guidance=report_data["career_guidance"],
        relationship_pattern=report_data["relationship_pattern"],
        personal_growth=report_data["personal_growth"],
        summary=report_data.get("summary"),
        ai_raw_content=report_data.get("ai_generated_content"),
        ai_model=settings.DEEPSEEK_MODEL,
        generation_time_ms=generation_time_ms,
        selected_topics=(input_data or {}).get("selected_topics", report_data.get("selected_topics", [])),
        additional_info=(input_data or {}).get("additional_info", report_data.get("additional_info")),
        status="completed",
        is_deleted=False
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    logger.info(f"报告创建成功 | 报告ID: {report.id}")

    return report


async def get_report_by_id(db: AsyncSession, report_id: int, user_id: Optional[int] = None) -> Optional[Report]:
    """Get report by ID"""
    logger.debug(f"查询报告 | 报告ID: {report_id} | 用户ID: {user_id}")

    query = select(Report).where(Report.id == report_id, Report.is_deleted == False)
    if user_id is not None:
        query = query.where(
            Report.user_id == user_id,
            Report.status == "completed",
            delivered_report_clause(),
        )

    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if report:
        logger.info(f"报告查询成功 | 报告ID: {report_id}")
    else:
        logger.warning(f"报告未找到 | 报告ID: {report_id}")

    return report


async def get_user_reports(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 10
) -> tuple[List[Report], int]:
    """Get user's reports with pagination"""
    # Only a consultant-delivered report belongs in the user's report library.
    visible_report = delivered_report_clause()
    count_query = select(func.count(Report.id)).where(
        Report.user_id == user_id,
        Report.is_deleted.is_(False),
        Report.status == "completed",
        visible_report,
    )
    total = await db.scalar(count_query) or 0

    # Get reports
    query = select(Report).where(
        Report.user_id == user_id,
        Report.is_deleted.is_(False),
        Report.status == "completed",
        visible_report,
    ).order_by(desc(Report.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return list(reports), total


def extract_report_day_pillar(report: Report) -> Optional[str]:
    """Return a report's natal day pillar from structured or legacy content."""
    content_payload = report.content_payload if isinstance(report.content_payload, dict) else {}
    foundation_data = (
        content_payload.get("foundation_data")
        or content_payload.get("foundationData")
        or {}
    )
    bazi = foundation_data.get("bazi") if isinstance(foundation_data, dict) else {}
    day = bazi.get("day") if isinstance(bazi, dict) else {}

    if isinstance(day, str):
        candidate = day.strip()
    elif isinstance(day, dict):
        candidate = day.get("pillar") or f"{day.get('stem', '')}{day.get('branch', '')}"
        candidate = candidate.strip()
    else:
        candidate = ""

    valid_pillar = re.compile(r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$")
    if valid_pillar.fullmatch(candidate):
        return candidate

    legacy_content = report.ai_raw_content or ""
    match = re.search(
        r"\*\*日柱[^*]*\*\*\s*([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])",
        legacy_content,
    )
    return match.group(1) if match else None


def format_report_list_item(report: Report) -> dict[str, Any]:
    """Project report content needed by report cards without loading detail pages."""
    energy_profile = report.energy_profile or {}
    content_payload = report.content_payload if isinstance(report.content_payload, dict) else {}
    core_traits = energy_profile.get("core_traits") or energy_profile.get("coreTraits")
    if isinstance(core_traits, list):
        core_traits = "、".join(str(trait) for trait in core_traits if trait)
    cover_description = content_payload.get("cover_description") or content_payload.get("coverDescription")
    if not isinstance(cover_description, str) or not cover_description.strip():
        cover_description = None
    else:
        cover_description = cover_description.strip()
    return {
        "id": report.id,
        "title": report.title,
        "created_at": report.created_at,
        "energy_type": energy_profile.get("type"),
        "core_traits": core_traits,
        "summary": report.summary,
        "day_pillar": extract_report_day_pillar(report),
        "cover_description": cover_description,
    }


async def delete_report(db: AsyncSession, report_id: int, user_id: int) -> bool:
    """Soft delete a report"""
    report = await get_report_by_id(db, report_id, user_id)
    if not report:
        return False

    report.is_deleted = True
    await db.commit()
    return True


def format_report_response(report: Report) -> Dict[str, Any]:
    """Format report for API response"""
    content_payload = dict(report.content_payload or {}) if report.content_payload else None
    if content_payload is not None:
        # The private AI source remains available to staff through the request
        # workspace, never through the public report response.
        content_payload.pop("ai_generated_content", None)
    snapshot = report.input_snapshot or {}
    birth_profile = snapshot.get("profile") or snapshot
    birth_year = birth_profile.get("birth_year")
    birth_month = birth_profile.get("birth_month")
    birth_day = birth_profile.get("birth_day")
    has_original_birth_date = all(
        value is not None for value in (birth_year, birth_month, birth_day)
    )
    displayed_birth_date = (
        f"{int(birth_year):04d}-{int(birth_month):02d}-{int(birth_day):02d}"
        if has_original_birth_date
        else report.birth_date.isoformat()
    )
    return {
        "id": report.id,
        "title": report.title,
        "basic_info": {
            "name": snapshot.get("name") or (snapshot.get("profile") or {}).get("name") or "用户",
            "birth_date": displayed_birth_date,
            "solar_birth_date": report.birth_date.isoformat(),
            "calendar_type": birth_profile.get("calendar_type", report.birth_calendar_type),
            "birth_is_leap_month": bool(birth_profile.get("birth_is_leap_month", False)),
            "report_date": report.created_at.date().isoformat(),
            "generated_by": "咨询师审校 + AI 初稿" if report.reviewed_at else ("DeepSeek AI" if report.ai_raw_content else "Basic Algorithm")
        },
        "energy_profile": report.energy_profile,
        "career_guidance": report.career_guidance,
        "relationship_pattern": report.relationship_pattern,
        "personal_growth": report.personal_growth,
        "summary": report.summary,
        "content_payload": content_payload,
        "ai_generated_content": report.ai_raw_content if not report.content_payload else None,
        "reviewed_at": report.reviewed_at,
        "input_snapshot": snapshot,
        "profile_version": snapshot.get("profile_version"),
        "context": snapshot.get("context"),
        "created_at": report.created_at
    }
