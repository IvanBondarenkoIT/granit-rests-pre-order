"""Тесты сезонного графика."""
from __future__ import annotations

import pandas as pd

from src.web.services.charts import median_by_iso_week


def test_median_by_iso_week_two_years():
    sales = pd.DataFrame({
        "iso_year": [2024, 2024, 2025, 2025],
        "iso_week": [10, 11, 10, 11],
        "qty": [100.0, 200.0, 120.0, 180.0],
    })
    med = median_by_iso_week(sales, [2024, 2025])
    w10 = med.loc[med["iso_week"] == 10, "qty_median"].iloc[0]
    assert w10 == 110.0


def test_median_empty_years():
    sales = pd.DataFrame({"iso_year": [2024], "iso_week": [1], "qty": [5.0]})
    med = median_by_iso_week(sales, [2099])
    assert med.empty
