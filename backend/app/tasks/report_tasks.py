import asyncio

from app.core.cache import cache_set, close_redis
from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.domains.reports.models import ReportTask
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)
LEGACY_TASK_ERROR = "旧版直接生成报告任务已停用，请通过服务申请进入咨询师协作流程。"


async def _mark_legacy_task_retired(task_id: str | None) -> None:
    try:
        if task_id:
            async with AsyncSessionLocal() as db:
                task = await db.get(ReportTask, task_id)
                if task:
                    task.status = "failed"
                    task.progress = 0
                    task.error = LEGACY_TASK_ERROR
                    await db.commit()
                    try:
                        await cache_set(
                            f"report:task:{task_id}",
                            {
                                "status": "failed",
                                "progress": 0,
                                "error": LEGACY_TASK_ERROR,
                            },
                            expire=600,
                        )
                    except Exception:
                        logger.exception(
                            "Retired report task cache update failed | task_id=%s",
                            task_id,
                        )
    finally:
        try:
            await engine.dispose()
        except Exception:
            logger.exception("Retired report task DB cleanup failed")
        try:
            await close_redis()
        except Exception:
            logger.exception("Retired report task Redis cleanup failed")


@celery_app.task(bind=True, name="generate_report", max_retries=0)
def generate_report_task(self, _user_id: int, _user_data: dict):
    """Consume queued legacy messages without generating a report outside a case."""
    task_id = self.request.id
    asyncio.run(_mark_legacy_task_retired(task_id))
    logger.warning("Retired direct report task rejected | task_id=%s", task_id)
    raise RuntimeError(LEGACY_TASK_ERROR)
