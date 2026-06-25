"""Прогноз недельного спроса с учётом сезонности (по ряду истинного спроса).

Метод: базовый уровень (среднее за недавний период) * сезонный индекс
(медиана спроса в окне +/- N недель вокруг той же ISO-недели / общая медиана).
Для прерывистого спроса базовый уровень = средняя интенсивность (учитывает нули).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RECENT_WEEKS = 52
SEASONAL_INDEX_CLAMP = (0.3, 3.0)


def _recent_level(demand: pd.DataFrame, weeks: int = RECENT_WEEKS) -> float:
    d = demand.sort_values("week_start")
    tail = d["true_demand"].tail(weeks)
    return float(tail.mean()) if len(tail) else 0.0


def seasonal_index(demand: pd.DataFrame, iso_week: int, window: int = 3) -> float:
    """Сезонный индекс для ISO-недели относительно общей медианы (с заворотом года)."""
    d = demand
    overall = d["true_demand"].median()
    if not overall or overall <= 0:
        return 1.0
    lo, hi = iso_week - window, iso_week + window
    wk = d["iso_week"]
    mask = ((wk >= lo) & (wk <= hi)) | (wk >= lo + 53) | (wk <= hi - 53)
    sub = d.loc[mask, "true_demand"]
    if sub.empty:
        return 1.0
    idx = float(sub.median() / overall)
    return float(np.clip(idx, *SEASONAL_INDEX_CLAMP))


def forecast_weeks(demand: pd.DataFrame, start_week: pd.Timestamp, n_weeks: int,
                   window: int = 3) -> pd.DataFrame:
    """Прогноз на n_weeks вперёд начиная со start_week (понедельники ISO).

    Возвращает DataFrame: week_start, iso_week, forecast.
    """
    level = _recent_level(demand)
    rows = []
    for i in range(1, n_weeks + 1):
        wk_start = start_week + pd.Timedelta(weeks=i)
        iso_week = int(wk_start.isocalendar().week)
        f = max(0.0, level * seasonal_index(demand, iso_week, window))
        rows.append({"week_start": wk_start, "iso_week": iso_week, "forecast": round(f, 4)})
    return pd.DataFrame(rows)


def demand_stats(demand: pd.DataFrame) -> dict:
    """Базовые статистики истинного спроса для расчёта запаса."""
    td = pd.to_numeric(demand["true_demand"], errors="coerce").fillna(0.0)
    recent = td.tail(RECENT_WEEKS)
    return {
        "weekly_mean": float(recent.mean()) if len(recent) else 0.0,
        "weekly_std": float(recent.std(ddof=0)) if len(recent) else 0.0,
        "weekly_median": float(recent.median()) if len(recent) else 0.0,
    }
