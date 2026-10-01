import asyncio
import time
from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.core.cache import cache_set, close_redis
from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.models.service_request import ServiceRequest, ServiceRequestDraft, ServiceRequestTask
from app.models.user import User  # noqa: F401 - registers user foreign keys in the worker process
from app.services.ai_service import generate_report_with_ai
from app.services.audit_service import record_audit
from app.services.calendar_ai_service import generate_calendar_with_ai
from app.services.service_request_repository import _append_revision
from app.services.service_request_payloads import flatten_ai_input
from app.services.service_request_drafts import (
    normalize_calendar_draft,
    normalize_report_draft,
    validate_draft,
)
from app.tasks.celery_app import celery_app


logger = get_logger(__name__)


async def _update_task_state(
    task_id: str,
    status: str,
    progress: int,
    error: str | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        task = await db.get(ServiceRequestTask, task_id)
        if task:
            task.status = status
            task.progress = progress
            if error is not None:
                task.error = error
            await db.commit()


async def _save_draft(
    request_id: int,
    task_id: str,
    ai_payload: dict[str, Any],
) -> None:
    async with AsyncSessionLocal() as db:
        service_request = await db.get(ServiceRequest, request_id)
        task = await db.get(ServiceRequestTask, task_id)
        if service_request is None or task is None:
            raise ValueError("service_request_task_target_not_found")
        validated_payload = validate_draft(service_request.service_type, ai_payload)

        existing = await db.scalar(
            select(ServiceRequestDraft).where(ServiceRequestDraft.request_id == request_id)
        )
        if existing:
            await _append_revision(db, request_id, "before_ai_regeneration", existing.editable_payload, None)
            existing.ai_payload = deepcopy(validated_payload)
            existing.editable_payload = deepcopy(validated_payload)
            existing.ai_version += 1
            existing.content_version += 1
            existing.updated_by = None
        else:
            existing = ServiceRequestDraft(
                request_id=request_id,
                ai_payload=deepcopy(validated_payload),
                editable_payload=deepcopy(validated_payload),
                ai_version=1,
                content_version=1,
            )
            db.add(existing)
            await db.flush()
        await _append_revision(db, request_id, "ai_generated", validated_payload, None)
        service_request.status = "ai_ready"
        service_request.ai_completed_at = datetime.utcnow()
        service_request.last_error = None
        task.status = "completed"
        task.progress = 100
        await record_audit(
            db,
            None,
            "service_request.ai.completed",
            "service_request",
            str(request_id),
            target_user_id=service_request.user_id,
            details={"task_id": task_id, "service_type": service_request.service_type},
        )
        await db.commit()


async def _run_service_request_task(task_id: str, request_id: int) -> dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            service_request = await db.get(ServiceRequest, request_id)
            task = await db.get(ServiceRequestTask, task_id)
            if service_request is None or task is None:
                raise ValueError("service_request_task_target_not_found")
            task.status = "processing"
            task.progress = 10
            await db.commit()

        await cache_set(
            f"service-request:task:{task_id}",
            {"status": "processing", "progress": 10, "message": "开始准备分析..."},
            expire=1800,
        )

        async with AsyncSessionLocal() as db:
            service_request = await db.get(ServiceRequest, request_id)
            if service_request is None:
                raise ValueError("service_request_not_found")
            user_data = flatten_ai_input(service_request)
            service_type = service_request.service_type

        started = time.time()
        if service_type == "report":
            ai_result = await generate_report_with_ai(user_data)
            ai_payload = normalize_report_draft(ai_result)
        else:
            ai_result = await generate_calendar_with_ai(user_data)
            async with AsyncSessionLocal() as db:
                service_request = await db.get(ServiceRequest, request_id)
                if service_request is None:
                    raise ValueError("service_request_not_found")
                ai_payload = normalize_calendar_draft(ai_result, service_request)
        elapsed_ms = int((time.time() - started) * 1000)

        await _update_task_state(task_id, "processing", 75)
        await cache_set(
            f"service-request:task:{task_id}",
            {"status": "processing", "progress": 75, "message": "AI 初稿已返回，正在校验..."},
            expire=1800,
        )

        # The service layer performs the strict calendar/report draft checks
        # before the consultant can save or deliver the result.
        await _save_draft(request_id, task_id, ai_payload)
        await cache_set(
            f"service-request:task:{task_id}",
            {
                "status": "completed",
                "progress": 100,
                "message": "AI 初稿已准备完成",
                "request_id": request_id,
                "generation_time_ms": elapsed_ms,
            },
            expire=1800,
        )
        return {"status": "completed", "request_id": request_id, "generation_time_ms": elapsed_ms}
    except Exception as error:
        error_text = str(error)
        logger.exception("服务申请 AI 任务失败 | task_id=%s | request_id=%s", task_id, request_id)
        try:
            async with AsyncSessionLocal() as db:
                task = await db.get(ServiceRequestTask, task_id)
                service_request = await db.get(ServiceRequest, request_id)
                if task:
                    task.status = "failed"
                    task.progress = 0
                    task.error = error_text
                if service_request:
                    service_request.status = "failed"
                    service_request.last_error = error_text
                    service_request.failed_at = datetime.utcnow()
                await record_audit(
                    db,
                    None,
                    "service_request.ai.failed",
                    "service_request",
                    str(request_id),
                    target_user_id=service_request.user_id if service_request else None,
                    details={"task_id": task_id, "error_type": type(error).__name__},
                )
                await db.commit()
        except Exception:
            logger.exception("服务申请 AI 失败状态写入失败 | task_id=%s", task_id)
        try:
            await cache_set(
                f"service-request:task:{task_id}",
                {"status": "failed", "progress": 0, "message": "AI 初稿生成失败", "error": error_text},
                expire=1800,
            )
        except Exception:
            logger.exception("服务申请 AI 失败缓存写入失败 | task_id=%s", task_id)
        raise
    finally:
        try:
            await engine.dispose()
        except Exception:
            logger.exception("服务申请数据库连接释放失败 | task_id=%s", task_id)
        try:
            await close_redis()
        except Exception:
            logger.exception("服务申请 Redis 连接释放失败 | task_id=%s", task_id)


@celery_app.task(bind=True, name="generate_service_request_draft")
def generate_service_request_task(self, request_id: int):
    return asyncio.run(_run_service_request_task(self.request.id, request_id))
