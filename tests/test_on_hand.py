"""Тесты симуляции on_hand (приход − продажи, якорь на current_stock)."""
from __future__ import annotations

import pandas as pd

from src.etl.transform import attach_on_hand


def _weeks(n: int = 4) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="W-MON")


def test_on_hand_anchor_last_week():
    ws = _weeks(3)
    stock = pd.DataFrame({
        "week_start": ws,
        "iso_year": [2024, 2024, 2024],
        "iso_week": [1, 2, 3],
        "stock_end": [100.0, 200.0, 150.0],
        "inflow": [100.0, 100.0, 0.0],
        "outflow": [0.0, 0.0, 0.0],
    })
    sales = pd.DataFrame({
        "week_start": ws,
        "iso_year": [2024, 2024, 2024],
        "iso_week": [1, 2, 3],
        "qty": [10.0, 20.0, 30.0],
        "amount": [0.0, 0.0, 0.0],
    })
    current = 500.0
    out = attach_on_hand(stock, sales, current)
    # sim: 90, 170, 140 -> offset = 500 - 140 = 360
    assert out["on_hand"].iloc[-1] == current
    assert out["on_hand"].iloc[0] == 450.0  # 90 + 360


def test_on_hand_inflow_then_sales_drop():
    ws = _weeks(2)
    stock = pd.DataFrame({
        "week_start": ws,
        "iso_year": [2024, 2024],
        "iso_week": [1, 2],
        "stock_end": [300.0, 280.0],
        "inflow": [300.0, 0.0],
        "outflow": [0.0, 0.0],
    })
    sales = pd.DataFrame({
        "week_start": ws,
        "iso_year": [2024, 2024],
        "iso_week": [1, 2],
        "qty": [0.0, 50.0],
        "amount": [0.0, 0.0],
    })
    out = attach_on_hand(stock, sales, current_stock=250.0)
    assert out["on_hand"].iloc[-1] == 250.0
    assert out["on_hand"].iloc[0] == 300.0
    assert out["on_hand"].iloc[1] == 250.0
