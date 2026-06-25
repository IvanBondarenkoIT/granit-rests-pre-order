"""Экран «Товар» — метрики, исчерпание, сезонность, рекомендация."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis import classify
from src.analysis import inventory as inv
from src.analysis import recommend
from src.config import SETTINGS
from src.gui.charts.depletion import build_depletion_chart
from src.gui.charts.seasonal import seasonal_figure
from src.gui.components.status import format_date
from src.gui.data_loader import format_gel, load_tables, merged_catalog
from src.gui.theme import apply_theme

apply_theme(setup_page=False)

data = load_tables()
products = data["products"]
if products.empty:
    st.error("Нет данных. Запустите ETL.")
    st.stop()

catalog = merged_catalog(data)
keys = catalog["product_key"].tolist()
labels = dict(zip(catalog["product_key"], catalog["label"]))
default_key = st.session_state.get("selected_product_key", keys[0] if keys else None)
default_idx = keys.index(default_key) if default_key in keys else 0

sel_key = st.selectbox("Товар", keys, index=default_idx, format_func=lambda k: labels.get(k, k))
st.session_state["selected_product_key"] = sel_key

prow = catalog[catalog["product_key"] == sel_key].iloc[0]
unit = prow.get("unit", "")
demand = data["weekly_demand"].query("product_key == @sel_key").sort_values("week_start")
sales = data["weekly_sales"].query("product_key == @sel_key").sort_values("week_start")
stock = data["weekly_stock"].query("product_key == @sel_key").sort_values("week_start")

as_of = pd.Timestamp.today().normalize()
current_stock = float(prow.get("current_stock") or 0.0)
sqnt = float(prow.get("safety_stock") or 0.0)
lead_time = int(SETTINGS.default_lead_time_weeks)
service_level = float(SETTINGS.service_level)

dclass = classify.classify(demand["true_demand"]) if not demand.empty \
    else classify.DemandClass("new", float("inf"), 0.0, 0)
res = inv.compute(
    demand=demand if not demand.empty else recommend._empty_demand(),
    current_stock=current_stock,
    as_of=as_of,
    lead_time_weeks=lead_time,
    service_level=service_level,
    safety_stock_target=sqnt,
    season_window=SETTINGS.season_window_weeks,
)

st.markdown(f"### {prow['label']}")
st.caption(f"Класс спроса: **{dclass.label}**")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Остаток", f"{current_stock:,.0f}")
c2.metric("Расход/нед", f"{res.weekly_consumption:,.1f}")
c3.metric("Дата заказа", format_date(res.reorder_date))
c4.metric("Объём", f"{res.recommended_order_qty:,.0f}")

st.subheader("Прогноз остатков")
st.plotly_chart(build_depletion_chart(res, current_stock, unit), use_container_width=True)

st.subheader("Аналитика")
years = sorted(sales["iso_year"].unique()) if not sales.empty else []
sel_years = st.multiselect("Годы", years, default=years[-3:] if len(years) >= 3 else years)
if sel_years and not sales.empty:
    st.plotly_chart(seasonal_figure(sales, stock, sel_years, unit), use_container_width=True)
else:
    st.info("Нет данных продаж для графика сезонности.")

price = prow.get("unit_purchase_price_gel")
cost = None
if price is not None and pd.notna(price):
    cost = float(res.recommended_order_qty) * float(price)

st.markdown(
    f'<div class="sticky-rec">'
    f'<b>Заказать {res.recommended_order_qty:,.0f} {unit}</b> к '
    f'<b>{format_date(res.reorder_date)}</b>'
    f'{" · " + format_gel(cost) if cost else ""}'
    f'<br><span style="color:#50453e;font-size:13px">'
    f'Иначе дефицит {format_date(res.depletion_date)}</span></div>',
    unsafe_allow_html=True,
)
if st.button("Добавить в заказ", type="primary"):
    cart = st.session_state.setdefault("order_cart", set())
    cart.add(sel_key)
    st.session_state["order_cart"] = cart
    st.success(f"{prow['label']} добавлен в заказ.")
