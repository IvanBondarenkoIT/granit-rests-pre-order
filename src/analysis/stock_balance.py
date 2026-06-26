"""Кандидаты формул остатка и сверка с orientation-benchmark."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.source.gdb_source import query_df

FORMULA_LABELS: dict[str, str] = {
    "ledger_all": "SUM(GDDKT.QUANT) — текущий леджер",
    "ledger_price_filter": "SUM(GDDKT.QUANT) WHERE PRICE>0",
    "ledger_in_out": "SUM(GDDKT) − SUM(GDDDT)",
    "ledger_typ0": "SUM(GDDKT) JOIN DGVKT TYP=0",
    "ledger_typ1": "SUM(GDDKT) JOIN DGVKT TYP=1",
    "ledger_stor_null": "SUM(GDDKT) JOIN DGVKT STORID IS NULL",
    "ledger_stor_141": "SUM(GDDKT) JOIN DGVKT STORID=141",
    "ledger_as_of": "SUM(GDDKT) на дату as_of",
    "ledger_as_of_price": "ledger_as_of + PRICE>0",
    "ledger_in_out_as_of": "(GDDKT−GDDDT) на дату as_of",
    "ledger_before_cutoff": "SUM(GDDKT) только MOVE_DATE < cutoff",
    "goods_qnt": "GOODS.QNT из карточки",
    "report_qend": "GddDt_MoveGoodsAll → Sum(QEND) на as_of",
    "report_qend_usergrp": "report_qend + фильтр UserGGrp",
}


@dataclass(frozen=True)
class BenchmarkItem:
    goods_id: int | None
    name: str
    article: str | None
    qty: float
    group_key: str


def _parse_as_of(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def load_benchmark(path: Path) -> tuple[date | None, list[BenchmarkItem]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    as_of = _parse_as_of(raw.get("as_of"))
    items: list[BenchmarkItem] = []
    groups: dict[str, Any] = raw.get("groups") or {}
    for group_key, group in groups.items():
        gname = str(group.get("name") or group_key)
        for gid, payload in (group.get("items_by_id") or {}).items():
            if isinstance(payload, dict):
                items.append(BenchmarkItem(int(gid), str(payload.get("name") or gid), payload.get("article"), float(payload["qty"]), group_key))
            else:
                items.append(BenchmarkItem(int(gid), gname, None, float(payload), group_key))
        for article, payload in (group.get("items_by_article") or {}).items():
            if isinstance(payload, dict):
                gid = int(payload["goods_id"]) if payload.get("goods_id") else None
                items.append(BenchmarkItem(gid, str(payload.get("name") or article), str(article), float(payload["qty"]), group_key))
            else:
                items.append(BenchmarkItem(None, gname, str(article), float(payload), group_key))
        for name_part, qty in (group.get("items_by_name") or {}).items():
            items.append(BenchmarkItem(None, str(name_part), None, float(qty), group_key))
    return as_of, items


def resolve_goods_id(item: BenchmarkItem) -> int | None:
    if item.goods_id is not None:
        return item.goods_id
    if item.article:
        df = query_df(
            "SELECT FIRST 1 ID FROM GOODS WHERE TRIM(CODE) = ? OR TRIM(BARCODE) = ? OR UPPER(NAME) CONTAINING ? ORDER BY ID",
            [item.article.strip(), item.article.strip(), item.article.strip().upper()],
        )
        if not df.empty:
            return int(df.iloc[0, 0])
    if item.name:
        df = query_df("SELECT FIRST 1 ID FROM GOODS WHERE UPPER(NAME) CONTAINING ? ORDER BY ID", [item.name.strip().upper()])
        if not df.empty:
            return int(df.iloc[0, 0])
    return None


def _scalar(sql: str, params: list[Any]) -> float:
    df = query_df(sql, params)
    if df.empty:
        return 0.0
    val = df.iloc[0, 0]
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    return float(val)


def _gddkt_sum(
    goods_id: int,
    *,
    as_of: date | None = None,
    before: date | None = None,
    price_positive: bool = False,
    typ: int | None = None,
    stor_null: bool = False,
    stor_id: int | None = None,
) -> float:
    clauses = ["K.GDSKEY = ?", "K.QUANT IS NOT NULL"]
    params: list[Any] = [goods_id]
    if price_positive:
        clauses.append("K.PRICE IS NOT NULL AND K.PRICE > 0")
    if as_of is not None:
        clauses.append("H.DAT_ <= ?")
        params.append(as_of)
    if before is not None:
        clauses.append("H.DAT_ < ?")
        params.append(before)
    if typ is not None:
        clauses.append("H.TYP = ?")
        params.append(typ)
    if stor_null:
        clauses.append("H.STORID IS NULL")
    if stor_id is not None:
        clauses.append("H.STORID = ?")
        params.append(stor_id)
    sql = f"SELECT COALESCE(SUM(K.QUANT), 0) FROM GDDKT K JOIN DGVKT H ON K.DGVKEY = H.ID WHERE {' AND '.join(clauses)}"
    return _scalar(sql, params)


def _gdddt_sum(goods_id: int, *, as_of: date | None = None) -> float:
    clauses = ["G.GDSKEY = ?", "G.QUANT IS NOT NULL"]
    params: list[Any] = [goods_id]
    if as_of is not None:
        clauses.append("H.DAT_ <= ?")
        params.append(as_of)
    sql = f"SELECT COALESCE(SUM(G.QUANT), 0) FROM GDDDT G JOIN DGVDT H ON G.DGVKEY = H.ID WHERE {' AND '.join(clauses)}"
    return _scalar(sql, params)


def _goods_qnt(goods_id: int) -> float:
    return _scalar("SELECT COALESCE(QNT, 0) FROM GOODS WHERE ID = ?", [goods_id])



def _report_qend(goods_id: int, as_of: date, *, require_user_group: bool = False) -> float:
    from src.source.queries import get_report_stock_qend

    return get_report_stock_qend(goods_id, as_of, require_user_group=require_user_group)

def compute_formula(
    goods_id: int,
    formula_id: str,
    *,
    as_of: date | None = None,
    cutoff: date | None = None,
) -> float:
    if formula_id == "ledger_all":
        return _gddkt_sum(goods_id)
    if formula_id == "ledger_price_filter":
        return _gddkt_sum(goods_id, price_positive=True)
    if formula_id == "ledger_in_out":
        return _gddkt_sum(goods_id) - _gdddt_sum(goods_id)
    if formula_id == "ledger_typ0":
        return _gddkt_sum(goods_id, typ=0)
    if formula_id == "ledger_typ1":
        return _gddkt_sum(goods_id, typ=1)
    if formula_id == "ledger_stor_null":
        return _gddkt_sum(goods_id, stor_null=True)
    if formula_id == "ledger_stor_141":
        return _gddkt_sum(goods_id, stor_id=141)
    if formula_id == "ledger_as_of":
        if as_of is None:
            raise ValueError("ledger_as_of requires as_of")
        return _gddkt_sum(goods_id, as_of=as_of)
    if formula_id == "ledger_as_of_price":
        if as_of is None:
            raise ValueError("ledger_as_of_price requires as_of")
        return _gddkt_sum(goods_id, as_of=as_of, price_positive=True)
    if formula_id == "ledger_in_out_as_of":
        if as_of is None:
            raise ValueError("ledger_in_out_as_of requires as_of")
        return _gddkt_sum(goods_id, as_of=as_of) - _gdddt_sum(goods_id, as_of=as_of)
    if formula_id == "ledger_before_cutoff":
        if cutoff is None:
            raise ValueError("ledger_before_cutoff requires cutoff")
        return _gddkt_sum(goods_id, before=cutoff)
    if formula_id == "goods_qnt":
        return _goods_qnt(goods_id)
    if formula_id == "report_qend":
        if as_of is None:
            raise ValueError("report_qend requires as_of")
        return _report_qend(goods_id, as_of, require_user_group=False)
    if formula_id == "report_qend_usergrp":
        if as_of is None:
            raise ValueError("report_qend_usergrp requires as_of")
        return _report_qend(goods_id, as_of, require_user_group=True)
    raise KeyError(f"Unknown formula: {formula_id}")


def default_formulas(*, as_of: date | None, cutoff: date | None = None) -> list[str]:
    base = ["ledger_all", "ledger_price_filter", "ledger_in_out", "ledger_typ0", "ledger_typ1",
            "ledger_stor_null", "ledger_stor_141", "goods_qnt"]
    if as_of is not None:
        base.extend(["ledger_as_of", "ledger_as_of_price", "ledger_in_out_as_of", "report_qend", "report_qend_usergrp"])
    if cutoff is not None:
        base.append("ledger_before_cutoff")
    return base


def reconcile_benchmark(
    items: list[BenchmarkItem],
    *,
    as_of: date | None = None,
    cutoff: date | None = None,
    formulas: list[str] | None = None,
) -> pd.DataFrame:
    formula_ids = formulas or default_formulas(as_of=as_of, cutoff=cutoff)
    rows: list[dict[str, Any]] = []
    for item in items:
        goods_id = resolve_goods_id(item)
        row: dict[str, Any] = {"group": item.group_key, "goods_id": goods_id, "name": item.name,
                               "article": item.article, "benchmark": item.qty}
        if goods_id is None:
            row.update({"best_formula": None, "best_value": None, "delta": None, "abs_delta": None})
            rows.append(row)
            continue
        best_formula: str | None = None
        best_value: float | None = None
        best_abs = float("inf")
        for fid in formula_ids:
            try:
                val = compute_formula(goods_id, fid, as_of=as_of, cutoff=cutoff)
            except (ValueError, KeyError):
                continue
            row[fid] = round(val, 4)
            ad = abs(val - item.qty)
            if ad < best_abs:
                best_abs = ad
                best_formula = fid
                best_value = val
        row["best_formula"] = best_formula
        row["best_value"] = best_value
        row["delta"] = None if best_value is None else round(best_value - item.qty, 4)
        row["abs_delta"] = None if best_value is None else round(best_abs, 4)
        rows.append(row)
    return pd.DataFrame(rows)


def probe_stock_tables(limit: int = 30) -> pd.DataFrame:
    from src.analysis.stock_metadata import decode_description, scan_metadata

    scan = scan_metadata(probe_counts=False)
    rows: list[dict[str, Any]] = []
    for tbl in scan["stock_field_tables"][:limit]:
        cols_df = query_df(
            "SELECT TRIM(rf.RDB$FIELD_NAME) AS COL FROM RDB$RELATION_FIELDS rf WHERE rf.RDB$RELATION_NAME = ? ORDER BY rf.RDB$FIELD_POSITION",
            [tbl],
        )
        cols = [str(c).strip() for c in cols_df["COL"]]
        desc_df = query_df("SELECT r.RDB$DESCRIPTION AS D FROM RDB$RELATIONS r WHERE r.RDB$RELATION_NAME = ?", [tbl])
        descr = decode_description(desc_df.iloc[0, 0]) if not desc_df.empty else ""
        cnt = None
        try:
            cnt = int(query_df(f"SELECT COUNT(*) FROM {tbl}").iloc[0, 0])
        except Exception:
            pass
        rows.append({"table": tbl, "columns": ", ".join(cols[:12]), "row_count": cnt, "description": descr[:120]})
    return pd.DataFrame(rows)

