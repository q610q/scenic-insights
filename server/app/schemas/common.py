"""Common Pydantic models (pagination / error)."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """游标分页响应。"""

    items: list[T]
    next_cursor: int | None = None
    has_more: bool = False


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
