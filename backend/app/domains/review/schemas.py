from typing import Any
from pydantic import BaseModel, Field


class ReviewVersion(BaseModel):
    fingerprint: str = Field(min_length=64, max_length=64)


class ReviewPatch(ReviewVersion):
    changes: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    core_review: dict[str, bool] | None = None
    birth_time_confirmation: dict[str, Any] | None = None
    narrative: dict[str, Any] | None = None


class ReviewCommandInput(ReviewVersion):
    idempotency_key: str = Field(min_length=1, max_length=160)


class ReviewCheckpointInput(ReviewCommandInput):
    checkpoint_key: str = Field(min_length=1, max_length=32)


class RevisionInput(ReviewCommandInput):
    targets: list[str] = Field(min_length=1, max_length=20)
    instruction: str = Field(min_length=1, max_length=5000)


class IssueResolution(ReviewVersion):
    check_id: int
    issue_id: str
    resolution: str
    reason: str = Field(min_length=1, max_length=3000)


class IssueResolutionGroup(ReviewVersion):
    """同类型问题整体处理：一次填写依据，每条问题仍单独留痕。"""

    check_id: int
    issue_ids: list[str] = Field(min_length=1, max_length=200)
    resolution: str
    reason: str = Field(min_length=1, max_length=3000)
