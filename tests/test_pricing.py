"""Тесты расчёта закупочной цены."""
from __future__ import annotations

import pandas as pd

from src.source.queries import weighted_purchase_price_gel


def test_weighted_purchase_price():
    mv = pd.DataFrame({
        "QUANT": [10.0, 20.0, -5.0],
        "PRICE": [100.0, 110.0, 50.0],
    })
    assert weighted_purchase_price_gel(mv) == 106.6667


def test_weighted_purchase_price_no_inflows():
    mv = pd.DataFrame({"QUANT": [-1.0], "PRICE": [10.0]})
    assert weighted_purchase_price_gel(mv) is None
