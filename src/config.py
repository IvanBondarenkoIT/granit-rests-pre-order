"""Конфигурация проекта: читает .env, отдаёт типизированные настройки."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _abs(path: str) -> str:
    """Абсолютный путь относительно корня проекта."""
    p = Path(path)
    return str(p if p.is_absolute() else (PROJECT_ROOT / p))


@dataclass(frozen=True)
class Settings:
    database_url: str
    gdb_path: str
    fb_client_dir: str
    gdb_user: str
    gdb_password: str
    our_orgn_id: int | None
    stock_report_user_id: int
    proxy_url: str
    proxy_token: str
    proxy_timeout: int
    service_level: float
    default_lead_time_weeks: int
    season_window_weeks: int

    @property
    def fb_embed_path(self) -> str:
        return str(Path(self.fb_client_dir) / "fbembed.dll")


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/granit_rests.sqlite3"),
        gdb_path=_abs(os.getenv("GDB_PATH", "granit bd copy/GEORGIA.GDB")),
        fb_client_dir=_abs(os.getenv("FB_CLIENT_DIR", "tools/fb25")),
        gdb_user=os.getenv("GDB_USER", "SYSDBA"),
        gdb_password=os.getenv("GDB_PASSWORD", "masterkey"),
        our_orgn_id=int(v) if (v := os.getenv("OURORGNID", "").strip()) else None,
        stock_report_user_id=int(os.getenv("STOCK_REPORT_USER_ID", "1")),
        proxy_url=os.getenv("PROXY_API_URL", ""),
        proxy_token=os.getenv("PROXY_API_TOKEN", ""),
        proxy_timeout=int(os.getenv("PROXY_API_TIMEOUT", "90")),
        service_level=float(os.getenv("SERVICE_LEVEL", "0.95")),
        default_lead_time_weeks=int(os.getenv("DEFAULT_LEAD_TIME_WEEKS", "8")),
        season_window_weeks=int(os.getenv("SEASON_WINDOW_WEEKS", "3")),
    )


SETTINGS = get_settings()
