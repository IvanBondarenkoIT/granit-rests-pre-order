"""Экран «Заказ» — совместное пополнение и сумма в лари."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis import recommend
from src.config import SETTINGS
from src.gui.data_loader import format_gel, load_tables, merged_catalog
from src.gui.theme import apply_theme

apply_theme(setup_page=False)

st.title("Заказ")
st.caption("Совместное пополнение поставщику")

data = load_tables()
if data["products"].empty:
    st.error("Нет данных. Запустите ETL.")
    st.stop()

catalog = merged_catalog(data)
rec = catalog
plan = recommend.sync_plan(rec)
common = plan["sync_order_date"].iloc[0] if not plan.empty else "—"
st.info(f"Ближайшая общая дата заказа: **{common}**")

cycle = st.slider(
    "Горизонт покрытия сверх срока поставки, нед.",
    2, 26, int(SETTINGS.default_lead_time_weeks),
)
mip = recommend.multi_item_plan(cycle_weeks=cycle)
mip = mip.merge(
    catalog[["product_key", "unit_purchase_price_gel"]],
    on="product_key", how="left",
)

cart_default = st.session_state.get("order_cart", set())
selected: dict[str, bool] = {}
quantities: dict[str, float] = {}

st.markdown("#### Позиции")
total_gel = 0.0
count = 0
for _, row in mip.iterrows():
    key = row["product_key"]
    default_on = key in cart_default or float(row["order_qty_sync"]) > 0
    cols = st.columns([1, 4, 2, 2])
    with cols[0]:
        selected[key] = st.checkbox("", value=default_on, key=f"chk_{key}", label_visibility="collapsed")
    with cols[1]:
        st.markdown(f"**{row['label']}**  \n{row['current_stock']:,.0f} {row['unit']}")
    with cols[2]:
        qty = st.number_input(
            "шт", min_value=0.0, value=float(row["order_qty_sync"]),
            key=f"qty_{key}", label_visibility="collapsed",
        )
        quantities[key] = qty
    price = row.get("unit_purchase_price_gel")
    line_cost = float(qty) * float(price) if price is not None and pd.notna(price) else None
    with cols[3]:
        st.markdown(format_gel(line_cost) if line_cost else "—")
    if selected[key] and qty > 0:
        count += 1
        if line_cost:
            total_gel += line_cost

st.markdown("---")
st.markdown(f"### Позиций: **{count}** · **{format_gel(total_gel) if total_gel else '—'}**")
st.caption("Сумма ориентировочная · закупка из GDDKT.PRICE · без НДС")

if st.button("Оформить список", type="primary"):
    lines = []
    for _, row in mip.iterrows():
        key = row["product_key"]
        if selected.get(key) and quantities.get(key, 0) > 0:
            price = row.get("unit_purchase_price_gel")
            qty = quantities[key]
            cost = f" · {format_gel(qty * float(price))}" if price is not None and pd.notna(price) else ""
            lines.append(f"- {row['label']}: {qty:,.0f} {row['unit']}{cost}")
    if lines:
        st.code("\n".join(lines), language=None)
    else:
        st.warning("Отметьте позиции с ненулевым количеством.")
