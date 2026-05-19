"""Comment-related schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class CommentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spot_id: int
    co_name: str | None = None
    co_grade: int | None = None
    content: str
    ip_region: str | None = None
    co_time: date
    src_schema: str | None = None
