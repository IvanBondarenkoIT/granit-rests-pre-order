"""График прогноза исчерпания остатка."""
from __future__ import annotations

import plotly.graph_objects as go

from src.analysis.inventory import InventoryResult
from src.gui.theme import COLORS


def build_depletion_chart(
    res: InventoryResult,
    current_stock: float,
    unit: str = "",
) -> go.Figure:
    df = res.horizon_forecast.copy()
    stock_proj = current_stock - df["forecast"].cumsum()
    return _build_figure(df["week_start"], stock_proj, res, unit)


def _build_figure(weeks, stock_proj, res: InventoryResult, unit: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks, y=stock_proj,
        mode="lines",
        name="Прогноз остатка",
        line=dict(color=COLORS["primary_container"], width=3),
        fill="tozeroy",
        fillcolor="rgba(111, 78, 55, 0.08)",
    ))
    fig.add_hline(
        y=res.reorder_point, line_dash="dot", line_color=COLORS["secondary"],
        annotation_text=f"ROP {res.reorder_point:,.0f}",
    )
    fig.add_hline(
        y=res.safety_stock_target, line_dash="dot", line_color=COLORS["error"],
        annotation_text=f"Страх. {res.safety_stock_target:,.0f}",
    )
    fig.add_hline(y=0, line_color="#82746d", line_width=1)
    if res.reorder_date is not None:
        fig.add_vline(
            x=res.reorder_date, line_dash="dash", line_color=COLORS["ok"],
            annotation_text="Рекомендация", annotation_position="top",
        )
    if res.depletion_date is not None:
        fig.add_vline(
            x=res.depletion_date, line_dash="dash", line_color=COLORS["error"],
            annotation_text="Исчерпание", annotation_position="bottom",
        )
    fig.update_layout(
        height=360,
        margin=dict(l=8, r=8, t=32, b=8),
        hovermode="x unified",
        showlegend=False,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        xaxis_title="Неделя",
        yaxis_title=f"Остаток, {unit}",
    )
    return fig
