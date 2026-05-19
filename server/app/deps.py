"""FastAPI dependency injection (re-export get_db for routers)."""

from app.db import get_db

__all__ = ["get_db"]
