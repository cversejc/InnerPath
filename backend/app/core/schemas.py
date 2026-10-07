from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_serializer

from app.core.time import api_datetime


def _serialize_api_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return api_datetime(value)
    if isinstance(value, dict):
        return {key: _serialize_api_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_api_value(item) for item in value]
    return value


class APIModel(BaseModel):
    """Base model that emits datetime fields with an explicit Shanghai offset."""

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_api_values(self, value: Any) -> Any:
        return _serialize_api_value(value)
