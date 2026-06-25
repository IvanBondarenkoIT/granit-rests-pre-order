"""Stitch design tokens и инъекция CSS в Streamlit."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

COLORS = {
    "surface": "#fcf9f5",
    "surface_container": "#f0ede9",
    "on_surface": "#1c1c1a",
    "on_surface_variant": "#50453e",
    "primary": "#553722",
    "primary_container": "#6f4e37",
    "secondary": "#875208",
    "secondary_container": "#ffb869",
    "tertiary": "#004923",
    "error": "#ba1a1a",
    "outline_variant": "#d4c3ba",
    "ok": "#006332",
    "warn": "#875208",
    "critical": "#ba1a1a",
}

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": COLORS["surface"],
        "plot_bgcolor": COLORS["surface"],
        "font": {"family": "Inter, sans-serif", "color": COLORS["on_surface"]},
        "colorway": [COLORS["primary_container"], COLORS["secondary_container"], "#004923", "#82746d"],
    }
}


def apply_theme(*, setup_page: bool = True) -> None:
    """Применить page_config и stitch.css."""
    if setup_page:
        try:
            st.set_page_config(
                page_title="Granit — остатки",
                page_icon="☕",
                layout="centered",
                initial_sidebar_state="collapsed",
            )
        except Exception:
            pass
    css_path = ASSETS_DIR / "stitch.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
