"""FastAPI application entry."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import close_redis
from app.config import settings
from app.db import engine
from app.routers import comments, dashboard, geocode, search, spots
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: 启动调度器，关闭时清理连接。"""
    start_scheduler()
    log.info("API started: %s v%s", settings.API_TITLE, settings.API_VERSION)
    yield
    log.info("API shutting down...")
    await stop_scheduler()
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


# ---- 健康检查 ----
@app.get("/healthz", tags=["meta"], summary="健康检查")
async def healthz() -> dict:
    return {"status": "ok", "service": settings.API_TITLE}


@app.get("/", tags=["meta"], summary="API 入口")
async def root() -> dict:
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ---- 业务路由 ----
prefix = settings.API_PREFIX
app.include_router(dashboard.router, prefix=prefix)
app.include_router(spots.router,     prefix=prefix)
app.include_router(comments.router,  prefix=prefix)
app.include_router(search.router,    prefix=prefix)
app.include_router(geocode.router,   prefix=prefix)
