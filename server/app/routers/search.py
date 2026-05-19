"""Search endpoints — full-text + geographic."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.spot import NearbyResult

router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("/spots", summary="景区关键词搜索（trigram + tsvector）")
async def search_spots(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.execute(
        text("SELECT * FROM search_spots(:q, :n)"),
        {"q": q, "n": limit},
    )
    return [dict(r._mapping) for r in rows]


@router.get(
    "/nearby",
    response_model=list[NearbyResult],
    summary="地理半径搜索（PostGIS）",
)
async def nearby_spots(
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    km: float = Query(50, gt=0, le=500),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        rows = await db.execute(
            text("SELECT * FROM nearby_spots(:lon, :lat, :km, :lim)"),
            {"lon": lon, "lat": lat, "km": km, "lim": limit},
        )
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Geo search failed (PostGIS extension installed?): {e}",
        ) from e
