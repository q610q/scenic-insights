"""Travel data ETL pipelines.

Modules:
    etl.sql        — DuckDB 主清洗 SQL（双 schema 联合 + 去重 + 落 Parquet）
    parse_txt.py   — TXT 景点详情解析
    geocode.py     — 高德 Web API Geocoding
    run.py         — CLI 入口
    utils.py       — 共用工具
"""

__version__ = "0.1.0"
