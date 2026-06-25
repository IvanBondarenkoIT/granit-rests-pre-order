"""Юнит-тесты расчётных функций: классификация, прогноз, параметры запаса."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import classify
from src.analysis import forecast as fc
from src.analysis import inventory as inv


def _steady_demand(weeks: int = 104, level: float = 10.0) -> pd.DataFrame:
    start = pd.Timestamp("2024-01-01")
    ws = pd.date_range(start, periods=weeks, freq="W-MON")
    iso = ws.isocalendar()
    return pd.DataFrame({"week_start": ws, "iso_week": iso["week"].astype(int),
                         "true_demand": np.full(weeks, level)})


def test_classify_smooth():
    res = classify.classify(_steady_demand()["true_demand"])
    assert res.label == "smooth"


def test_classify_intermittent():
    d = pd.Series([0, 0, 5, 0, 0, 6, 0, 0, 4, 0, 0, 5] * 4)
    res = classify.classify(d)
    assert res.label in {"intermittent", "lumpy"}
    assert res.adi > classify.ADI_THRESHOLD


def test_forecast_steady_level():
    d = _steady_demand(level=10.0)
    f = fc.forecast_weeks(d, pd.Timestamp("2025-12-29"), 8)
    assert len(f) == 8
    assert abs(f["forecast"].mean() - 10.0) < 1.0


def test_weeks_to_stockout_steady():
    d = _steady_demand(level=10.0)
    res = inv.compute(demand=d, current_stock=100.0, as_of=pd.Timestamp("2025-12-29"),
                      lead_time_weeks=4, service_level=0.95, safety_stock_target=0.0)
    # 100 / 10 = ~10 недель
    assert res.weeks_to_stockout is not None
    assert 9 <= res.weeks_to_stockout <= 11


def test_recommended_order_positive_when_below_rop():
    d = _steady_demand(level=10.0)
    res = inv.compute(demand=d, current_stock=5.0, as_of=pd.Timestamp("2025-12-29"),
                      lead_time_weeks=4, service_level=0.95, safety_stock_target=20.0)
    assert res.recommended_order_qty > 0
    assert res.reorder_date is not None
