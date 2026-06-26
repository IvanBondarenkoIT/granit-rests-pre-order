"""Статус срочности позиций для веб-UI."""
from __future__ import annotations

import pandas as pd

STATUS_ORDER_NOW = "order_now"
STATUS_SOON = "soon"
STATUS_OK = "ok"

STATUS_LABELS = {
    STATUS_ORDER_NOW: "Заказать сейчас",
    STATUS_SOON: "Скоро",
    STATUS_OK: "Под контролем",
}

STATUS_BADGE = {
    STATUS_ORDER_NOW: ("Критично", "bg-red-100 text-red-800"),
    STATUS_SOON: ("Скоро", "bg-amber-100 text-amber-800"),
    STATUS_OK: ("Ок", "bg-green-100 text-green-800"),
}


def urgency_status(
    row: pd.Series,
    as_of: pd.Timestamp | None = None,
    lead_time_weeks: int = 8,
) -> str:
    as_of = as_of or pd.Timestamp.today().normalize()
    reorder = row.get("reorder_date")
    if pd.notna(reorder) and pd.Timestamp(reorder).normalize() <= as_of:
        return STATUS_ORDER_NOW
    wts = row.get("weeks_to_stockout")
    if pd.notna(wts):
        if wts <= lead_time_weeks:
            return STATUS_ORDER_NOW
        if wts <= lead_time_weeks * 2:
            return STATUS_SOON
    return STATUS_OK


def status_summary(df: pd.DataFrame, lead_time_weeks: int = 8) -> dict[str, int]:
    counts = {STATUS_ORDER_NOW: 0, STATUS_SOON: 0, STATUS_OK: 0}
    for _, row in df.iterrows():
        counts[urgency_status(row, lead_time_weeks=lead_time_weeks)] += 1
    return counts


def format_date(d) -> str:
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return "—"
    ts = pd.Timestamp(d)
    if pd.isna(ts):
        return "—"
    return ts.strftime("%d.%m.%Y")


def format_gel(amount: float | None) -> str:
    if amount is None or pd.isna(amount):
        return "—"
    return f"~{amount:,.0f} ₾".replace(",", " ")
