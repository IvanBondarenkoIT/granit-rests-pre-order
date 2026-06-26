"""Анализ истории пополнений по приходам (weekly_stock.inflow / GDDKT).

Запуск: python -m src.analysis.replenishment
"""
from __future__ import annotations

import argparse
import math
from statistics import median

import pandas as pd

from src.config import SETTINGS
from src.critical_products import resolved_items
from src.storage import db

MIN_EVENTS_RELIABLE = 3
CLUSTER_GAP_DAYS = 14
DEFAULT_CYCLE_WEEKS = 13


def inflow_threshold(target_qty: float | None) -> float:
    return max(50.0, (target_qty or 0) * 0.1)


def cluster_inflow_events(events: pd.DataFrame) -> pd.DataFrame:
    """Слить приходы в пределах CLUSTER_GAP_DAYS в одну партию заказа."""
    if events.empty:
        return pd.DataFrame(columns=["order_date", "qty"])
    rows: list[dict] = []
    acc_qty = 0.0
    last_date: pd.Timestamp | None = None
    for row in events.sort_values("week_start").itertuples():
        d = pd.Timestamp(row.week_start).normalize()
        qty = float(row.inflow)
        if last_date is None or (d - last_date).days <= CLUSTER_GAP_DAYS:
            acc_qty += qty
            last_date = d
        else:
            rows.append({"order_date": last_date, "qty": acc_qty})
            acc_qty = qty
            last_date = d
    if acc_qty > 0 and last_date is not None:
        rows.append({"order_date": last_date, "qty": acc_qty})
    return pd.DataFrame(rows)


def detect_order_events(weekly_stock: pd.DataFrame, target_qty: float | None) -> pd.DataFrame:
    """Недели с значимым приходом, сгруппированные в партии."""
    if weekly_stock.empty:
        return pd.DataFrame(columns=["order_date", "qty"])
    df = weekly_stock.copy()
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["inflow"] = pd.to_numeric(df["inflow"], errors="coerce").fillna(0.0)
    threshold = inflow_threshold(target_qty)
    raw = df[df["inflow"] >= threshold][["week_start", "inflow"]].copy()
    return cluster_inflow_events(raw)


def _interval_weeks(dates: pd.Series) -> list[float]:
    if len(dates) < 2:
        return []
    out: list[float] = []
    for i in range(len(dates) - 1):
        days = (pd.Timestamp(dates.iloc[i + 1]) - pd.Timestamp(dates.iloc[i])).days
        out.append(max(days / 7.0, 1.0))
    return out


def order_cycle_weeks(
    stats: dict | pd.Series | None,
    target_qty: float | None,
    weekly_consumption: float,
) -> float:
    """Целевой интервал заказа: из истории или из target_qty / расход."""
    if stats is not None:
        count = int(stats.get("order_count") or 0)
        med = stats.get("median_interval_weeks")
        if count >= MIN_EVENTS_RELIABLE and med is not None and not (
            isinstance(med, float) and math.isnan(med)
        ):
            return float(med)
    if target_qty and weekly_consumption > 0:
        return max(float(target_qty) / weekly_consumption, SETTINGS.default_lead_time_weeks)
    return float(DEFAULT_CYCLE_WEEKS)


