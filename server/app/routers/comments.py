"""Comment endpoints — cursor pagination, no OFFSET."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.comment import CommentItem
from app.schemas.common import CursorPage

router = APIRouter(prefix="/comments", tags=["评论"])


@router.get("", response_model=CursorPage[CommentItem], summary="评论游标分页")
async def list_comments(
    spot_id: int = Query(..., description="景区 ID"),
    cursor: int | None = Query(None, description="上一页最后一条 id"),
    limit: int = Query(20, ge=1, le=100),
    min_grade: int | None = Query(None, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conds = ["spot_id = :sid"]
    params: dict = {"sid": spot_id, "lim": limit + 1}
    if cursor:
        conds.append("id < :cur")
        params["cur"] = cursor
    if min_grade is not None:
        conds.append("co_grade >= :mg")
        params["mg"] = min_grade

    sql = f"""
        SELECT id, spot_id, co_name, co_grade, content,
               ip_region, co_time, src_schema
        FROM fact_comment
        WHERE {" AND ".join(conds)}
        ORDER BY id DESC
        LIMIT :lim
    """
    rows = (await db.execute(text(sql), params)).mappings().all()

    has_more = len(rows) > limit
    items = list(rows)[:limit]
    next_cursor = items[-1]["id"] if items and has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
