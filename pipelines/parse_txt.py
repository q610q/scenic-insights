"""Parse TXT scenic spot detail files into a Parquet dim file.

每个 TXT 形如:
    [SPOT]\n景点名\n[LOCATION]\n地址\n[OPENTIME]\n开放时间...
    INTRO 后含: 开放时间 / 优待政策 / 服务设施 / 温馨提示 等自然语言小节
"""

from __future__ import annotations

import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import typer
from rich.progress import track

from pipelines.utils import console  # 已强制 UTF-8 输出

SECTION_RE = re.compile(r"^\[([A-Z_]+)\]$")
KNOWN_KEYS = {"SPOT", "LOCATION", "OPENTIME", "PHONE", "INTRO"}

# INTRO 后置的自然语言小节标签 → 目标字段名
TAIL_SECTIONS: list[tuple[str, str]] = [
    ("开放时间\n", "open_time_detail"),
    ("优待政策\n", "policies_raw"),
    ("服务设施\n", "facilities_raw"),
    ("温馨提示\n", "tips_raw"),
    ("交通\n",     "traffic_raw"),
    ("地图\n",     "map_raw"),
]
TAIL_LABELS = {label for label, _ in TAIL_SECTIONS} | {"其他信息\n", "周边推荐\n"}


def parse_one(path: Path) -> dict:
    """解析单个 TXT 文件 → dict。"""
    text = path.read_text(encoding="utf-8", errors="replace")

    # ---- Pass 1: [SECTION] 段落 ----
    sections: dict[str, str] = {}
    cur_key: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            if cur_key:
                sections[cur_key] = "\n".join(buf).strip()
            cur_key, buf = m.group(1), []
        else:
            buf.append(line)
    if cur_key:
        sections[cur_key] = "\n".join(buf).strip()

    # ---- Pass 2: INTRO 内置的自然语言小节 ----
    tail: dict[str, str] = {}
    intro = sections.get("INTRO", "")
    for label, key in TAIL_SECTIONS:
        if label in intro:
            section = intro.split(label, 1)[1]
            # 截到下一个 tail 标签为止
            for nxt in TAIL_LABELS:
                if nxt == label:
                    continue
                if nxt in section:
                    section = section.split(nxt, 1)[0]
            tail[key] = section.strip()

    return {
        "spot_name":         sections.get("SPOT", "").strip().lstrip("?"),
        "location":          sections.get("LOCATION", "").strip(),
        "open_time":         sections.get("OPENTIME", "").strip(),
        "phone":             sections.get("PHONE", "").strip(),
        "intro":             intro,
        "open_time_detail":  tail.get("open_time_detail", ""),
        "policies_raw":      tail.get("policies_raw", ""),
        "facilities_raw":    tail.get("facilities_raw", ""),
        "tips_raw":          tail.get("tips_raw", ""),
        "traffic_raw":       tail.get("traffic_raw", ""),
        "raw_path":          str(path),
    }


def main(
    txt_dir: Path = typer.Option(Path("data/txt"), help="TXT 输入目录"),
    out: Path = typer.Option(Path("data/parquet/dim_txt.parquet"), help="输出 Parquet"),
) -> None:
    """解析 TXT 景点详情 → Parquet 单文件"""
    txt_files = sorted(txt_dir.glob("*.txt"))
    if not txt_files:
        console.print(f"[red]No TXT files in {txt_dir}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Parsing {len(txt_files)} TXT files...[/]")
    rows: list[dict] = []
    failed = 0
    for p in track(txt_files, description="Parsing"):
        try:
            rows.append(parse_one(p))
        except Exception as e:
            failed += 1
            console.print(f"[red]Failed {p.name}: {e}[/]")

    out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, out, compression="zstd")
    console.print(
        f"[green]✓ Wrote {len(rows):,} rows ({failed} failed) to {out}[/]"
    )


if __name__ == "__main__":
    typer.run(main)
