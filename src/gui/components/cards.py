"""Карточки товаров на экране Обзор."""
from __future__ import annotations

import streamlit as st

from src.gui.components.status import BADGE_CLASS, STATUS_LABELS, format_date, urgency_status


def render_product_card(row, lead_time_weeks: int = 8) -> None:
    status = urgency_status(row, lead_time_weeks=lead_time_weeks)
    wts = row.get("weeks_to_stockout")
    cover = f"{wts:.0f} нед" if pd_notna(wts) else ">104 нед"
    unit = row.get("unit", "")
    stock = row.get("current_stock", 0)
    reorder = format_date(row.get("reorder_date"))

    html = f"""
    <div class="product-card status-{status}">
      <h4>{row.get('label', row.get('product_key'))}</h4>
      <div class="meta">
        <span class="badge {BADGE_CLASS[status]}">{STATUS_LABELS[status]}</span>
        &nbsp;· остаток {stock:,.0f} {unit} · запас {cover}
        <br>Заказать до: <b>{reorder}</b>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def pd_notna(val) -> bool:
    import pandas as pd
    return val is not None and not (isinstance(val, float) and pd.isna(val))
