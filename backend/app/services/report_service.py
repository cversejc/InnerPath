from datetime import datetime, date, time as dt_time
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.report import Report
from app.schemas.report import ReportCreate
from app.core.logging_config import get_logger
import json

logger = get_logger(__name__)


async def create_report(
    db: AsyncSession,
    user_id: int,
    report_data: Dict[str, Any],
    generation_time_ms: int
) -> Report:
    """Create a new report"""
    logger.info(f"创建报告 | 用户ID: {user_id} | 生成耗时: {generation_time_ms}ms")

    # Extract birth date and time
    birth_date_str = report_data["basic_info"]["birth_date"]
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()

    logger.debug(f"出生日期: {birth_date}")

    # Create report
    report = Report(
        user_id=user_id,
        title="个人能量地图报告",
        birth_date=birth_date,
        birth_time=None,  # TODO: parse from user data if available
        energy_profile=report_data["energy_profile"],
        career_guidance=report_data["career_guidance"],
        relationship_pattern=report_data["relationship_pattern"],
        personal_growth=report_data["personal_growth"],
        summary=report_data.get("summary"),
        ai_raw_content=report_data.get("ai_generated_content"),
        ai_model="deepseek-chat",
        generation_time_ms=generation_time_ms,
        selected_topics=report_data.get("selected_topics", []),
        additional_info=report_data.get("additional_info"),
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
    if user_id:
        query = query.where(Report.user_id == user_id)

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
    # Get total count
    count_query = select(Report).where(
        Report.user_id == user_id,
        Report.is_deleted == False
    )
    count_result = await db.execute(count_query)
    total = len(count_result.all())

    # Get reports
    query = select(Report).where(
        Report.user_id == user_id,
        Report.is_deleted == False
    ).order_by(desc(Report.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return list(reports), total


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
    return {
        "id": report.id,
        "title": report.title,
        "basic_info": {
            "name": "用户",  # Name is not stored in report
            "birth_date": report.birth_date.isoformat(),
            "report_date": report.created_at.date().isoformat(),
            "generated_by": "DeepSeek AI" if report.ai_raw_content else "Basic Algorithm"
        },
        "energy_profile": report.energy_profile,
        "career_guidance": report.career_guidance,
        "relationship_pattern": report.relationship_pattern,
        "personal_growth": report.personal_growth,
        "summary": report.summary,
        "ai_generated_content": report.ai_raw_content,
        "created_at": report.created_at
    }
