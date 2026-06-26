"""Подключение к локальному хранилищу и запись/чтение таблиц через SQLAlchemy.

DATABASE_URL из .env: postgresql+psycopg2://... (цель) или sqlite:///... (fallback).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import PROJECT_ROOT, SETTINGS

# Таблицы хранилища
TABLES = (
    "products",
    "weekly_sales",
    "weekly_stock",
    "weekly_demand",
    "recommendations",
    "replenishment_stats",
    "sync_state",
)


def _ensure_sqlite_dir(url: str) -> None:
    """Создать каталог под файл SQLite, если его нет."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        db_path = url[len(prefix):]
        p = Path(db_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = SETTINGS.database_url
        _ensure_sqlite_dir(url)
        _engine = create_engine(url, future=True)
    return _engine


def write_df(df: pd.DataFrame, table: str, if_exists: str = "replace") -> int:
    """Записать DataFrame в таблицу. По умолчанию полная перезапись (rebuild)."""
    eng = get_engine()
    df.to_sql(table, eng, if_exists=if_exists, index=False)
    return len(df)


def read_df(table_or_sql: str) -> pd.DataFrame:
    """Прочитать таблицу по имени или произвольный SQL."""
    eng = get_engine()
    sql = table_or_sql
    if table_or_sql.isidentifier():
        sql = f"SELECT * FROM {table_or_sql}"
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn)


def table_exists(table: str) -> bool:
    from sqlalchemy import inspect

    return inspect(get_engine()).has_table(table)
