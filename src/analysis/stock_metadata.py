"""Разведка метаданных Firebird: русские описания в RDB$DESCRIPTION (WIN1251)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.source.gdb_source import query_df

KEYWORDS: tuple[str, ...] = (
    "остат", "склад", "движен", "парт", "баланс", "запас", "колич",
    "приход", "расход", "налич", "товар", "gdd", "stor", "goods", "qnt", "quant",
)

_RELATIONS_SQL = """
    SELECT TRIM(r.RDB$RELATION_NAME) AS NAME,
           r.RDB$DESCRIPTION AS DESCR,
           r.RDB$VIEW_BLR AS VIEW_BLR
    FROM RDB$RELATIONS r
    WHERE r.RDB$SYSTEM_FLAG = 0
      AND r.RDB$DESCRIPTION IS NOT NULL
"""

_FIELDS_SQL = """
    SELECT TRIM(rf.RDB$RELATION_NAME) AS TBL,
           TRIM(rf.RDB$FIELD_NAME) AS COL,
           rf.RDB$DESCRIPTION AS DESCR
    FROM RDB$RELATION_FIELDS rf
    WHERE rf.RDB$SYSTEM_FLAG = 0
      AND rf.RDB$DESCRIPTION IS NOT NULL
"""

_PROCEDURES_SQL = """
    SELECT TRIM(p.RDB$PROCEDURE_NAME) AS NAME,
           p.RDB$DESCRIPTION AS DESCR
    FROM RDB$PROCEDURES p
    WHERE p.RDB$SYSTEM_FLAG = 0
      AND p.RDB$DESCRIPTION IS NOT NULL
"""

_STOCK_FIELD_TABLES_SQL = """
    SELECT DISTINCT TRIM(rf.RDB$RELATION_NAME) AS TBL
    FROM RDB$RELATION_FIELDS rf
    WHERE rf.RDB$SYSTEM_FLAG = 0
      AND (
            UPPER(TRIM(rf.RDB$FIELD_NAME)) IN ('GDSKEY', 'GODSID', 'GOODSID')
         OR UPPER(TRIM(rf.RDB$FIELD_NAME)) IN ('QUANT', 'QNT', 'BQUANT', 'RSQUANT', 'SOURCE')
      )
    ORDER BY 1
"""


def decode_description(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return value.decode("cp1251", errors="replace").strip()
    return str(value).strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def matches_keywords(text: str, name: str = "") -> bool:
    hay = f"{name} {_normalize(text)}".lower()
    return any(k in hay for k in KEYWORDS)


def _probe_row_count(table_name: str) -> int | None:
    safe = table_name.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_$]+", safe):
        return None
    try:
        df = query_df(f"SELECT COUNT(*) AS CNT FROM {safe}")
        return int(df.iloc[0, 0])
    except Exception:
        return None


def scan_metadata(*, probe_counts: bool = False) -> dict[str, Any]:
    relations_raw = query_df(_RELATIONS_SQL)
    fields_raw = query_df(_FIELDS_SQL)
    procedures_raw = query_df(_PROCEDURES_SQL)

    relations: list[dict[str, Any]] = []
    for _, row in relations_raw.iterrows():
        name = str(row["NAME"]).strip()
        descr = decode_description(row["DESCR"])
        if not matches_keywords(descr, name):
            continue
        kind = "view" if row["VIEW_BLR"] is not None else "table"
        entry: dict[str, Any] = {"kind": kind, "name": name, "description": _normalize(descr)}
        if probe_counts and kind == "table":
            entry["row_count"] = _probe_row_count(name)
        relations.append(entry)

    fields: list[dict[str, Any]] = []
    for _, row in fields_raw.iterrows():
        tbl = str(row["TBL"]).strip()
        col = str(row["COL"]).strip()
        descr = decode_description(row["DESCR"])
        if not matches_keywords(descr, f"{tbl}.{col}"):
            continue
        fields.append({"table": tbl, "column": col, "description": _normalize(descr)})

    procedures: list[dict[str, Any]] = []
    for _, row in procedures_raw.iterrows():
        name = str(row["NAME"]).strip()
        descr = decode_description(row["DESCR"])
        if not matches_keywords(descr, name):
            continue
        procedures.append({"name": name, "description": _normalize(descr)})

    stock_field_tables = [str(v).strip() for v in query_df(_STOCK_FIELD_TABLES_SQL)["TBL"]]

    return {
        "keywords": list(KEYWORDS),
        "relations": sorted(relations, key=lambda x: x["name"]),
        "fields": sorted(fields, key=lambda x: (x["table"], x["column"])),
        "procedures": sorted(procedures, key=lambda x: x["name"]),
        "stock_field_tables": stock_field_tables,
        "counts": {
            "relations": len(relations),
            "fields": len(fields),
            "procedures": len(procedures),
            "stock_field_tables": len(stock_field_tables),
        },
    }


def render_markdown(scan: dict[str, Any]) -> str:
    lines = [
        "# Кандидаты таблиц/процедур по RDB$DESCRIPTION",
        "",
        f"- Таблиц/представлений: **{scan['counts']['relations']}**",
        f"- Полей: **{scan['counts']['fields']}**",
        f"- Процедур: **{scan['counts']['procedures']}**",
        f"- Таблиц с GDSKEY/QUANT/QNT: **{scan['counts']['stock_field_tables']}**",
        "",
        "## Приоритетные таблицы (остат / склад / движен)",
        "",
    ]
    priority = ("остат", "склад", "движен", "приход", "расход")
    for rel in scan["relations"]:
        if not any(p in rel["description"].lower() for p in priority):
            continue
        rc = rel.get("row_count")
        rc_s = f", rows={rc}" if rc is not None else ""
        lines.append(f"- **{rel['name']}** ({rel['kind']}{rc_s}): {rel['description']}")

    lines.extend(["", "## Процедуры (остат / движен)", ""])
    for proc in scan["procedures"]:
        if "остат" not in proc["description"].lower() and "движен" not in proc["description"].lower():
            continue
        lines.append(f"- **{proc['name']}**: {proc['description'][:200]}")

    lines.extend(["", "## Таблицы с полями товара/количества", ""])
    for tbl in scan["stock_field_tables"][:40]:
        lines.append(f"- `{tbl}`")
    if len(scan["stock_field_tables"]) > 40:
        lines.append(f"- … ещё {len(scan['stock_field_tables']) - 40}")

    return "\n".join(lines) + "\n"


def write_scan_outputs(scan: dict[str, Any], *, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(scan), encoding="utf-8")
