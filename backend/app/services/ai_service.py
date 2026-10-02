import os
from typing import Any, Dict

from app.core.logging_config import get_logger, log_external_api
from app.services.intake_service import flatten_snapshot_for_ai
from app.domains.reports.generation.multi_step_report import MultiStepReportGenerator
from app.domains.reports.generation.single_step_report import generate_report_single_step

logger = get_logger(__name__)


@log_external_api("DeepSeek API")
async def generate_report_with_ai(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize report input and run the configured generation strategy."""
    if user_data.get("schema_version") == 2 and user_data.get("profile"):
        snapshot = dict(user_data)
        user_data = flatten_snapshot_for_ai(snapshot)
        user_data["profile"] = snapshot.get("profile") or {}

    use_multistep = os.getenv("USE_MULTISTEP_GENERATION", "false").lower() == "true"
    if use_multistep:
        logger.info(f"使用多步生成模式 | 用户: {user_data.get('name', 'Unknown')}")
        try:
            generator = MultiStepReportGenerator()
            return await generator.generate_report(user_data)
        except Exception as error:
            logger.error(f"多步生成失败，降级到单步模式: {str(error)}")

    return await generate_report_single_step(user_data)
