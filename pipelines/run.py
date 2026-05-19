"""Travel data ETL — CLI entry.

Commands:
    clean      — 运行 etl.sql，CSV → dim_spot + comments_dedup + Parquet
    txt        — 解析 TXT 详情 → dim_txt.parquet
    geocode    — 对 dim_spot 做高德 Geocoding
    enrich     — 用 dim_txt 填充 dim_spot 缺失字段
    all        — clean → txt → enrich → geocode
    load       — 灌 Parquet → PostgreSQL
    bootstrap  — 幂等一键（容器入口）：等 PG → 已灌则跳过, 否则 all + load
    stats      — 输出 DuckDB 中表的数据质量摘要

Usage:
    uv run python -m pipelines.run clean
    uv run python -m pipelines.run all
    docker compose --profile bootstrap up etl   # 容器内 bootstrap
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import typer
from rich.table import Table

from pipelines import geocode as geocode_mod
from pipelines import load_to_pg as load_mod
from pipelines import parse_txt as parse_txt_mod
from pipelines.utils import console, load_env
app = typer.Typer(help="Travel data ETL CLI", add_completion=False)


@app.callback()
def _bootstrap() -> None:
    """每次命令执行前自动加载 .env（关键修复：让 AMAP_API_KEY/DATABASE_URL 等环境变量在任何子命令下都生效）。"""
    load_env()


def _connect(path: Path) -> duckdb.DuckDBPyConnection:
    """连接 DuckDB（自动创建父目录）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


@app.command()
def clean(
    sql_file: Path = typer.Option(Path("pipelines/etl.sql")),
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
) -> None:
    """运行 etl.sql：双 schema CSV → comments_dedup + dim_spot + Parquet。"""
    if not sql_file.exists():
        console.print(f"[red]SQL not found: {sql_file}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]▶ Running ETL SQL: {sql_file}[/]")
    con = _connect(duckdb_path)
    con.execute(sql_file.read_text(encoding="utf-8"))

    # 质量摘要
    n_a       = con.execute("SELECT count(*) FROM staging_a").fetchone()[0]
    n_b       = con.execute("SELECT count(*) FROM staging_b").fetchone()[0]
    n_all     = con.execute("SELECT count(*) FROM all_records").fetchone()[0]
    n_real    = con.execute("SELECT count(*) FROM comments_real").fetchone()[0]
    n_spots   = con.execute("SELECT count(*) FROM dim_spot").fetchone()[0]
    n_silent  = con.execute(
        "SELECT count(*) FROM dim_spot WHERE NOT has_real_comments"
    ).fetchone()[0]
    n_2023    = con.execute(
        "SELECT count(*) FROM comments_real WHERE year(co_time) = 2023"
    ).fetchone()[0]

    tbl = Table(title="ETL Summary", show_header=True)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Count", justify="right", style="green")
    tbl.add_row("Schema A staged",      f"{n_a:,}")
    tbl.add_row("Schema B staged",      f"{n_b:,}")
    tbl.add_row("All records (含默认评)", f"{n_all:,}")
    tbl.add_row("Real comments (去重后)", f"{n_real:,}")
    tbl.add_row("Default rate",         f"{(1 - n_real/n_all)*100:.1f}%")
    tbl.add_row("Unique spots (维表)",   f"{n_spots:,}")
    tbl.add_row("  └ silent (无真实评)", f"{n_silent:,}")
    tbl.add_row("2023 comments",        f"{n_2023:,}")
    console.print(tbl)

    con.close()
    console.print(
        f"[green]✓ Parquet written to data/parquet/ "
        f"(fact_comment/year=*/*.parquet + dim_spot.parquet)[/]"
    )


@app.command()
def txt(
    txt_dir: Path = typer.Option(Path("data/txt")),
    out: Path = typer.Option(Path("data/parquet/dim_txt.parquet")),
) -> None:
    """解析 TXT 详情 → dim_txt.parquet。"""
    parse_txt_mod.main(txt_dir=txt_dir, out=out)


