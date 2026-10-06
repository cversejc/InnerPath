from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ReportVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    version_no: int
    workflow_version_id: int
    narrative_plan_id: int
    fragment_snapshot: list[dict[str, Any]]
    semantic_snapshot: dict[str, Any]
    structured_data: dict[str, Any]
    rendered_html: str
    pdf_url: Optional[str] = None
    created_at: datetime
    delivered_at: datetime
