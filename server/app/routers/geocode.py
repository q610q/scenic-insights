"""AMap (高德) geocoding proxy — 隐藏 API key + 服务端缓存。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.cache import cache_get_or_set
from app.config import settings
from app.services.amap import amap_geocode

router = APIRouter(prefix="/geocode", tags=["高德代理"])


@router.get("", summary="高德地理编码代理")
async def geocode(
    address: str = Query(..., min_length=2, max_length=128),
) -> dict:
    if not settings.AMAP_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AMAP_API_KEY 未配置。在服务端 .env 中设置后重启。",
        )

    async def _call():
        return await amap_geocode(address, settings.AMAP_API_KEY)

    return await cache_get_or_set(f"geocode:{address}", _call, 7 * 86400)
