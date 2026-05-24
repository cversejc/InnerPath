import time
import json
import os
from typing import Dict, Any
from app.tasks.celery_app import celery_app
from app.services.ai_service import generate_report_with_ai
from app.services.report_service import create_report
from app.db.session import AsyncSessionLocal
from app.core.cache import cache_set
import asyncio


@celery_app.task(bind=True, name="generate_report")
def generate_report_task(self, user_id: int, user_data: Dict[str, Any]):
    """
    Celery task to generate report asynchronously
    Supports both authenticated users and guest users (user_id can be None)
    """
    task_id = self.request.id
    use_multistep = os.getenv("USE_MULTISTEP_GENERATION", "false").lower() == "true"

    try:
        # Update progress based on generation mode
        if use_multistep:
            # Multi-step progress updates
            asyncio.run(cache_set(
                f"report:task:{task_id}",
                json.dumps({"status": "processing", "progress": 10, "message": "准备生成报告..."}),
                expire=600
            ))

            # Step 1: Foundation calculation (10% -> 25%)
            asyncio.run(cache_set(
                f"report:task:{task_id}",
                json.dumps({"status": "processing", "progress": 15, "message": "推算命理基础..."}),
                expire=600
            ))

            # Generate report with AI
            start_time = time.time()
            report_data = asyncio.run(generate_report_with_ai(user_data))
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Progress updates are handled within MultiStepReportGenerator
            # Final progress update
            asyncio.run(cache_set(
                f"report:task:{task_id}",
                json.dumps({"status": "processing", "progress": 90, "message": "组装最终报告..."}),
                expire=600
            ))
        else:
            # Single-step progress updates
            asyncio.run(cache_set(
                f"report:task:{task_id}",
                json.dumps({"status": "processing", "progress": 10, "message": "开始生成报告..."}),
                expire=600
            ))

            # Generate report with AI
            start_time = time.time()
            report_data = asyncio.run(generate_report_with_ai(user_data))
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Update progress: AI generation complete
            asyncio.run(cache_set(
                f"report:task:{task_id}",
                json.dumps({"status": "processing", "progress": 70, "message": "AI 分析完成..."}),
                expire=600
            ))

        # Save to database only if user is authenticated
        report_id = None
        if user_id:
            async def save_report():
                async with AsyncSessionLocal() as db:
                    report = await create_report(
                        db,
                        user_id=user_id,
                        report_data=report_data,
                        generation_time_ms=generation_time_ms
                    )
                    return report.id

            report_id = asyncio.run(save_report())

        # For guest users, store report data in cache temporarily
        if not user_id:
            asyncio.run(cache_set(
                f"report:guest:{task_id}",
                json.dumps(report_data),
                expire=3600  # 1 hour
            ))

        # Update progress: completed
        asyncio.run(cache_set(
            f"report:task:{task_id}",
            json.dumps({
                "status": "completed",
                "progress": 100,
                "message": "报告生成完成",
                "report_id": report_id,
                "report_data": report_data if not user_id else None  # Include data for guests
            }),
            expire=600
        ))

        return {
            "status": "completed",
            "report_id": report_id,
            "generation_time_ms": generation_time_ms,
            "report_data": report_data if not user_id else None
        }

    except Exception as e:
        # Update progress: failed
        asyncio.run(cache_set(
            f"report:task:{task_id}",
            json.dumps({
                "status": "failed",
                "progress": 0,
                "message": f"报告生成失败: {str(e)}",
                "error": str(e)
            }),
            expire=600
        ))

        raise
