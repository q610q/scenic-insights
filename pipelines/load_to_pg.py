"""Load Parquet → PostgreSQL via DuckDB ATTACH.

读取 P1 ETL 产生的 Parquet (dim_spot + fact_comment/year=*/*.parquet)，
通过 DuckDB postgres extension 直灌 PG。

性能: ~150K 评论 + 2K 景区，<10 秒。
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import typer
from rich.table import Table

from pipelines.utils import console  # UTF-8 console


def parse_pg_url(url: str) -> str:
    """把 postgresql+asyncpg://user:pass@host:port/db → DuckDB ATTACH 字符串"""
    if "+" in url.split("://", 1)[0]:
        scheme, rest = url.split("://", 1)
        scheme = scheme.split("+", 1)[0]
        url = f"{scheme}://{rest}"
    return url


def main(
    parquet_dir: Path = typer.Option(Path("data/parquet")),
    pg_url: str = typer.Option(None, envvar="DATABASE_URL"),
    refresh_mvs: bool = typer.Option(True, help="导入后刷新物化视图"),
    rebuild_indexes: bool = typer.Option(
        True, help="导入完成后创建 03_indexes.sql 的索引"
    ),
) -> None:
    """灌入 PG。"""
    if not pg_url:
        console.print(
            "[red]DATABASE_URL 未设置；在 .env 或 -pg-url 提供[/]"
        )
        raise typer.Exit(1)

    dim_path  = parquet_dir / "dim_spot.parquet"
    fact_path = parquet_dir / "fact_comment"

    if not dim_path.exists():
        console.print(f"[red]Missing {dim_path}. 先跑 'python -m pipelines.run clean'[/]")
        raise typer.Exit(1)

    pg_dsn = parse_pg_url(pg_url)
    console.print(f"[cyan]Connecting to PG: {pg_dsn.split('@')[-1]}[/]")

    # 先用 psycopg 跑 TRUNCATE（DuckDB ATTACH 不支持 RESTART IDENTITY）
    try:
        import psycopg
    except ImportError:
        console.print("[red]psycopg 未装：pip install 'psycopg[binary]'[/]")
        raise typer.Exit(1)

    with psycopg.connect(pg_dsn, autocommit=True) as pg_con, pg_con.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE fact_comment, dim_scenic_spot RESTART IDENTITY CASCADE"
        )
    console.print("[cyan]▶ Truncated existing tables[/]")

    con = duckdb.connect(":memory:")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(f"ATTACH '{pg_dsn}' AS pg (TYPE postgres)")

    # -------- dim_scenic_spot --------
    console.print("[cyan]▶ Loading dim_scenic_spot...[/]")
    con.execute(f"""
        INSERT INTO pg.dim_scenic_spot (
            name, level, tag, location, province, city, phone,
            open_time_raw, intro, notice, tips,
            grade, hot, total_comments_raw,
            comment_count_all, comment_count_real, comment_count_default,
            has_real_comments, comment_tier,
            source_schemas, lon, lat
        )
        SELECT
            name, level, tag, location, province, city, phone,
            open_time_raw, intro, notice, tips,
            grade, hot, total_comments_raw,
            comment_count_all, comment_count_real, comment_count_default,
            has_real_comments, comment_tier,
            source_schemas, lon, lat
        FROM '{dim_path.as_posix()}'
    """)
    n_dim = con.execute("SELECT count(*) FROM pg.dim_scenic_spot").fetchone()[0]
    console.print(f"[green]  ✓ dim_scenic_spot: {n_dim:,} rows[/]")

    # -------- fact_comment --------
    if fact_path.exists():
        console.print("[cyan]▶ Loading fact_comment (按景区名映射 spot_id)...[/]")
        # 先读维表 (name → id) 映射
        con.execute("""
            CREATE TEMP TABLE name_id_map AS
            SELECT id, name FROM pg.dim_scenic_spot
        """)

        # 写评论：用景区名 join 得到 PG 中的 spot_id
        # （DuckDB 自动跳过 Parquet 旧 spot_id，按 name 重新映射）
        sql_load = f"""
            INSERT INTO pg.fact_comment
                (spot_id, co_name, co_grade, content, content_hash,
                 ip_region, co_time, src_schema)
            SELECT
                m.id          AS spot_id,
                f.co_name,
                f.co_grade,
                f.content,
                f.content_hash,
                f.ip_region,
                f.co_time,
                f.src_schema
            FROM read_parquet('{fact_path.as_posix()}/**/*.parquet',
                              hive_partitioning = true) f
            JOIN name_id_map m ON m.name = f.spot_name
            WHERE f.co_time IS NOT NULL
        """
        con.execute(sql_load)
        n_fact = con.execute("SELECT count(*) FROM pg.fact_comment").fetchone()[0]
        console.print(f"[green]  ✓ fact_comment: {n_fact:,} rows[/]")
    else:
        console.print("[yellow]  ⚠ fact_comment Parquet 不存在，跳过[/]")
        n_fact = 0

    # -------- 索引 + 物化视图（用 psycopg 直连，避免 DuckDB 转义复杂 DDL）--------
    pg_actions_done = False
    with psycopg.connect(pg_dsn, autocommit=True) as pg_con, pg_con.cursor() as cur:
        if rebuild_indexes:
            idx_sql = Path("db/init/03_indexes.sql")
            if idx_sql.exists():
                console.print("[cyan]▶ Creating indexes...[/]")
                cur.execute(idx_sql.read_text(encoding="utf-8"))
                console.print("[green]  ✓ Indexes created[/]")

        # ---- 文本清洗（intro/notice/tips/tag/location 去除空白/占位符）----
        cleanup_sql = Path("db/init/06_text_cleanup.sql")
        if cleanup_sql.exists():
            console.print("[cyan]▶ Applying text cleanup...[/]")
            cur.execute(cleanup_sql.read_text(encoding="utf-8"))
            console.print("[green]  ✓ Text fields cleaned[/]")

        # ---- 城市/省份字典回填（修复 etl.sql 正则提取 city 60% 失败）----
        city_sql = Path("db/init/07_city_backfill.sql")
        if city_sql.exists():
            console.print("[cyan]▶ Backfilling city / province from dict...[/]")
            cur.execute(city_sql.read_text(encoding="utf-8"))
            console.print("[green]  ✓ City / province filled[/]")

        if refresh_mvs:
            console.print("[cyan]▶ Refreshing materialized views...[/]")
            cur.execute("REFRESH MATERIALIZED VIEW mv_spot_metrics")
            cur.execute("REFRESH MATERIALIZED VIEW mv_comment_monthly")
            cur.execute("REFRESH MATERIALIZED VIEW mv_city_summary")
            cur.execute("REFRESH MATERIALIZED VIEW mv_level_dist")
            console.print("[green]  ✓ Materialized views refreshed[/]")

        cur.execute("ANALYZE dim_scenic_spot")
        cur.execute("ANALYZE fact_comment")
        pg_actions_done = True

    # -------- Redis 缓存失效（避免清洗后 API 仍命中旧缓存）--------
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis  # type: ignore

        r = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        n_keys = r.dbsize()
        r.flushdb()
        console.print(
            f"[green]  ✓ Redis cache flushed ({n_keys} keys @ {redis_url})[/]"
        )
    except ImportError:
        console.print(
            "[yellow]  ⚠ redis 包未安装，跳过缓存失效；"
            "如有 FastAPI 在跑，请手动 docker exec travel-redis redis-cli FLUSHDB[/]"
        )
    except Exception as e:
        console.print(
            f"[yellow]  ⚠ Redis 不可达 ({e}); 跳过缓存失效。"
            "如 FastAPI 在跑，请手动 FLUSHDB[/]"
        )

    # -------- 摘要 --------
    tbl = Table(title="Loaded to PostgreSQL")
    tbl.add_column("Table", style="cyan")
    tbl.add_column("Rows", justify="right", style="green")
    tbl.add_row("dim_scenic_spot", f"{n_dim:,}")
    tbl.add_row("fact_comment",    f"{n_fact:,}")
    console.print(tbl)

    con.close()


if __name__ == "__main__":
    typer.run(main)
