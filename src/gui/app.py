"""Точка входа Streamlit — перенаправление на Обзор."""
from __future__ import annotations

import streamlit as st

from src.gui.theme import apply_theme

apply_theme()
st.markdown("### Granit — остатки и предзаказы")
st.caption("Критические расходники · прогноз исчерпания · рекомендации по заказу")
if st.button("Открыть обзор", type="primary"):
    st.switch_page("pages/1_Обзор.py")
