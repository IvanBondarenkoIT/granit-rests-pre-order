"""Тесты анализа пополнений и сценария Coffee."""
from __future__ import annotations

import pandas as pd

from src.analysis import inventory as inv
from src.analysis import replenishment as rep


def test_cluster_inflow_merges_close_weeks():
    events = pd.DataFrame({
        "week_start": pd.to_datetime(["2026-06-01", "2026-06-08", "2026-07-01"]),
        "inflow": [3000.0, 200.0, 500.0],
    })
    clustered = rep.cluster_inflow_events(events)
    assert len(clustered) == 2
    assert clustered.iloc[0]["qty"] == 3200.0


def test_order_cycle_fallback_target_over_consumption():
    cycle = rep.order_cycle_weeks(None, target_qty=1700.0, weekly_consumption=85.0)
    assert cycle >= 4
    assert abs(cycle - 1700 / 85) < 0.1


def test_coffee_not_urgent_with_max_safety_not_sum():
    """Остаток 4000, расход 72/нед — не срочный заказ при safety=1000 (MAX), не 6270 (SUM)."""
    demand = pd.DataFrame({
        "week_start": pd.date_range("2024-01-01", periods=104, freq="W-MON"),
        "iso_year": [2024] * 52 + [2025] * 52,
        "iso_week": list(range(1, 53)) * 2,
        "true_demand": [72.0] * 104,
    })
    res = inv.compute(
        demand=demand,
        current_stock=3998.0,
        as_of=pd.Timestamp("2026-06-25"),
        lead_time_weeks=4,
        service_level=0.95,
        safety_stock_target=1000.0,
        coverage_weeks=20.0,
    )
    assert res.reorder_date is None or res.reorder_date > pd.Timestamp("2026-06-25")
    assert res.weeks_to_stockout is not None
    assert res.weeks_to_stockout > 40
