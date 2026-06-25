"""Экран «Обзор» — что заказать в первую очередь."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.gui.components.kpi import render_kpi_chips
from src.gui.components.status import STATUS_OK, STATUS_ORDER_NOW, STATUS_SOON, format_date, status_summary, urgency_status
from src.gui.data_loader import category_of, lead_time_weeks, load_tables, merged_catalog
from src.gui.theme import apply_theme

apply_theme(setup_page=False)

st.title("Обзор")
st.caption("Что заказать в первую очередь")

data = load_tables()
if data["products"].empty:
    st.error("Нет данных. Запустите: `python -m src.etl.run_etl`")
    st.stop()

catalog = merged_catalog(data)
lt = lead_time_weeks()
catalog["_status"] = catalog.apply(lambda r: urgency_status(r, lead_time_weeks=lt), axis=1)

counts = status_summary(catalog, lead_time_weeks=lt)
render_kpi_chips(counts)

filter_opt = st.radio(
    "Фильтр",
    ["Все", "Срочные", "DeLonghi", "Стаканы", "Кофе"],
    horizontal=True,
    label_visibility="collapsed",
)
filtered = catalog.copy()
if filter_opt == "Срочные":
    filtered = filtered[filtered["_status"].isin([STATUS_ORDER_NOW, STATUS_SOON])]
elif filter_opt == "DeLonghi":
    filtered = filtered[filtered["product_key"].apply(lambda k: category_of(k) == "delonghi")]
elif filter_opt == "Стаканы":
    filtered = filtered[filtered["product_key"].apply(lambda k: category_of(k) == "cups")]
elif filter_opt == "Кофе":
    filtered = filtered[filtered["product_key"].apply(lambda k: category_of(k) == "coffee")]

status_order = {STATUS_ORDER_NOW: 0, STATUS_SOON: 1, STATUS_OK: 2}
filtered["_sort"] = filtered["_status"].map(status_order)
filtered = filtered.sort_values(["_sort", "weeks_to_stockout"], na_position="last")

st.markdown(f"**{len(filtered)}** позиций")
for _, row in filtered.iterrows():
    wts = row.get("weeks_to_stockout")
    cover = f"{wts:.0f} нед" if pd.notna(wts) else ">104 нед"
    status = row["_status"]
    badge = {"order_now": "🔴", "soon": "🟠", "ok": "🟢"}.get(status, "")
    cols = st.columns([5, 1])
    with cols[0]:
        st.markdown(
            f"**{badge} {row['label']}**  \n"
            f"{row.get('current_stock', 0):,.0f} {row.get('unit', '')} · запас {cover} · "
            f"заказ до **{format_date(row.get('reorder_date'))}**"
        )
    with cols[1]:
        if st.button("→", key=f"go_{row['product_key']}"):
            st.session_state["selected_product_key"] = row["product_key"]
            st.switch_page("pages/2_Товар.py")
