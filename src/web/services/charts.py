"""JSON-данные для Chart.js."""
from __future__ import annotations

import pandas as pd

from src.analysis import classify
from src.analysis import forecast as fc
from src.analysis import inventory as inv
from src.analysis import recommend
from src.analysis import replenishment as rep
from src.config import SETTINGS

YEAR_COLORS = ["#6f4e37", "#8a6a52", "#a5876d", "#c0a489", "#9a7b62"]
AVG_COLOR = "#006332"


def _iso_week_labels(df: pd.DataFrame) -> list[int]:
    return [int(x) for x in df["iso_week"].tolist()]


def median_by_iso_week(sales: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    sub = sales[sales["iso_year"].isin(years)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["iso_week", "qty_median"])
    return sub.groupby("iso_week", as_index=False)["qty"].median().rename(columns={"qty": "qty_median"})


YEAR_COLORS = ["#6f4e37", "#8a6a52", "#a5876d", "#c0a489", "#9a7b62"]
AVG_COLOR = "#006332"
SEASON_ISO_WEEKS = list(range(1, 54))


def _iso_week_monday(year: int, iso_week: int) -> pd.Timestamp:
    """Понедельник ISO-недели (fallback для редкой 53-й)."""
    try:
        return pd.Timestamp.fromisocalendar(year, iso_week, 1)
    except ValueError:
        return pd.Timestamp.fromisocalendar(year, min(iso_week, 52), 1)


def _season_axis_dates(iso_weeks: list[int], ref_year: int) -> list[str]:
    """Подписи оси X: понедельник недели в опорном году."""
    return [_iso_week_monday(ref_year, w).strftime("%d.%m") for w in iso_weeks]


def _year_week_dates(sales: pd.DataFrame, year: int, iso_weeks: list[int]) -> list[str | None]:
    """Фактические даты недель по году (для подсказки)."""
    grp = sales[sales["iso_year"] == year]
    by_week: dict[int, str] = {}
    for row in grp.itertuples():
        wk = int(row.iso_week)
        by_week[wk] = pd.Timestamp(row.week_start).strftime("%d.%m.%Y")
    return [by_week.get(w) for w in iso_weeks]


def season_chart_data(sales: pd.DataFrame, years: list[int] | None = None) -> dict:
    if sales.empty:
        return {
            "labels": [], "datasets": [], "yearSeries": {},
            "isoWeeks": [], "dateLabels": [], "yearWeekDates": {},
        }
    all_years = sorted(int(y) for y in sales["iso_year"].unique())
    selected = years if years else all_years
    iso_weeks = SEASON_ISO_WEEKS
    ref_year = selected[-1]
    date_labels = _season_axis_dates(iso_weeks, ref_year)
    year_week_dates = {str(yr): _year_week_dates(sales, yr, iso_weeks) for yr in selected}
    year_series: dict[str, list[float | None]] = {}
    datasets = []
    for i, yr in enumerate(selected):
        grp = sales[sales["iso_year"] == yr].sort_values("iso_week")
        by_week = {int(r.iso_week): float(r.qty) for r in grp.itertuples()}
        data = [by_week.get(w) for w in iso_weeks]
        year_series[str(yr)] = data
        datasets.append({
            "label": str(yr),
            "data": data,
            "borderColor": YEAR_COLORS[i % len(YEAR_COLORS)],
            "backgroundColor": "transparent",
            "borderWidth": 2,
            "pointRadius": 2,
            "spanGaps": True,
            "isYear": True,
            "order": 1,
        })
    avg_data = _median_series(year_series, [str(y) for y in selected], iso_weeks)
    if len(selected) >= 2:
        datasets.append({
            "label": "Средняя",
            "data": avg_data,
            "borderColor": AVG_COLOR,
            "backgroundColor": "transparent",
            "borderWidth": 4,
            "pointRadius": 0,
            "spanGaps": True,
            "isAverage": True,
            "order": 100,
        })
    return {
        "labels": date_labels,
        "isoWeeks": iso_weeks,
        "dateLabels": date_labels,
        "refYear": ref_year,
        "yearWeekDates": year_week_dates,
        "datasets": datasets,
        "yearSeries": year_series,
    }


def _median_series(
    year_series: dict[str, list[float | None]],
    active_years: list[str],
    labels: list[int],
) -> list[float | None]:
    """Медиана по iso_week для активных годов."""
    out: list[float | None] = []
    for idx in range(len(labels)):
        vals = [
            year_series[y][idx] for y in active_years
            if y in year_series and year_series[y][idx] is not None
        ]
        out.append(float(pd.Series(vals).median()) if vals else None)
    return out


def on_hand_chart_data(stock: pd.DataFrame, current_stock: float) -> dict:
    if stock.empty or "on_hand" not in stock.columns:
        return {"labels": [], "datasets": [], "inflowIndexes": []}
    labels = [pd.Timestamp(w).strftime("%d.%m.%y") for w in stock["week_start"]]
    values = [float(x) if pd.notna(x) else None for x in stock["on_hand"]]
    inflow_idx = [
        i for i, row in enumerate(stock.itertuples())
        if float(getattr(row, "inflow", 0) or 0) > 0
    ]
    return {
        "labels": labels,
        "datasets": [{
            "label": "Остаток на складе",
            "data": values,
            "borderColor": "#6f4e37",
            "backgroundColor": "rgba(111, 78, 55, 0.08)",
            "fill": True,
            "borderWidth": 2,
            "pointRadius": 0,
        }],
        "inflowIndexes": inflow_idx,
        "currentStock": current_stock,
    }


def forecast_chart_data(
    demand: pd.DataFrame,
    current_stock: float,
    safety_stock: float,
) -> dict:
    as_of = pd.Timestamp.today().normalize()
    dclass = classify.classify(demand["true_demand"]) if not demand.empty \
        else classify.DemandClass("new", float("inf"), 0.0, 0)
    res = inv.compute(
        demand=demand if not demand.empty else recommend._empty_demand(),
        current_stock=current_stock,
        as_of=as_of,
        lead_time_weeks=SETTINGS.default_lead_time_weeks,
        service_level=SETTINGS.service_level,
        safety_stock_target=safety_stock,
        season_window=SETTINGS.season_window_weeks,
    )
    horizon = res.horizon_forecast.copy()
    stock_proj = current_stock - horizon["forecast"].cumsum()
    labels = [pd.Timestamp(w).strftime("%d.%m.%y") for w in horizon["week_start"]]
    return {
        "labels": labels,
        "datasets": [{
            "label": "Прогноз остатка",
            "data": [float(x) for x in stock_proj],
            "borderColor": "#6f4e37",
            "backgroundColor": "rgba(111, 78, 55, 0.08)",
            "fill": True,
            "borderWidth": 3,
            "pointRadius": 0,
        }],
        "rop": res.reorder_point,
        "safety": res.safety_stock_target,
        "reorderDate": format_date(res.reorder_date),
        "depletionDate": format_date(res.depletion_date),
        "demandClass": dclass.label,
        "weeklyConsumption": res.weekly_consumption,
        "recommendedQty": res.recommended_order_qty,
    }


def format_date(d) -> str | None:
    if d is None:
        return None
    ts = pd.Timestamp(d)
    if pd.isna(ts):
        return None
    return ts.strftime("%d.%m.%Y")


def product_metrics(
    demand: pd.DataFrame,
    current_stock: float,
    safety_stock: float,
    years: list[int] | None = None,
    unit_price: float | None = None,
    target_qty: float | None = None,
    rep_stats: dict | None = None,
) -> dict:
    """Метрики запаса по спросу за выбранные календарные годы (iso_year)."""
    d = demand
    if years:
        d = demand[demand["iso_year"].isin(years)].copy()
    if d.empty:
        return _empty_metrics()
    as_of = pd.Timestamp.today().normalize()
    recent_weeks = len(d) if years else fc.RECENT_WEEKS
    pre = inv.compute(
        demand=d,
        current_stock=current_stock,
        as_of=as_of,
        lead_time_weeks=SETTINGS.default_lead_time_weeks,
        service_level=SETTINGS.service_level,
        safety_stock_target=safety_stock,
        season_window=SETTINGS.season_window_weeks,
        recent_weeks=recent_weeks,
    )
    coverage = rep.order_cycle_weeks(rep_stats, target_qty, pre.weekly_consumption)
    res = inv.compute(
        demand=d,
        current_stock=current_stock,
        as_of=as_of,
        lead_time_weeks=SETTINGS.default_lead_time_weeks,
        service_level=SETTINGS.service_level,
        safety_stock_target=safety_stock,
        season_window=SETTINGS.season_window_weeks,
        recent_weeks=recent_weeks,
        coverage_weeks=coverage,
    )
    is_urgent = res.reorder_date is not None and res.reorder_date.normalize() <= as_of
    below_rop = current_stock <= res.reorder_point
    display_qty = res.recommended_order_qty if is_urgent else 0.0
    cost = None
    if is_urgent and unit_price is not None and not (
        isinstance(unit_price, float) and pd.isna(unit_price)
    ):
        cost = f"~{display_qty * float(unit_price):,.0f} ₾".replace(",", " ")
    policy = (
        "Ниже точки заказа — пополнение срочно"
        if is_urgent
        else f"Запас выше ROP ({res.reorder_point:,.0f}) — заказ не срочен".replace(",", " ")
    )
    return {
        "weekly_consumption": res.weekly_consumption,
        "depletion_date": format_date(res.depletion_date),
        "reorder_date": format_date(res.reorder_date),
        "recommended_order_qty": display_qty,
        "raw_recommended_order_qty": res.recommended_order_qty,
        "reorder_point": res.reorder_point,
        "order_cycle_weeks": coverage,
        "is_urgent": is_urgent,
        "below_rop": below_rop,
        "policy_note": policy,
        "cost_gel": cost,
    }


def _empty_metrics() -> dict:
    return {
        "weekly_consumption": None,
        "depletion_date": None,
        "reorder_date": None,
        "recommended_order_qty": None,
        "raw_recommended_order_qty": None,
        "reorder_point": None,
        "order_cycle_weeks": None,
        "is_urgent": False,
        "below_rop": False,
        "policy_note": "",
        "cost_gel": None,
    }


def format_metrics_display(metrics: dict) -> dict:
    """Форматирование чисел для шаблона."""
    wc = metrics.get("weekly_consumption")
    qty = metrics.get("recommended_order_qty")
    is_urgent = metrics.get("is_urgent", False)
    rop = metrics.get("reorder_point")
    return {
        "consumption_fmt": f"{wc:,.1f}".replace(",", " ") if wc is not None else "—",
        "depletion_date": metrics.get("depletion_date") or "—",
        "reorder_date": metrics.get("reorder_date") or "—",
        "qty_fmt": (
            f"{qty:,.0f}".replace(",", " ")
            if is_urgent and qty is not None and qty > 0
            else "—"
        ),
        "rop_fmt": f"{rop:,.0f}".replace(",", " ") if rop is not None else "—",
        "policy_note": metrics.get("policy_note") or "",
        "is_urgent": is_urgent,
        "cost_gel": metrics.get("cost_gel") if is_urgent else None,
    }


def season_years(sales: pd.DataFrame) -> list[int]:
    if sales.empty:
        return []
    return sorted(int(y) for y in sales["iso_year"].unique())


def build_chart_payload(
    chart_type: str,
    sales: pd.DataFrame,
    stock: pd.DataFrame,
    demand: pd.DataFrame,
    current_stock: float,
    safety_stock: float,
    years: list[int] | None = None,
) -> dict:
    if chart_type == "season":
        return {"type": "season", **season_chart_data(sales, years)}
    if chart_type == "stock":
        return {"type": "stock", **on_hand_chart_data(stock, current_stock)}
    if chart_type == "forecast":
        return {"type": "forecast", **forecast_chart_data(demand, current_stock, safety_stock)}
    raise ValueError(f"Unknown chart type: {chart_type}")
