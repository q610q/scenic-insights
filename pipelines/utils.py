"""Common helpers for ETL pipelines."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from rich.console import Console

# Windows GBK 控制台无法输出 ✓ 等字符 → 强制 stdout/stderr 改 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, io.UnsupportedOperation):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True, legacy_windows=False)


def load_env(env_file: Path | str = ".env") -> dict[str, str]:
    """简易 .env 加载器（不依赖 python-dotenv 也能用）。

    优先级: 已存在的 os.environ > .env 文件。
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
        loaded[k] = v

    if loaded:
        console.print(f"[dim]Loaded {len(loaded)} keys from {env_path}[/]")
    return loaded


def ensure_dir(path: Path | str) -> Path:
    """确保目录存在，返回 Path 对象。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
