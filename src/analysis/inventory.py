"""Параметры запаса: страховой запас, точка заказа, проекция остатка, дата заказа/исчерпания."""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import pandas as pd

from src.analysis import forecast as fc


def z_for_service_level(service_level: float) -> float:
    return float(NormalDist().inv_cdf(min(max(service_level, 0.5), 0.999)))


@dataclass
class InventoryResult:
    weekly_consumption: float
    lead_time_weeks: float
    safety_stock_calc: float
    safety_stock_target: float
    reorder_point: float
    weeks_to_stockout: float | None
    depletion_date: pd.Timestamp | None
    reorder_date: pd.Timestamp | None
    recommended_order_qty: float
    horizon_forecast: pd.DataFrame


# Потолок расчётного страхового запаса (в долях от спроса за lead time),
# чтобы высокая дисперсия (оптовые всплески) не раздувала заказ.
SAFETY_CAP_FACTOR = 2.0


def safety_stock(weekly_std: float, weekly_mean: float, lead_time_weeks: float,
                 service_level: float) -> float:
    """Страховой запас = z * sigma_lead, ограниченный SAFETY_CAP_FACTOR * спрос за lead."""
    z = z_for_service_level(service_level)
    sigma_lead = weekly_std * math.sqrt(max(lead_time_weeks, 0.0))
    raw = z * sigma_lead
    cap = SAFETY_CAP_FACTOR * weekly_mean * lead_time_weeks
    return min(raw, cap) if cap > 0 else raw


def compute(demand: pd.DataFrame, current_stock: float, as_of: pd.Timestamp,
            lead_time_weeks: float, service_level: float,
            safety_stock_target: float = 0.0, season_window: int = 3,
            coverage_weeks: float | None = None,
            horizon_weeks: int = 104) -> InventoryResult:
    """Расчёт параметров запаса и дат на основе прогноза вперёд.

    coverage_weeks — целевое покрытие сверх lead time при заказе (по умолчанию = lead time).
    """
    stats = fc.demand_stats(demand)
    weekly_mean = stats["weekly_mean"]
    weekly_std = stats["weekly_std"]
    coverage_weeks = lead_time_weeks if coverage_weeks is None else coverage_weeks

    safety_calc = safety_stock(weekly_std, weekly_mean, lead_time_weeks, service_level)
    safety_eff = max(safety_calc, float(safety_stock_target or 0.0))

    horizon = fc.forecast_weeks(demand, as_of, horizon_weeks, season_window)
    demand_over_lead = float(horizon["forecast"].head(int(math.ceil(lead_time_weeks))).sum())
    reorder_point = demand_over_lead + safety_eff

    # Проекция остатка вперёд по прогнозу
    stock = current_stock
    weeks_to_stockout: float | None = None
    reorder_week: int | None = None
    for i, row in horizon.reset_index(drop=True).iterrows():
        if reorder_week is None and stock <= reorder_point:
            reorder_week = i  # уже ниже ROP -> заказывать в начале горизонта (i недель)
        stock -= row["forecast"]
        if weeks_to_stockout is None and stock <= 0:
            weeks_to_stockout = i + 1
            break
    if reorder_week is None and current_stock <= reorder_point:
        reorder_week = 0

    depletion_date = (as_of + pd.Timedelta(weeks=weeks_to_stockout)) if weeks_to_stockout else None
    reorder_date = (as_of + pd.Timedelta(weeks=reorder_week)) if reorder_week is not None else None

    # Уровень «заказать до» S = спрос за (lead + coverage) + страховой запас.
    # Объём = S минус позиция запаса на момент заказа: если уже ниже ROP — срочный
    # заказ от текущего остатка; иначе типовая партия (S - ROP = спрос за coverage).
    cover_n = int(math.ceil(lead_time_weeks + coverage_weeks))
    demand_cover = float(horizon["forecast"].head(cover_n).sum())
    order_up_to = demand_cover + safety_eff
    recommended = max(0.0, order_up_to - min(current_stock, reorder_point))

    return InventoryResult(
        weekly_consumption=round(weekly_mean, 4),
        lead_time_weeks=lead_time_weeks,
        safety_stock_calc=round(safety_calc, 4),
        safety_stock_target=round(safety_eff, 4),
        reorder_point=round(reorder_point, 4),
        weeks_to_stockout=weeks_to_stockout,
        depletion_date=depletion_date,
        reorder_date=reorder_date,
        recommended_order_qty=round(recommended, 4),
        horizon_forecast=horizon,
    )
