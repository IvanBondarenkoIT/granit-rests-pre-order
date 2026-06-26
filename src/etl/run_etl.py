"""Оркестратор ETL: локальная .GDB -> недельные ряды -> локальное хранилище.

Запуск: python -m src.etl.run_etl
"""
from __future__ import annotations

import pandas as pd

from src.config import SETTINGS
from src.critical_products import CriticalItem, resolved_items, unmatched_items
from src.etl import transform
from src.source import queries
from src.storage import db


def _member_ids(item: CriticalItem) -> list[int]:
    if item.kind == "sku" and item.product_id is not None:
        return [item.product_id]
    if item.param_ids:
        members = queries.get_param_member_ids(item.param_ids[0], item.param_ids[1])
        return [int(x) for x in members["ID"].tolist()]
    if item.kind == "group" and item.group_ids:
        members = queries.get_group_member_ids(item.group_ids)
        return [int(x) for x in members["ID"].tolist()]
    return []


def _aggregate_safety(info: pd.DataFrame) -> float | None:
    """Страховой для агрегата: MAX(SQNT) среди SKU, не SUM."""
    sq = pd.to_numeric(info["SAFETY_STOCK"], errors="coerce").dropna()
    if sq.empty:
        return None
    mx = float(sq.max())
    return mx if mx > 0 else None


def _product_row(item: CriticalItem, member_ids: list[int], current_stock: float,
                 unit_purchase_price_gel: float | None = None) -> dict:
    name = item.label
    code = ""
    group_name = ""
    safety = None
    if member_ids:
        info = queries.get_products(member_ids)
        if not info.empty:
            if item.kind == "sku":
                r = info.iloc[0]
                name = r["NAME"]
                code = r.get("CODE", "") or ""
                group_name = r.get("GROUP_NAME", "") or ""
                safety = float(r["SAFETY_STOCK"]) if pd.notna(r["SAFETY_STOCK"]) else None
            else:
                group_name = item.label
                safety = _aggregate_safety(info)
    return {
        "product_key": item.key,
        "label": item.label,
        "kind": item.kind,
        "unit": item.unit,
        "target_qty": item.target_qty,
        "product_id": item.product_id,
        "group_ids": ",".join(map(str, item.group_ids)) if item.group_ids else "",
        "name": name,
        "code": code,
        "group_name": group_name,
        "safety_stock": safety,
        "current_stock": round(current_stock, 4),
        "unit_purchase_price_gel": unit_purchase_price_gel,
        "demand_source": item.demand_source,
        "note": item.note,
    }


def run() -> None:
    items = resolved_items()
    print(f"Обрабатываем {len(items)} позиций (не сопоставлено: {len(unmatched_items())}).")

    products_rows: list[dict] = []
    sales_all, stock_all, demand_all = [], [], []

    for item in items:
        member_ids = _member_ids(item)
        if not member_ids:
            print(f"  [skip] {item.key}: нет member_ids")
            continue

        sales_mv = queries.get_sales_movements(member_ids)
        stock_mv = queries.get_stock_movements(member_ids)

        ws_sales = transform.weekly_sales(sales_mv)
        ws_stock = transform.weekly_stock(stock_mv)
        current_stock = float(pd.to_numeric(stock_mv["QUANT"], errors="coerce").sum()) if not stock_mv.empty else 0.0
        ws_stock = transform.attach_on_hand(ws_stock, ws_sales, current_stock)
        ws_demand = transform.build_demand(
            ws_stock, ws_sales, SETTINGS.season_window_weeks,
            demand_source=item.demand_source,
            stock_mv=stock_mv if item.demand_source == "inflow" else None,
            target_qty=item.target_qty,
        )
        purchase_price = queries.weighted_purchase_price_gel(stock_mv)
        products_rows.append(_product_row(item, member_ids, current_stock, purchase_price))

        for frame in (ws_sales, ws_stock, ws_demand):
            frame.insert(0, "product_key", item.key)
        sales_all.append(ws_sales)
        stock_all.append(ws_stock)
        demand_all.append(ws_demand)
        print(f"  [ok] {item.key}: members={len(member_ids)}, weeks_stock={len(ws_stock)}, "
              f"current_stock={current_stock:.1f}, sales_rows={len(sales_mv)}")

    products_df = pd.DataFrame(products_rows)
    sales_df = pd.concat(sales_all, ignore_index=True) if sales_all else pd.DataFrame()
    stock_df = pd.concat(stock_all, ignore_index=True) if stock_all else pd.DataFrame()
    demand_df = pd.concat(demand_all, ignore_index=True) if demand_all else pd.DataFrame()

    db.write_df(products_df, "products")
    db.write_df(sales_df, "weekly_sales")
    db.write_df(stock_df, "weekly_stock")
    db.write_df(demand_df, "weekly_demand")
    db.write_df(pd.DataFrame([{"key": "last_etl", "value": pd.Timestamp.now().isoformat()}]), "sync_state")

    print(f"\nЗаписано: products={len(products_df)}, weekly_sales={len(sales_df)}, "
          f"weekly_stock={len(stock_df)}, weekly_demand={len(demand_df)}")
    print(f"Хранилище: {SETTINGS.database_url}")


if __name__ == "__main__":
    run()
