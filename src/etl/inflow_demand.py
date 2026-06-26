"""Расход по графику приходов (GDDKT) для позиций без продаж в чеках."""
from __future__ import annotations

import pandas as pd

# Стабильный удельный расход: партия предыдущего заказа / интервал до следующего прихода.
DEFAULT_ORDER_CYCLE_WEEKS = 13


def inflow_order_events(stock_mv: pd.DataFrame, min_qty: float = 1.0) -> pd.DataFrame:
    """Значимые приходы: положительный QUANT, агрегат по дате движения."""
    if stock_mv.empty:
        return pd.DataFrame(columns=["move_date", "qty"])
    df = stock_mv.copy()
    df["qty"] = pd.to_numeric(df["QUANT"], errors="coerce").fillna(0.0)
    df = df[df["qty"] >= min_qty].copy()
    if df.empty:
        return pd.DataFrame(columns=["move_date", "qty"])
    df["move_date"] = pd.to_datetime(df["MOVE_DATE"]).dt.normalize()
    return (
        df.groupby("move_date", as_index=False)["qty"].sum()
        .sort_values("move_date")
        .reset_index(drop=True)
    )


def implied_weekly_consumption(
    stock_mv: pd.DataFrame,
    target_qty: float | None = None,
    min_qty: float | None = None,
) -> float:
    """Медиана удельного расхода (партия / недели до следующего прихода).

    Если приходов < 2 — оценка из target_qty и типичного цикла заказа.
    """
    floor = min_qty if min_qty is not None else max((target_qty or 0) * 0.05, 1.0)
    orders = inflow_order_events(stock_mv, min_qty=floor)
    rates: list[float] = []
    for i in range(len(orders) - 1):
        batch = float(orders.iloc[i]["qty"])
        d1 = pd.Timestamp(orders.iloc[i]["move_date"])
        d2 = pd.Timestamp(orders.iloc[i + 1]["move_date"])
        weeks = max((d2 - d1).days / 7.0, 1.0)
        rates.append(batch / weeks)
    if rates:
        return round(float(pd.Series(rates).median()), 4)
    if target_qty and target_qty > 0:
        return round(float(target_qty) / DEFAULT_ORDER_CYCLE_WEEKS, 4)
    return 0.0
