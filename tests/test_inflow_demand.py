"""Тесты расчёта расхода по приходам GDDKT."""
from __future__ import annotations

import pandas as pd

from src.etl.inflow_demand import (
    DEFAULT_ORDER_CYCLE_WEEKS,
    implied_weekly_consumption,
    inflow_order_events,
)
from src.etl import transform


def test_inflow_order_events_aggregates_same_day():
    mv = pd.DataFrame({
        "MOVE_DATE": ["2024-01-01", "2024-01-01", "2024-02-15"],
        "QUANT": [100.0, 50.0, 200.0],
    })
    ev = inflow_order_events(mv, min_qty=1.0)
    assert len(ev) == 2
    assert ev.iloc[0]["qty"] == 150.0


def test_implied_weekly_from_two_orders():
  mv = pd.DataFrame({
      "MOVE_DATE": ["2024-01-01", "2024-04-01"],
      "QUANT": [300.0, 300.0],
  })
  # 300 pcs over ~13 weeks
  rate = implied_weekly_consumption(mv, target_qty=300)
  assert 20 < rate < 25


def test_implied_weekly_fallback_target_qty():
    mv = pd.DataFrame({"MOVE_DATE": ["2024-06-01"], "QUANT": [500.0]})
    rate = implied_weekly_consumption(mv, target_qty=260.0)
    assert rate == round(260.0 / DEFAULT_ORDER_CYCLE_WEEKS, 4)


def test_build_demand_inflow_flat_rate():
    ws_stock = pd.DataFrame({
        "week_start": pd.to_datetime(["2024-01-01", "2024-01-08"]),
        "iso_year": [2024, 2024],
        "iso_week": [1, 2],
        "stock_end": [100.0, 90.0],
        "inflow": [0.0, 0.0],
        "outflow": [0.0, 0.0],
    })
    ws_sales = pd.DataFrame({
        "week_start": pd.to_datetime(["2024-01-01", "2024-01-08"]),
        "iso_year": [2024, 2024],
        "iso_week": [1, 2],
        "qty": [0.0, 0.0],
        "amount": [0.0, 0.0],
    })
    stock_mv = pd.DataFrame({
        "MOVE_DATE": ["2024-01-01", "2024-04-01"],
        "QUANT": [300.0, 300.0],
    })
    d = transform.build_demand(
        ws_stock, ws_sales, demand_source="inflow", stock_mv=stock_mv, target_qty=300,
    )
    assert (d["true_demand"] > 0).all()
    assert d["true_demand"].nunique() == 1
