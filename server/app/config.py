"""Application configuration (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Database -----
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://travel:changeme@localhost:5432/travel_dw"
    )

    # ----- Redis -----
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # ----- High AMap -----
    AMAP_API_KEY: str = Field(default="")

    # ----- API -----
    API_TITLE: str = Field(default="旅游数据 API")
    API_VERSION: str = Field(default="0.1.0")
    API_PREFIX: str = Field(default="/api/v1")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173"
    )

    # ----- Cache TTL (seconds) -----
    CACHE_DASHBOARD_TTL: int = Field(default=300)
    CACHE_SPOT_DETAIL_TTL: int = Field(default=3600)
    CACHE_HEATMAP_TTL: int = Field(default=3600)

    # ----- Scheduler -----
    MV_REFRESH_CRON_HOUR: int = Field(default=3)

    # ----- Misc -----
    LOG_LEVEL: str = Field(default="INFO")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
