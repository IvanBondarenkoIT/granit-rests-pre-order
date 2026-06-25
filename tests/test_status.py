"""Тесты статуса срочности для GUI."""
from __future__ import annotations

import pandas as pd

from src.gui.components.status import STATUS_OK, STATUS_ORDER_NOW, STATUS_SOON, urgency_status


def test_urgency_order_now_by_reorder_date():
    row = pd.Series({"reorder_date": pd.Timestamp("2020-01-01"), "weeks_to_stockout": 20.0})
    assert urgency_status(row, as_of=pd.Timestamp("2025-01-01")) == STATUS_ORDER_NOW


def test_urgency_soon_by_weeks():
    row = pd.Series({"reorder_date": None, "weeks_to_stockout": 12.0})
    assert urgency_status(row, as_of=pd.Timestamp("2025-01-01"), lead_time_weeks=8) == STATUS_SOON


def test_urgency_ok():
    row = pd.Series({"reorder_date": None, "weeks_to_stockout": 50.0})
    assert urgency_status(row, lead_time_weeks=8) == STATUS_OK
