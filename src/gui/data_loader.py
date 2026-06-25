"""Загрузка таблиц хранилища для GUI."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis import recommend
from src.config import SETTINGS
from src.storage import db


@st.cache_data(ttl=300)
def load_tables() -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for t in ("products", "weekly_sales", "weekly_stock", "weekly_demand", "recommendations"):
        df = db.read_df(t) if db.table_exists(t) else pd.DataFrame()
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"])
        for c in ("reorder_date", "depletion_date", "as_of_date"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        out[t] = df
    return out


def ensure_recommendations(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Пересчитать рекомендации, если таблица пуста или устарела."""
    rec = data.get("recommendations", pd.DataFrame())
    if rec.empty and not data.get("products", pd.DataFrame()).empty:
        rec = recommend.run()
        data["recommendations"] = rec
    return rec


def merged_catalog(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """products + recommendations для списков и карточек."""
    products = data["products"]
    rec = ensure_recommendations(data)
    if rec.empty:
        return products
    cols = [c for c in rec.columns if c != "product_key" or c == "product_key"]
    merged = products.merge(rec, on="product_key", how="left", suffixes=("", "_rec"))
    return merged


def category_of(product_key: str) -> str:
    """Грубая категория для фильтров."""
    if product_key.startswith("dlsc") or product_key.startswith("drip"):
        return "delonghi"
    if product_key.startswith("cup"):
        return "cups"
    if product_key in ("coffee", "caotina", "caotina_100_dark", "caotina_100_original"):
        return "coffee"
    if product_key in ("bag_paper", "sugar"):
        return "other"
    return "other"


def format_gel(amount: float | None) -> str:
    if amount is None or pd.isna(amount):
        return "—"
    return f"~{amount:,.0f} ₾".replace(",", " ")


def lead_time_weeks() -> int:
    return int(SETTINGS.default_lead_time_weeks)
