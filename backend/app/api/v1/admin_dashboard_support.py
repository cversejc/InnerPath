from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import _db_end, _db_start


async def _daily_counts(
    db: AsyncSession,
    model,
    id_column,
    timestamp_column,
    start_date: date,
    end_date: date,
    *,
    use_log_date: bool = False,
) -> dict[date, int]:
    if use_log_date:
        day_expression = timestamp_column
        conditions = [timestamp_column >= start_date, timestamp_column <= end_date]
    else:
        day_expression = func.date(timestamp_column + text("interval '8 hours'"))
        conditions = [timestamp_column >= _db_start(start_date), timestamp_column < _db_end(end_date)]
    statement = (
        select(day_expression.label("day"), func.count(id_column))
        .select_from(model)
        .where(*conditions)
        .group_by(day_expression)
    )
    rows = (await db.execute(statement)).all()
    return {row[0]: int(row[1]) for row in rows}