def analyze_product(
    product_key: str,
    weekly_stock: pd.DataFrame,
    target_qty: float | None,
    weekly_consumption: float = 0.0,
) -> dict:
    """Метрики пополнения по одной позиции."""
    events = detect_order_events(weekly_stock, target_qty)
    intervals = _interval_weeks(events["order_date"]) if len(events) >= 2 else []
    med_interval = round(median(intervals), 2) if intervals else None
    med_batch = round(float(events["qty"].median()), 2) if not events.empty else None
    last = events.iloc[-1] if not events.empty else None
    implied_cover = None
    if med_batch and weekly_consumption > 0:
        implied_cover = round(med_batch / weekly_consumption, 1)
    model_cycle = SETTINGS.default_lead_time_weeks * 2
    reliable = len(events) >= MIN_EVENTS_RELIABLE and med_interval is not None
    return {
        "product_key": product_key,
        "order_count": len(events),
        "last_order_date": last["order_date"].date().isoformat() if last is not None else None,
        "last_order_qty": round(float(last["qty"]), 2) if last is not None else None,
        "median_batch": med_batch,
        "median_interval_weeks": med_interval,
        "implied_cover_weeks": implied_cover,
        "order_cycle_weeks": round(
            order_cycle_weeks(
                {"order_count": len(events), "median_interval_weeks": med_interval},
                target_qty,
                weekly_consumption,
            ),
            2,
        ),
        "model_cycle_weeks": model_cycle,
        "cycle_reliable": reliable,
        "data_note": (
            "достаточно событий"
            if reliable
            else f"мало приходов ({len(events)}); цикл из target_qty/расхода"
        ),
    }


def run_from_data(
    products: pd.DataFrame,
    weekly_stock: pd.DataFrame,
    rec: pd.DataFrame,
) -> pd.DataFrame:
    """Пересчёт replenishment_stats после recommendations (есть weekly_consumption)."""
    wc_map = (
        rec.set_index("product_key")["weekly_consumption"].to_dict()
        if not rec.empty and "weekly_consumption" in rec.columns
        else {}
    )
    rows = []
    for _, p in products.iterrows():
        key = p["product_key"]
        target = p.get("target_qty")
        ws = weekly_stock[weekly_stock["product_key"] == key] if not weekly_stock.empty else pd.DataFrame()
        wc = float(wc_map.get(key) or 0.0)
        rows.append(analyze_product(key, ws, target, wc))
    df = pd.DataFrame(rows)
    db.write_df(df, "replenishment_stats")
    return df


def run() -> pd.DataFrame:
    """Пересчитать replenishment_stats для всех критических позиций."""
    products = db.read_df("products") if db.table_exists("products") else pd.DataFrame()
    stock_all = db.read_df("weekly_stock") if db.table_exists("weekly_stock") else pd.DataFrame()
    rec = db.read_df("recommendations") if db.table_exists("recommendations") else pd.DataFrame()
    wc_map = (
        rec.set_index("product_key")["weekly_consumption"].to_dict()
        if not rec.empty and "weekly_consumption" in rec.columns
        else {}
    )
    rows = []
    for item in resolved_items():
        p = products[products["product_key"] == item.key] if not products.empty else pd.DataFrame()
        target = (
            float(p.iloc[0]["target_qty"])
            if not p.empty and pd.notna(p.iloc[0].get("target_qty"))
            else item.target_qty
        )
        ws = stock_all[stock_all["product_key"] == item.key] if not stock_all.empty else pd.DataFrame()
        wc = float(wc_map.get(item.key) or 0.0)
        rows.append(analyze_product(item.key, ws, target, wc))
    df = pd.DataFrame(rows)
    db.write_df(df, "replenishment_stats")
    print(f"Пополнения: {len(df)} позиций -> replenishment_stats")
    return df


def load_stats_map() -> dict[str, dict]:
    if not db.table_exists("replenishment_stats"):
        return {}
    df = db.read_df("replenishment_stats")
    return {r["product_key"]: r for r in df.to_dict("records")}


def print_report(df: pd.DataFrame | None = None) -> None:
    df = df if df is not None else (
        db.read_df("replenishment_stats") if db.table_exists("replenishment_stats") else pd.DataFrame()
    )
    if df.empty:
        print("Нет данных replenishment_stats. Запустите: python -m src.analysis.replenishment")
        return
    cols = [
        "product_key", "order_count", "median_interval_weeks", "median_batch",
        "order_cycle_weeks", "last_order_date", "data_note",
    ]
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(df[cols].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="Только отчёт без пересчёта")
    args = parser.parse_args()
    if args.report:
        print_report()
    else:
        print_report(run())
