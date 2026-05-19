"""Spot-related schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SpotBrief(BaseModel):
    """列表 / 大屏简要信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    level: str | None = None
    city: str | None = None
    grade: Decimal | None = None
    hot: Decimal | None = None
    comment_count_real: int = 0
    comment_tier: str | None = None
    lon: float | None = None
    lat: float | None = None


class SpotDetail(SpotBrief):
    """详情页完整字段。"""

    tag: str | None = None
    location: str | None = None
    province: str | None = None
    district: str | None = None
    phone: str | None = None
    open_time_raw: str | None = None
    intro: str | None = None
    notice: str | None = None
    tips: str | None = None
    total_comments_raw: int | None = None
    comment_count_all: int = 0
    comment_count_default: int = 0
    has_real_comments: bool = False


class SpotMetric(BaseModel):
    """大屏 mv_spot_metrics 投影。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: str | None = None
    level: str | None = None
    tag: str | None = None
    grade: Decimal | None = None
    hot: Decimal | None = None
    comment_count_real: int = 0
    avg_co_grade: Decimal | None = None
    grade_5_count: int = 0
    grade_4_count: int = 0
    grade_3_count: int = 0
    grade_2_count: int = 0
    grade_1_count: int = 0
    lon: float | None = None
    lat: float | None = None


class HeatmapPoint(BaseModel):
    """ECharts 地图散点格式: { name, value: [lon, lat, count, grade] }"""

    name: str
    value: list[float | int] = Field(default_factory=list)


class LevelDist(BaseModel):
    level: str
    spot_count: int
    total_comments: int = 0
    avg_grade: Decimal | None = None


class NearbyResult(BaseModel):
    id: int
    name: str
    city: str | None = None
    level: str | None = None
    grade: Decimal | None = None
    dist_km: float
