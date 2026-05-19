"""Geocode scenic spots via AMap Web API.

读取 DuckDB 中 dim_spot 表，对 location 字段做 Geocoding，
回写 lon / lat 列，并同步导出到 dim_spot.parquet（供 load_to_pg 灌库）。
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import duckdb
import httpx
import typer
from rich.progress import track

from pipelines.utils import console, load_env  # 已强制 UTF-8 输出

AMAP_URL = "https://restapi.amap.com/v3/geocode/geo"
DEFAULT_SLEEP_SEC = 0.2  # 友善限速
DEFAULT_DUCKDB = Path("data/etl.duckdb")
DEFAULT_PARQUET = Path("data/parquet/dim_spot.parquet")


def geocode_one(
    client: httpx.Client,
    address: str,
    api_key: str,
) -> tuple[float, float] | None:
    """单次 Geocoding 请求 → (lon, lat) | None"""
    try:
        r = client.get(
            AMAP_URL,
            params={"address": address, "key": api_key, "output": "json"},
            timeout=5,
        )
        data = r.json()
        if data.get("status") != "1" or int(data.get("count", 0)) < 1:
            return None
        loc = data["geocodes"][0]["location"]  # "lon,lat"
        lon, lat = loc.split(",")
        return float(lon), float(lat)
    except Exception as e:
        console.print(f"[yellow]geocode error for {address[:30]!r}: {e}[/]")
        return None


def run_geocode(
    duckdb_path: Path = DEFAULT_DUCKDB,
    api_key: str | None = None,
    sleep_sec: float = DEFAULT_SLEEP_SEC,
    only_missing: bool = True,
    parquet_out: Path | None = DEFAULT_PARQUET,
) -> int:
    """对 dim_spot 全表做 Geocoding，写回 DuckDB 并同步 parquet。

    Args:
        duckdb_path: DuckDB 文件路径
        api_key: 高德 Web 服务 key；为 None 时从环境变量 AMAP_API_KEY 读取
        sleep_sec: 单次请求间隔（避开限流）
        only_missing: True = 只补 lon IS NULL 的行（增量安全）
        parquet_out: 同步导出的 parquet 路径；传 None 跳过导出

    Returns:
        成功 geocoded 的行数
    """
    key = api_key or os.environ.get("AMAP_API_KEY", "")
    if not key:
        console.print("[red]AMAP_API_KEY 未设置（参数或 .env）[/]")
        raise typer.Exit(1)

    con = duckdb.connect(str(duckdb_path))

    where = "AND lon IS NULL" if only_missing else ""
    rows = con.execute(
        f"""SELECT id, name, location
            FROM dim_spot
            WHERE location IS NOT NULL AND length(location) > 2
            {where}"""
    ).fetchall()

    if not rows:
        console.print("[yellow]无待处理景点（全部已有坐标）[/]")
        con.close()
        return 0

    console.print(f"[cyan]Geocoding {len(rows)} spots (sleep={sleep_sec}s)...[/]")

    with httpx.Client() as client:
        ok = 0
        for spot_id, name, location in track(rows, description="Geocoding"):
            address = location or name
            coords = geocode_one(client, address, key)
            if coords:
                lon, lat = coords
                con.execute(
                    "UPDATE dim_spot SET lon = ?, lat = ? WHERE id = ?",
                    [lon, lat, spot_id],
                )
                ok += 1
            time.sleep(sleep_sec)

    console.print(f"[green]✓ Geocoded {ok}/{len(rows)} successfully[/]")

    # 关键修复：同步回写 parquet，避免 load_to_pg 读到旧文件丢失坐标
    if parquet_out is not None:
        parquet_out.parent.mkdir(parents=True, exist_ok=True)
        con.execute(
            f"COPY dim_spot TO '{parquet_out.as_posix()}' "
            f"(FORMAT PARQUET, OVERWRITE_OR_IGNORE 1, COMPRESSION 'zstd')"
        )
        n_with = con.execute(
            f"SELECT count(*) FROM '{parquet_out.as_posix()}' "
            f"WHERE lon IS NOT NULL"
        ).fetchone()[0]
        console.print(
            f"[green]✓ Parquet re-exported: {parquet_out} ({n_with} rows with coords)[/]"
        )

    con.close()
    return ok


def _cli(
    duckdb_path: Path = typer.Option(DEFAULT_DUCKDB),
    api_key: str = typer.Option(None, envvar="AMAP_API_KEY"),
    sleep_sec: float = typer.Option(DEFAULT_SLEEP_SEC),
    only_missing: bool = typer.Option(True, help="只对 lon IS NULL 的行处理"),
    parquet_out: Path = typer.Option(DEFAULT_PARQUET, help="同步导出 parquet；空字符串跳过"),
) -> None:
    """Typer CLI 包装。"""
    load_env()  # 直接运行 python -m pipelines.geocode 时也能拿到 AMAP_API_KEY
    run_geocode(
        duckdb_path=duckdb_path,
        api_key=api_key or os.environ.get("AMAP_API_KEY"),
        sleep_sec=sleep_sec,
        only_missing=only_missing,
        parquet_out=parquet_out if str(parquet_out) else None,
    )


# 兼容旧调用（pipelines.run 仍可能 import main）
main = _cli


if __name__ == "__main__":
    typer.run(_cli)