@app.command()
def enrich(
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
    txt_parquet: Path = typer.Option(Path("data/parquet/dim_txt.parquet")),
    fuzzy_threshold: int = typer.Option(85, help="rapidfuzz 阈值 (0-100)"),
) -> None:
    """用 dim_txt + rapidfuzz 模糊匹配填充 dim_spot 缺失字段。"""
    if not txt_parquet.exists():
        console.print(f"[red]Missing {txt_parquet} — run 'txt' first[/]")
        raise typer.Exit(1)

    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        console.print("[red]rapidfuzz 未装：pip install rapidfuzz[/]")
        raise typer.Exit(1)

    con = _connect(duckdb_path)
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_txt AS
        SELECT * FROM '{txt_parquet.as_posix()}'
    """)

    # 1. 取所有 dim_spot 名（候选池）
    spot_rows = con.execute(
        "SELECT id, name FROM dim_spot"
    ).fetchall()
    spot_names = [r[1] for r in spot_rows]
    name_to_id = {r[1]: r[0] for r in spot_rows}

    # 2. 取所有 dim_txt 待匹配
    txt_rows = con.execute("""
        SELECT spot_name, intro, phone, location, policies_raw, facilities_raw, tips_raw
        FROM dim_txt
        WHERE spot_name IS NOT NULL AND length(spot_name) >= 2
    """).fetchall()

    # 3. 对每个 TXT 找最相似的 dim_spot
    matched = []
    no_match = 0
    for txt in txt_rows:
        spot_name, intro, phone, location, pol, fac, tips = txt
        # 先精确匹配
        if spot_name in name_to_id:
            best = (spot_name, 100.0)
        else:
            # token_set_ratio 对中文长名匹配较友好
            result = process.extractOne(
                spot_name, spot_names,
                scorer=fuzz.token_set_ratio,
                score_cutoff=fuzzy_threshold,
            )
            if result is None:
                no_match += 1
                continue
            best = (result[0], result[1])
        matched.append((name_to_id[best[0]], intro, phone, location, pol, fac, tips, best[1]))

    # 4. 批量 UPDATE
    if matched:
        con.execute("""
            CREATE TEMP TABLE _enrich_buf (
                spot_id INT, intro VARCHAR, phone VARCHAR, location VARCHAR,
                policies_raw VARCHAR, facilities_raw VARCHAR, tips_raw VARCHAR,
                score DOUBLE
            )
        """)
        con.executemany(
            "INSERT INTO _enrich_buf VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            matched,
        )
        # 用更长的文本覆盖；保留原有 intro/phone 非空字段
        n_updated = con.execute("""
            UPDATE dim_spot AS d
            SET intro    = COALESCE(NULLIF(d.intro, ''),    b.intro),
                phone    = COALESCE(NULLIF(d.phone, ''),    b.phone),
                location = COALESCE(NULLIF(d.location, ''), b.location)
            FROM _enrich_buf b
            WHERE d.id = b.spot_id
              AND b.intro IS NOT NULL AND length(b.intro) > 50
            RETURNING d.id
        """).fetchall()
        console.print(f"[green]✓ Enriched {len(n_updated)} spots[/]")
    console.print(
        f"[cyan]  matched={len(matched)} / no_match={no_match} "
        f"(threshold={fuzzy_threshold})[/]"
    )

    # 5. 写回 Parquet
    con.execute(
        "COPY dim_spot TO 'data/parquet/dim_spot.parquet' "
        "(FORMAT PARQUET, OVERWRITE_OR_IGNORE 1, COMPRESSION 'zstd')"
    )
    con.close()


@app.command(name="geocode")
def geocode_cmd(
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
    api_key: str = typer.Option(None, envvar="AMAP_API_KEY"),
    sleep_sec: float = typer.Option(0.2),
    only_missing: bool = typer.Option(True),
    parquet_out: Path = typer.Option(Path("data/parquet/dim_spot.parquet")),
) -> None:
    """对 dim_spot 做高德 Geocoding（并同步回写 parquet）。"""
    geocode_mod.run_geocode(
        duckdb_path=duckdb_path,
        api_key=api_key or os.environ.get("AMAP_API_KEY"),
        sleep_sec=sleep_sec,
        only_missing=only_missing,
        parquet_out=parquet_out,
    )


@app.command(name="load")
def load_cmd(
    parquet_dir: Path = typer.Option(Path("data/parquet")),
    pg_url: str = typer.Option(None, envvar="DATABASE_URL"),
) -> None:
    """灌 Parquet → PostgreSQL。"""
    load_mod.main(parquet_dir=parquet_dir, pg_url=pg_url)


@app.command()
def stats(
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
) -> None:
    """打印 DuckDB 中表的数据质量摘要。"""
    if not duckdb_path.exists():
        console.print(f"[red]DuckDB not found: {duckdb_path}[/]")
        raise typer.Exit(1)

    con = _connect(duckdb_path)
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]

    tbl = Table(title="DuckDB Tables", show_header=True)
    tbl.add_column("Table", style="cyan")
    tbl.add_column("Rows", justify="right", style="green")
    for t in tables:
        try:
            n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            tbl.add_row(t, f"{n:,}")
        except Exception as e:
            tbl.add_row(t, f"[red]err: {e}[/]")
    console.print(tbl)

    if "dim_spot" in tables:
        console.print("\n[bold]Top 10 景点 (by comment_count_real):[/]")
        rows = con.execute(
            "SELECT name, level, grade, hot, comment_count_real, comment_tier "
            "FROM dim_spot ORDER BY comment_count_real DESC NULLS LAST LIMIT 10"
        ).fetchall()
        for r in rows:
            console.print(f"  {r[0]} | {r[1]} | grade={r[2]} | hot={r[3]} | real={r[4]:,} | tier={r[5]}")

        console.print("\n[bold]景区评论分层:[/]")
        for tier, cnt in con.execute(
            "SELECT comment_tier, count(*) FROM dim_spot GROUP BY comment_tier ORDER BY 1"
        ).fetchall():
            console.print(f"  {tier:<10} {cnt}")

    con.close()


@app.command(name="all")
def all_(
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
) -> None:
    """运行完整 pipeline: clean → txt → enrich → geocode → stats。"""
    load_env()
    clean(sql_file=Path("pipelines/etl.sql"), duckdb_path=duckdb_path)
    txt(txt_dir=Path("data/txt"), out=Path("data/parquet/dim_txt.parquet"))
    enrich(duckdb_path=duckdb_path, txt_parquet=Path("data/parquet/dim_txt.parquet"))

    api_key = os.getenv("AMAP_API_KEY", "")
    if api_key:
        geocode_mod.run_geocode(
            duckdb_path=duckdb_path,
            api_key=api_key,
            parquet_out=Path("data/parquet/dim_spot.parquet"),
        )
    else:
        console.print("[yellow]⚠ AMAP_API_KEY 未设置，跳过 Geocoding[/]")

    stats(duckdb_path=duckdb_path)


@app.command()
def bootstrap(
    pg_url: str = typer.Option(None, envvar="DATABASE_URL"),
    duckdb_path: Path = typer.Option(Path("data/etl.duckdb")),
    csv_dir: Path = typer.Option(Path("data/csv")),
    skip_if_loaded: bool = typer.Option(True, help="PG 已有数据则跳过 ETL（幂等）"),
    wait_secs: int = typer.Option(60, help="等待 PG schema 就绪的最长秒数"),
) -> None:
    """幂等一键：等 PG → 判断是否已灌 → 全流程 ETL → load。

    专为 docker compose 一次性服务设计：
        docker compose --profile bootstrap up etl

    退出码：
        0 — 已存在数据（跳过）或全流程成功
        1 — 配置错误（DATABASE_URL 缺失 / 依赖未装）
        2 — data/csv/ 为空（用户需先放数据）
        3 — PG 在 wait_secs 内未就绪
    """
    import time

    load_env()
    pg_url = pg_url or os.environ.get("DATABASE_URL")
    if not pg_url:
        console.print("[red]✗ DATABASE_URL 未设置[/]")
        raise typer.Exit(1)

    try:
        import psycopg
    except ImportError:
        console.print("[red]✗ psycopg 未装：pip install 'psycopg[binary]'[/]")
        raise typer.Exit(1)

    # psycopg 走同步驱动，去掉 +asyncpg 后缀
    pg_dsn = pg_url
    if "+" in pg_dsn.split("://", 1)[0]:
        scheme, rest = pg_dsn.split("://", 1)
        pg_dsn = f"{scheme.split('+', 1)[0]}://{rest}"

    # 1) 等 PG + schema 就绪（db/init/*.sql 在 PG 容器首启时跑）
    console.print(f"[cyan]▶ Waiting for PG schema (up to {wait_secs}s)...[/]")
    deadline = time.time() + wait_secs
    schema_ready = False
    while time.time() < deadline:
        try:
            with psycopg.connect(pg_dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.dim_scenic_spot')")
                if cur.fetchone()[0] is None:
                    time.sleep(2)
                    continue
                if skip_if_loaded:
                    cur.execute("SELECT count(*) FROM dim_scenic_spot")
                    n = cur.fetchone()[0]
                    if n > 0:
                        console.print(
                            f"[green]✓ PG 已有 {n} 个景点 → 跳过 ETL（幂等）[/]"
                        )
                        return
                schema_ready = True
                break
        except psycopg.OperationalError:
            time.sleep(2)

    if not schema_ready:
        console.print(f"[red]✗ {wait_secs}s 内 PG schema 未就绪[/]")
        raise typer.Exit(3)

    # 2) 检查源数据是否就位
    if not csv_dir.exists() or not any(csv_dir.glob("*.csv")):
        console.print(
            f"[red]✗ {csv_dir}/ 为空。\n"
            f"  请把原始 CSV 放到 ./data/csv/ 后重跑：\n"
            f"    docker compose --profile bootstrap up etl[/]"
        )
        raise typer.Exit(2)

    # 3) 全流程
    console.print("[cyan bold]▶ ETL 开始（clean → txt → enrich → geocode? → load）...[/]")
    all_(duckdb_path=duckdb_path)
    load_mod.main(parquet_dir=Path("data/parquet"), pg_url=pg_url)
    console.print(
        "[green bold]✅ Bootstrap 完成！刷新 http://localhost 查看大屏[/]"
    )


if __name__ == "__main__":
    app()
