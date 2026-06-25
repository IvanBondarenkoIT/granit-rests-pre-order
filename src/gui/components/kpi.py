"""KPI-чипы Stitch."""
from __future__ import annotations

import streamlit as st

from src.gui.components.status import STATUS_LABELS, STATUS_OK, STATUS_ORDER_NOW, STATUS_SOON


def render_kpi_chips(counts: dict[str, int]) -> None:
    chips = [
        (STATUS_ORDER_NOW, "critical"),
        (STATUS_SOON, "warn"),
        (STATUS_OK, "ok"),
    ]
    parts = ['<div class="kpi-row">']
    for key, css in chips:
        parts.append(
            f'<div class="kpi-chip {css}">'
            f'<div class="num">{counts.get(key, 0)}</div>'
            f'<div class="lbl">{STATUS_LABELS[key]}</div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)
