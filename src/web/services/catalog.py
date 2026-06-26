"""Загрузка каталога из локального хранилища."""
from __future__ import annotations

import pandas as pd

from src.analysis import recommend
from src.config import SETTINGS
from src.storage import db


def load_tables() -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for t in ("products", "weekly_sales", "weekly_stock", "weekly_demand", "recommendations", "replenishment_stats"):
        df = db.read_df(t) if db.table_exists(t) else pd.DataFrame()
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"])
        for c in ("reorder_date", "depletion_date", "as_of_date"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        out[t] = df
    return out


def merged_catalog(data: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    data = data or load_tables()
    products = data["products"]
    if products.empty:
        return products
    rec = data.get("recommendations", pd.DataFrame())
    if rec.empty:
        rec = recommend.run()
    return products.merge(rec, on="product_key", how="left", suffixes=("", "_rec"))


def lead_time_weeks() -> int:
    return int(SETTINGS.default_lead_time_weeks)


def product_series(data: dict[str, pd.DataFrame], product_key: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sales = data["weekly_sales"].query("product_key == @product_key").sort_values("week_start")
    stock = data["weekly_stock"].query("product_key == @product_key").sort_values("week_start")
    demand = data["weekly_demand"].query("product_key == @product_key").sort_values("week_start")
    return sales, stock, demand
