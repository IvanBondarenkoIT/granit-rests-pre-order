"""Сборка рекомендаций по заказам: индивидуально + многотоварная синхронизация.

Запуск: python -m src.analysis.recommend
"""
from __future__ import annotations

import pandas as pd

from src.analysis import classify
from src.analysis import forecast as fc
from src.analysis import inventory as inv
from src.config import SETTINGS
from src.storage import db


def _demand_of(product_key: str, weekly_demand: pd.DataFrame) -> pd.DataFrame:
    d = weekly_demand[weekly_demand["product_key"] == product_key].copy()
    d["week_start"] = pd.to_datetime(d["week_start"])
    return d.sort_values("week_start")


def compute_for_item(prod_row: pd.Series, demand: pd.DataFrame,
                     as_of: pd.Timestamp | None = None) -> dict:
    """Рекомендация по одной позиции."""
    as_of = as_of or pd.Timestamp.today().normalize()
    current_stock = float(prod_row.get("current_stock") or 0.0)
    sqnt = float(prod_row.get("safety_stock") or 0.0)
    typical_batch = float(prod_row.get("target_qty") or 0.0)

    dclass = classify.classify(demand["true_demand"]) if not demand.empty \
        else classify.DemandClass("new", float("inf"), 0.0, 0)

    res = inv.compute(
        demand=demand if not demand.empty else _empty_demand(),
        current_stock=current_stock,
        as_of=as_of,
        lead_time_weeks=SETTINGS.default_lead_time_weeks,
        service_level=SETTINGS.service_level,
        safety_stock_target=sqnt,
        season_window=SETTINGS.season_window_weeks,
    )
    unit_price = prod_row.get("unit_purchase_price_gel")
    est_cost = None
    if unit_price is not None and not (isinstance(unit_price, float) and pd.isna(unit_price)):
        est_cost = round(float(res.recommended_order_qty) * float(unit_price), 2)
    return {
        "product_key": prod_row["product_key"],
        "as_of_date": as_of.date().isoformat(),
        "current_stock": round(current_stock, 4),
        "safety_stock_target": res.safety_stock_target,
        "typical_order_qty": typical_batch,
        "weekly_consumption": res.weekly_consumption,
        "demand_class": dclass.label,
        "lead_time_weeks": res.lead_time_weeks,
        "safety_stock_calc": res.safety_stock_calc,
        "reorder_point": res.reorder_point,
        "weeks_to_stockout": res.weeks_to_stockout,
        "depletion_date": res.depletion_date.date().isoformat() if res.depletion_date is not None else None,
        "reorder_date": res.reorder_date.date().isoformat() if res.reorder_date is not None else None,
        "recommended_order_qty": res.recommended_order_qty,
        "service_level": SETTINGS.service_level,
        "unit_purchase_price_gel": unit_price,
        "estimated_order_cost_gel": est_cost,
    }


def _empty_demand() -> pd.DataFrame:
    return pd.DataFrame({"week_start": pd.to_datetime([]), "iso_week": [], "true_demand": []})


def run(as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    products = db.read_df("products")
    weekly_demand = db.read_df("weekly_demand")
    rows = [compute_for_item(r, _demand_of(r["product_key"], weekly_demand), as_of)
            for _, r in products.iterrows()]
    rec = pd.DataFrame(rows)
    db.write_df(rec, "recommendations")
    print(f"Рекомендации рассчитаны: {len(rec)} позиций -> таблица recommendations")
    return rec


def sync_plan(recommendations: pd.DataFrame) -> pd.DataFrame:
    """Многотоварная синхронизация: общий ближайший заказ по самой срочной позиции.

    Общая дата заказа = минимальная reorder_date по группе. Объём каждой позиции
    масштабируется на покрытие до общей даты + lead time (упрощённый JRP).
    """
    rec = recommendations.copy()
    rec["reorder_date_dt"] = pd.to_datetime(rec["reorder_date"], errors="coerce")
    if rec["reorder_date_dt"].notna().any():
        common_date = rec["reorder_date_dt"].min()
    else:
        common_date = pd.Timestamp.today().normalize()
    rec["sync_order_date"] = common_date.date().isoformat()
    rec["urgent"] = rec["reorder_date_dt"] <= common_date + pd.Timedelta(weeks=SETTINGS.default_lead_time_weeks)
    return rec.drop(columns=["reorder_date_dt"])


def multi_item_plan(as_of: pd.Timestamp | None = None,
                    cycle_weeks: int | None = None) -> pd.DataFrame:
    """Совместное пополнение: единый заказ сейчас с общим горизонтом покрытия.

    Все позиции заказываются на общий горизонт T = lead + cycle, чтобы их запас
    «садился» синхронно. Объём = прогноз спроса за T недель + страховой − остаток.
    Возвращает таблицу с order_qty_sync и days_of_cover.
    """
    as_of = as_of or pd.Timestamp.today().normalize()
    cycle_weeks = cycle_weeks if cycle_weeks is not None else SETTINGS.default_lead_time_weeks
    horizon_n = int(SETTINGS.default_lead_time_weeks + cycle_weeks)

    products = db.read_df("products")
    weekly_demand = db.read_df("weekly_demand")
    rows = []
    for _, p in products.iterrows():
        d = _demand_of(p["product_key"], weekly_demand)
        current = float(p.get("current_stock") or 0.0)
        sqnt = float(p.get("safety_stock") or 0.0)
        if d.empty:
            order_qty, cover_weeks = 0.0, None
        else:
            fc_df = fc.forecast_weeks(d, as_of, horizon_n, SETTINGS.season_window_weeks)
            demand_T = float(fc_df["forecast"].sum())
            stats = fc.demand_stats(d)
            safety = max(sqnt, inv.safety_stock(
                stats["weekly_std"], stats["weekly_mean"],
                SETTINGS.default_lead_time_weeks, SETTINGS.service_level))
            order_qty = max(0.0, demand_T + safety - current)
            weekly = stats["weekly_mean"]
            cover_weeks = round(current / weekly, 1) if weekly > 0 else None
        rows.append({
            "product_key": p["product_key"], "label": p["label"], "unit": p.get("unit", ""),
            "current_stock": round(current, 2), "horizon_weeks": horizon_n,
            "order_qty_sync": round(order_qty, 1), "current_cover_weeks": cover_weeks,
        })
    return pd.DataFrame(rows).sort_values("current_cover_weeks", na_position="last")


if __name__ == "__main__":
    df = run()
    plan = sync_plan(df)
    common = plan["sync_order_date"].iloc[0] if not plan.empty else "-"
    print(f"Общая дата ближайшего синхронного заказа: {common}")
    cols = ["product_key", "current_stock", "weekly_consumption", "demand_class",
            "weeks_to_stockout", "reorder_date", "depletion_date", "recommended_order_qty"]
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(df[cols].to_string(index=False))
