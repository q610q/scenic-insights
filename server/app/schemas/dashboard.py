"""Dashboard-specific schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CityKPI(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    city: str
    province: str | None = None
    spot_count: int
    avg_grade: Decimal | None = None
    total_real_comments: int = 0
    hot_spot_count: int = 0


class GlobalKPI(BaseModel):
    """首页四张卡片汇总。"""

    spot_total: int
    real_comment_total: int
    avg_grade: Decimal | None
    city_count: int


class MonthlyTrend(BaseModel):
    ym: date
    cnt: int
    avg_grade: Decimal | None = None
