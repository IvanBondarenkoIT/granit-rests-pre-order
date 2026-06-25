"""Чтение локальной копии GEORGIA.GDB (Firebird 2.5) через embedded-движок.

Read-only. Возвращает pandas.DataFrame.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import pandas as pd

from src.config import SETTINGS


def _prepare_env() -> None:
    """Прописать каталог FB embedded в окружение/поиск DLL (нужно до import fdb)."""
    fb_dir = SETTINGS.fb_client_dir
    os.environ.setdefault("FIREBIRD", fb_dir)
    if fb_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = fb_dir + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory") and os.path.isdir(fb_dir):
        try:
            os.add_dll_directory(fb_dir)
        except (FileNotFoundError, OSError):
            pass


@contextmanager
def connect() -> Iterator[Any]:
    """Контекстный менеджер соединения с локальной .GDB через embedded."""
    _prepare_env()
    import fdb  # импорт после настройки окружения

    con = fdb.connect(
        database=SETTINGS.gdb_path,
        user=SETTINGS.gdb_user,
        password=SETTINGS.gdb_password,
        charset="UTF8",
        fb_library_name=SETTINGS.fb_embed_path,
    )
    try:
        yield con
    finally:
        con.close()


def query_df(sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
    """Выполнить SELECT и вернуть DataFrame (строки чистятся от хвостовых пробелов)."""
    with connect() as con:
        cur = con.cursor()
        cur.execute(sql, list(params or []))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
    return df
