import asyncio
import os
import time
from typing import Any, Dict

from app.core.cache import cache_set, close_redis
from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.models.report import ReportTask
# Import the user model so SQLAlchemy can resolve report foreign keys in the
# standalone Celery process (which does not import the FastAPI routers).
from app.models.user import User  # noqa: F401
from app.services.ai_service import generate_report_with_ai
from app.services.report_service import create_report
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


async def update_task_state(
    task_id: str,
    status: str,
    progress: int,
    report_id: int | None = None,
    error: str | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        task = await db.get(ReportTask, task_id)
        if task:
            task.status = status
            task.progress = progress
            if report_id is not None:
                task.report_id = report_id
            if error is not None:
                task.error = error
            await db.commit()


async def _run_generate_report_task(
    task_id: str,
    user_id: int,
    user_data: Dict[str, Any],
    use_multistep: bool,
) -> Dict[str, Any]:
    """Run the complete report workflow on one event loop."""
    try:
        await update_task_state(task_id, "processing", 10)
        await cache_set(
            f"report:task:{task_id}",
            {"status": "processing", "progress": 10, "message": "开始生成报告..."},
            expire=600,
        )

        if use_multistep:
            await cache_set(
                f"report:task:{task_id}",
                {"status": "processing", "progress": 15, "message": "建立先天坐标..."},
                expire=600,
            )

        start_time = time.time()
        report_data = await generate_report_with_ai(user_data)
        generation_time_ms = int((time.time() - start_time) * 1000)

        await update_task_state(task_id, "processing", 70)
        await cache_set(
            f"report:task:{task_id}",
            {"status": "processing", "progress": 70, "message": "AI 分析完成..."},
            expire=600,
        )

        async def save_report() -> int:
            async with AsyncSessionLocal() as db:
                report = await create_report(
                    db,
                    user_id=user_id,
                    report_data=report_data,
                    generation_time_ms=generation_time_ms,
                    input_data=user_data,
                )
                return report.id

        report_id = await save_report()
        await update_task_state(task_id, "completed", 100, report_id=report_id)
        await cache_set(
            f"report:task:{task_id}",
            {
                "status": "completed",
                "progress": 100,
                "message": "报告生成完成",
                "report_id": report_id,
            },
            expire=600,
        )

        return {
            "status": "completed",
            "report_id": report_id,
            "generation_time_ms": generation_time_ms,
        }

    except Exception as error:
        error_text = str(error)
        try:
            await update_task_state(task_id, "failed", 0, error=error_text)
        except Exception:
            logger.exception("报告任务失败状态写入失败 | task_id=%s", task_id)
        try:
            await cache_set(
                f"report:task:{task_id}",
                {
                    "status": "failed",
                    "progress": 0,
                    "message": f"报告生成失败: {error_text}",
                    "error": error_text,
                },
                expire=600,
            )
        except Exception:
            logger.exception("报告任务失败缓存写入失败 | task_id=%s", task_id)
        raise
    finally:
        # AsyncEngine and redis-py async clients retain loop-bound resources.
        # Dispose them before asyncio.run closes this task's loop so the next
        # Celery task cannot reuse connections from a dead loop.
        try:
            await engine.dispose()
        except Exception:
            logger.exception("报告任务数据库连接释放失败 | task_id=%s", task_id)
        try:
            await close_redis()
        except Exception:
            logger.exception("报告任务 Redis 连接释放失败 | task_id=%s", task_id)


@celery_app.task(bind=True, name="generate_report")
def generate_report_task(self, user_id: int, user_data: Dict[str, Any]):
    task_id = self.request.id
    use_multistep = os.getenv("USE_MULTISTEP_GENERATION", "false").lower() == "true"
    return asyncio.run(_run_generate_report_task(task_id, user_id, user_data, use_multistep))
