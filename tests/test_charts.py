"""Тесты JSON для графиков."""
from __future__ import annotations

import pandas as pd

from src.web.services.charts import on_hand_chart_data, season_chart_data


def test_season_average_green_dataset():
    sales = pd.DataFrame({
        "iso_year": [2024, 2024, 2025, 2025],
        "iso_week": [10, 11, 10, 11],
        "qty": [100.0, 120.0, 110.0, 130.0],
        "week_start": pd.date_range("2024-01-01", periods=4, freq="W-MON"),
        "amount": [0.0] * 4,
    })
    data = season_chart_data(sales, [2024, 2025])
    avg = [d for d in data["datasets"] if d["label"] == "Средняя"]
    assert len(avg) == 1
    assert avg[0]["borderColor"] == "#006332"
    assert avg[0]["borderWidth"] == 4
    assert avg[0]["order"] == 100
    assert "yearSeries" in data
    assert "isoWeeks" in data
    assert "dateLabels" in data
    assert "yearWeekDates" in data
    assert "2024" in data["yearSeries"]
    assert len(data["labels"]) == 53
    assert data["labels"][0]  # дата dd.mm


def test_on_hand_anchor_in_payload():
    stock = pd.DataFrame({
        "week_start": pd.date_range("2024-01-01", periods=2, freq="W-MON"),
        "inflow": [100.0, 0.0],
        "on_hand": [400.0, 350.0],
    })
    payload = on_hand_chart_data(stock, current_stock=350.0)
    assert payload["currentStock"] == 350.0
    assert payload["datasets"][0]["data"][-1] == 350.0


def test_product_metrics_year_filter_changes_consumption():
    demand = pd.DataFrame({
        "week_start": pd.date_range("2024-01-01", periods=104, freq="W-MON"),
        "iso_year": [2024] * 52 + [2025] * 52,
        "iso_week": list(range(1, 53)) * 2,
        "true_demand": [10.0] * 52 + [50.0] * 52,
    })
    from src.web.services.charts import product_metrics

    only_2024 = product_metrics(demand, 1000.0, 0.0, years=[2024])
    only_2025 = product_metrics(demand, 1000.0, 0.0, years=[2025])
    assert only_2024["weekly_consumption"] == 10.0
    assert only_2025["weekly_consumption"] == 50.0

