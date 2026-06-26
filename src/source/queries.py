"""SQL-запросы к Firebird (GEORGIA.GDB). Канонические правила домена — см. AGENTS.md."""
from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd

from src.source.gdb_source import query_df

SALES_TYPES = (1, 2, 3, 5)  # CSDTKTHBID — реальные продажи


def _ph(n: int) -> str:
    return ",".join(["?"] * n)


def get_products(product_ids: Sequence[int]) -> pd.DataFrame:
    """Справочник товаров: страх.запас (SQNT), единица, группа, текущий остаток считается отдельно."""
    if not product_ids:
        return pd.DataFrame()
    sql = f"""
        SELECT G.ID, G.NAME, G.CODE, G.BARCODE, G.OWNER AS GROUP_ID,
               GG.NAME AS GROUP_NAME, G.SQNT AS SAFETY_STOCK,
               G.ONE AS UNIT_NAME, G.ONEID AS UNIT_ID, G.NW AS NET_WEIGHT_KG
        FROM GOODS G
        LEFT JOIN GOODSGROUPS GG ON G.OWNER = GG.ID
        WHERE G.ID IN ({_ph(len(product_ids))})
    """
    return query_df(sql, list(product_ids))


def get_param_member_ids(param_id: int, fixval: int) -> pd.DataFrame:
    """ID товаров по параметру карточки (напр. Продукция=Кофе(кг): PARAMID=2, FIXVAL=3)."""
    sql = """
        SELECT G.ID, G.OWNER AS GROUP_ID, G.NAME
        FROM GDSPARAMGDSREF R
        JOIN GOODS G ON G.ID = R.GOODSID
        WHERE R.PARAMID = ? AND R.FIXVAL = ?
    """
    return query_df(sql, [param_id, fixval])


def get_group_member_ids(group_ids: Sequence[int]) -> pd.DataFrame:
    """ID товаров, входящих в группы (для агрегатов Coffee/Caotina)."""
    if not group_ids:
        return pd.DataFrame(columns=["ID", "GROUP_ID", "NAME"])
    sql = f"""
        SELECT G.ID, G.OWNER AS GROUP_ID, G.NAME
        FROM GOODS G
        WHERE G.OWNER IN ({_ph(len(group_ids))})
    """
    return query_df(sql, list(group_ids))


def get_sales_movements(product_ids: Sequence[int]) -> pd.DataFrame:
    """Розничные продажи по строкам чеков (для графика «продажи»).

    qty = COALESCE(NULLIF(RSQUANT,0), SOURCE, 0); фильтр CSDTKTHBID IN (1,2,3,5).
    """
    if not product_ids:
        return pd.DataFrame(columns=["SALE_DATE", "PRODUCT_ID", "QTY", "PRICE"])
    sql = f"""
        SELECT D.DAT_ AS SALE_DATE,
               GD.GODSID AS PRODUCT_ID,
               COALESCE(NULLIF(GD.RSQUANT, 0), GD.SOURCE, 0) AS QTY,
               GD.PRICE AS PRICE
        FROM STORZAKAZDT D
        JOIN STORZDTGDS GD ON D.ID = GD.SZID
        WHERE GD.GODSID IN ({_ph(len(product_ids))})
          AND D.CSDTKTHBID IN ({_ph(len(SALES_TYPES))})
    """
    return query_df(sql, list(product_ids) + list(SALES_TYPES))


def get_stock_movements(product_ids: Sequence[int]) -> pd.DataFrame:
    """Все движения товара из GDDKT с датой шапки DGVKT.DAT_.

    Остаток = нарастающая сумма QUANT по дате (проверено: точность ~99.76%).
    QUANT знаковый: приход +, расход -.
    """
    if not product_ids:
        return pd.DataFrame(columns=["MOVE_DATE", "PRODUCT_ID", "QUANT", "PRICE"])
    sql = f"""
        SELECT H.DAT_ AS MOVE_DATE,
               K.GDSKEY AS PRODUCT_ID,
               K.QUANT AS QUANT,
               K.PRICE AS PRICE
        FROM GDDKT K
        JOIN DGVKT H ON K.DGVKEY = H.ID
        WHERE K.GDSKEY IN ({_ph(len(product_ids))})
          AND K.QUANT IS NOT NULL
    """
    return query_df(sql, list(product_ids))


def weighted_purchase_price_gel(movements: pd.DataFrame) -> float | None:
    """Средневзвешенная закупочная цена по приходам GDDKT (QUANT > 0), GEL."""
    if movements.empty or "QUANT" not in movements.columns:
        return None
    inflows = movements[pd.to_numeric(movements["QUANT"], errors="coerce").fillna(0) > 0].copy()
    if inflows.empty:
        return None
    qty = pd.to_numeric(inflows["QUANT"], errors="coerce").fillna(0)
    price = pd.to_numeric(inflows["PRICE"], errors="coerce").fillna(0)
    total_q = float(qty.sum())
    if total_q <= 0:
        return None
    return round(float((qty * price).sum() / total_q), 4)


def resolve_our_orgn_id() -> int:
    """OURORGNID from STORLIST or SETTINGS."""
    from src.config import SETTINGS

    if SETTINGS.our_orgn_id is not None:
        return SETTINGS.our_orgn_id
    df = query_df("SELECT FIRST 1 OURORGNID FROM STORLIST ORDER BY ID", [])
    if df.empty:
        raise RuntimeError("OURORGNID not found; set OURORGNID in .env")
    return int(df.iloc[0, 0])


def get_report_stock_qend(
    goods_id: int,
    as_of: date,
    *,
    orgn_id: int | None = None,
    user_id: int | None = None,
    require_user_group: bool = False,
) -> float:
    """Granit report stock: Sum(QEND) from GddDt_MoveGoodsAll on as_of."""
    from datetime import date as date_type
    from src.config import SETTINGS

    if not isinstance(as_of, date_type):
        raise TypeError("as_of must be datetime.date")
    oid = orgn_id if orgn_id is not None else resolve_our_orgn_id()
    uid = user_id if user_id is not None else SETTINGS.stock_report_user_id
    edate = as_of.isoformat()
    if require_user_group:
        sql = (
            "SELECT COALESCE(SUM(P.QEND), 0) AS QUANT "
            "FROM GddDt_MoveGoodsAll(?, CAST(? AS DATE), CAST(? AS DATE)) P "
            "JOIN GOODS G ON G.ID = P.GID "
            "JOIN GOODS GG ON GG.ID = G.OWNER "
            "JOIN USERGGRP UG ON UG.GGRPID = GG.ID AND UG.USERID = ? "
            "WHERE P.GID = ?"
        )
        params = [oid, edate, edate, uid, goods_id]
    else:
        sql = (
            "SELECT COALESCE(SUM(P.QEND), 0) AS QUANT "
            "FROM GddDt_MoveGoodsAll(?, CAST(? AS DATE), CAST(? AS DATE)) P "
            "WHERE P.GID = ?"
        )
        params = [oid, edate, edate, goods_id]
    df = query_df(sql, params)
    if df.empty:
        return 0.0
    val = df.iloc[0, 0]
    return 0.0 if val is None else float(val)
