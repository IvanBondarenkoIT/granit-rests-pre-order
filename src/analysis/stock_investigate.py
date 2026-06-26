"""Детальный разбор движений GDDKT для калибровки остатков."""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.source.gdb_source import query_df


def movement_detail(goods_id: int) -> pd.DataFrame:
    """Все строки GDDKT с ненулевым QUANT и полями шапки DGVKT."""
    return query_df(
        """
        SELECT k.ID AS GDDKT_ID,
               k.QUANT,
               k.PRICE,
               h.ID AS DGVKT_ID,
               h.DAT_ AS MOVE_DATE,
               h.TYP,
               h.STORID,
               h.CSDTKTHBID,
               h.COMMENT
        FROM GDDKT k
        JOIN DGVKT h ON k.DGVKEY = h.ID
        WHERE k.GDSKEY = ?
          AND k.QUANT IS NOT NULL
          AND k.QUANT <> 0
        ORDER BY h.DAT_, k.ID
        """,
        [goods_id],
    )


def movement_summary(goods_id: int) -> dict[str, Any]:
    """Сводка по движениям: леджер, разбивка TYP, срезы по датам."""
    df = movement_detail(goods_id)
    ledger = float(df["QUANT"].sum()) if not df.empty else 0.0
    typ = (
        df.groupby("TYP", dropna=False)["QUANT"].sum().to_dict()
        if not df.empty
        else {}
    )
    by_date: list[dict[str, Any]] = []
    if not df.empty:
        for move_date, grp in df.groupby("MOVE_DATE"):
            by_date.append({
                "date": str(move_date)[:10],
                "quant": float(grp["QUANT"].sum()),
                "docs": [int(x) for x in grp["DGVKT_ID"].tolist()],
            })
    cutoffs: dict[str, float] = {}
    if not df.empty:
        for label, cut in [
            ("before_2026_06_23", date(2026, 6, 23)),
            ("before_2026_06_25", date(2026, 6, 25)),
        ]:
            mask = pd.to_datetime(df["MOVE_DATE"]).dt.date < cut
            cutoffs[label] = float(df.loc[mask, "QUANT"].sum())
    return {
        "goods_id": goods_id,
        "ledger_all": ledger,
        "nonzero_rows": len(df),
        "by_typ": typ,
        "by_date": by_date,
        "cutoffs": cutoffs,
    }


def gddktqnt_by_stor(goods_id: int) -> pd.DataFrame:
    """Остаток по складам через связку GDDKTQNT (если есть строки)."""
    return query_df(
        """
        SELECT gq.STOR, SUM(g.QUANT) AS QUANT, COUNT(*) AS LINE_COUNT
        FROM GDDKTQNT gq
        JOIN GDDKT g ON g.ID = gq.ID
        WHERE g.GDSKEY = ?
        GROUP BY gq.STOR
        ORDER BY 3 DESC
        """,
        [goods_id],
    )
