"""Преобразование движений в недельные ряды (ISO-недели) и сигнал спроса."""
from __future__ import annotations

import numpy as np
import pandas as pd


def week_start(dates: pd.Series) -> pd.Series:
    """Понедельник ISO-недели для каждой даты."""
    d = pd.to_datetime(dates)
    return (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()


def _iso_cols(week_start_series: pd.Series) -> pd.DataFrame:
    iso = pd.to_datetime(week_start_series).dt.isocalendar()
    return pd.DataFrame({"iso_year": iso["year"].astype(int), "iso_week": iso["week"].astype(int)})


def weekly_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Недельные продажи (qty, amount) из строк чеков."""
    cols = ["week_start", "iso_year", "iso_week", "qty", "amount"]
    if sales_df.empty:
        return pd.DataFrame(columns=cols)
    df = sales_df.copy()
    df["qty"] = pd.to_numeric(df["QTY"], errors="coerce").fillna(0.0)
    df["price"] = pd.to_numeric(df["PRICE"], errors="coerce").fillna(0.0)
    df["amount"] = df["qty"] * df["price"]
    df["week_start"] = week_start(df["SALE_DATE"])
    g = df.groupby("week_start", as_index=False).agg(qty=("qty", "sum"), amount=("amount", "sum"))
    g = pd.concat([g, _iso_cols(g["week_start"])], axis=1)
    return g[cols].sort_values("week_start").reset_index(drop=True)


def weekly_stock(stock_df: pd.DataFrame) -> pd.DataFrame:
    """Недельные остатки: stock_end (нараст. сумма QUANT), inflow, outflow.

    Сетка недель — сплошная от первой до последней недели движения.
    """
    cols = ["week_start", "iso_year", "iso_week", "stock_end", "inflow", "outflow"]
    if stock_df.empty:
        return pd.DataFrame(columns=cols)
    df = stock_df.copy()
    df["quant"] = pd.to_numeric(df["QUANT"], errors="coerce").fillna(0.0)
    df["week_start"] = week_start(df["MOVE_DATE"])
    per_week = df.groupby("week_start").agg(
        net=("quant", "sum"),
        inflow=("quant", lambda s: s[s > 0].sum()),
        outflow=("quant", lambda s: -s[s < 0].sum()),
    ).reset_index()

    full_idx = pd.date_range(per_week["week_start"].min(), per_week["week_start"].max(), freq="W-MON")
    per_week = per_week.set_index("week_start").reindex(full_idx).rename_axis("week_start").reset_index()
    per_week[["net", "inflow", "outflow"]] = per_week[["net", "inflow", "outflow"]].fillna(0.0)
    per_week["stock_end"] = per_week["net"].cumsum()

    out = pd.concat([per_week, _iso_cols(per_week["week_start"])], axis=1)
    return out[cols].sort_values("week_start").reset_index(drop=True)


def attach_on_hand(
    ws_stock: pd.DataFrame,
    ws_sales: pd.DataFrame,
    current_stock: float,
) -> pd.DataFrame:
    """Симуляция остатка на складе: приход − продажи, якорь на current_stock в последней неделе.

    on_hand[w] = on_hand[w-1] + inflow[w] - sales[w] (после сдвига offset).
    Для графика в UI; KPI «сейчас» — леджер products.current_stock.
    """
    cols = list(ws_stock.columns) if not ws_stock.empty else [
        "week_start", "iso_year", "iso_week", "stock_end", "inflow", "outflow", "on_hand",
    ]
    if ws_stock.empty:
        return pd.DataFrame(columns=cols)

    sales_map: dict = {}
    if not ws_sales.empty:
        sales_map = dict(zip(ws_sales["week_start"], ws_sales["qty"]))

    sim: list[float] = []
    prev = 0.0
    for _, row in ws_stock.iterrows():
        inflow = float(row.get("inflow") or 0.0)
        sales = float(sales_map.get(row["week_start"], 0.0))
        prev = prev + inflow - sales
        sim.append(prev)

    out = ws_stock.copy()
    offset = float(current_stock) - sim[-1] if sim else 0.0
    out["on_hand"] = np.round(np.array(sim) + offset, 4)
    return out


def build_demand(
    ws_stock: pd.DataFrame,
    ws_sales: pd.DataFrame,
    season_window: int = 3,
    *,
    demand_source: str = "sales",
    stock_mv: pd.DataFrame | None = None,
    target_qty: float | None = None,
) -> pd.DataFrame:
    """Сигнал спроса (потребление) с восстановлением истинного спроса при дефиците.

    В этой БД движения GDDKT для критических товаров содержат ТОЛЬКО приход
    (outflow=0), а реальное потребление пишется в продажах STORZAKAZDT. Поэтому
    базовый сигнал спроса = observed_sales; остаток для графика — леджер GDDKT
    (нараст. сумма QUANT, авторитетный остаток отчётов).

    stockout_flag: неделя считается дефицитной, если потребление было НУЛЕВЫМ при
    положительном медианном спросе по этой ISO-неделе (косвенный признак нехватки),
    либо stock_end<=0. В такие недели true_demand поднимается до сезонного ожидания.
    Ограничение: без точного исторического on-hand детекция дефицита приблизительна
    (см. docs/REQUIREMENTS_WORKSHEET.md, раздел B/C).
    """
    cols = ["week_start", "iso_year", "iso_week", "observed_sales", "outflow",
            "stock_end", "stockout_flag", "true_demand"]
    spine = ws_stock if not ws_stock.empty else ws_sales
    if spine is None or spine.empty:
        return pd.DataFrame(columns=cols)

    df = spine[["week_start", "iso_year", "iso_week"]].copy()
    stk = ws_stock[["week_start", "stock_end", "outflow"]] if not ws_stock.empty \
        else pd.DataFrame(columns=["week_start", "stock_end", "outflow"])
    sales = ws_sales[["week_start", "qty"]].rename(columns={"qty": "observed_sales"}) if not ws_sales.empty \
        else pd.DataFrame(columns=["week_start", "observed_sales"])
    df = df.merge(stk, on="week_start", how="left").merge(sales, on="week_start", how="left")
    for c in ("stock_end", "outflow", "observed_sales"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce").fillna(0.0)

    # Без надёжного исторического on-hand детекцию дефицита не делаем (иначе фабрикуем
    # спрос у редко-продаваемых позиций). true_demand = observed_sales.
    # Механизм unconstraining включится, когда появится точный on-hand (см. worksheet).
    df["stockout_flag"] = 0
    if demand_source == "inflow" and stock_mv is not None:
        from src.etl.inflow_demand import implied_weekly_consumption

        rate = implied_weekly_consumption(stock_mv, target_qty=target_qty)
        df["true_demand"] = rate
    else:
        df["true_demand"] = np.round(df["observed_sales"], 4)
    return df[cols].sort_values("week_start").reset_index(drop=True)
