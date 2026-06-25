"""Сезонный график: продажи по годам + средняя + остаток."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.gui.theme import COLORS


def median_by_iso_week(sales: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Медиана продаж по iso_week для выбранных годов."""
    sub = sales[sales["iso_year"].isin(years)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["iso_week", "qty_median"])
    grp = sub.groupby("iso_week", as_index=False)["qty"].median()
    return grp.rename(columns={"qty": "qty_median"})


def seasonal_figure(
    sales: pd.DataFrame,
    stock: pd.DataFrame,
    selected_years: list[int],
    unit: str = "",
) -> go.Figure:
    """Комбинированный график: продажи сверху, остаток снизу (зеркально)."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.06,
        subplot_titles=("Продажи по неделям", "Остаток (убывание)"),
    )
    colors = ["#6f4e37", "#ffb869", "#006332", "#82746d", "#004923"]
    for i, yr in enumerate(sorted(selected_years)):
        grp = sales[sales["iso_year"] == yr].sort_values("iso_week")
        if grp.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=grp["iso_week"], y=grp["qty"],
                mode="lines+markers", name=str(yr),
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=4),
            ),
            row=1, col=1,
        )
    if len(selected_years) >= 2:
        med = median_by_iso_week(sales, selected_years)
        if not med.empty:
            fig.add_trace(
                go.Scatter(
                    x=med["iso_week"], y=med["qty_median"],
                    mode="lines", name="Средняя",
                    line=dict(color=COLORS["on_surface"], width=2, dash="dash"),
                ),
                row=1, col=1,
            )
    stk = stock[stock["iso_year"].isin(selected_years)].sort_values("week_start") if selected_years else stock
    if not stk.empty:
        fig.add_trace(
            go.Scatter(
                x=stk["iso_week"], y=stk["stock_end"],
                mode="lines", name="Остаток",
                line=dict(color=COLORS["error"], width=2),
                fill="tozeroy",
                fillcolor="rgba(186, 26, 26, 0.06)",
            ),
            row=2, col=1,
        )
        inflow_weeks = stk[stk["inflow"].fillna(0) > 0]
        if not inflow_weeks.empty:
            fig.add_trace(
                go.Scatter(
                    x=inflow_weeks["iso_week"], y=inflow_weeks["stock_end"],
                    mode="markers", name="Приход",
                    marker=dict(color=COLORS["ok"], size=8, symbol="triangle-up"),
                ),
                row=2, col=1,
            )
    fig.update_xaxes(title_text="Неделя (ISO)", row=2, col=1)
    fig.update_yaxes(title_text=f"Продажи, {unit}/нед", row=1, col=1)
    fig.update_yaxes(title_text=f"Остаток, {unit}", row=2, col=1, autorange="reversed")
    fig.update_layout(
        height=520,
        margin=dict(l=8, r=8, t=48, b=8),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
    )
    return fig
