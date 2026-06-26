"""Извлечение шаблонов FastReport из таблицы FRREPORT (локальная .GDB)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from src.source.gdb_source import connect


def _decode_template(blob: bytes | None) -> str:
    if not blob:
        return ""
    for enc in ("utf-8", "cp1251", "latin1"):
        try:
            return blob.decode(enc, errors="replace")
        except Exception:
            continue
    return ""


def list_reports() -> None:
    with connect() as con:
        cur = con.cursor()
        cur.execute("SELECT ID, PARENTID, NAME, TYP, FRVER FROM FRREPORT ORDER BY ID")
        rows = cur.fetchall()
    print(f"FRREPORT: {len(rows)} записей")
    for row in rows:
        print(f"  ID={row[0]}  NAME={row[2]!r}  TYP={row[3]}  FRVER={row[4]}")


def search_reports(keyword: str) -> list[tuple[int, str]]:
    kw = keyword.lower()
    hits: list[tuple[int, str]] = []
    with connect() as con:
        cur = con.cursor()
        cur.execute("SELECT ID, NAME, TEMPLATE FROM FRREPORT")
        for rid, name, template in cur.fetchall():
            name_s = (name or "").strip()
            text = _decode_template(template)
            if kw in name_s.lower() or kw in text.lower():
                hits.append((int(rid), name_s))
    return hits


def extract_report(report_id: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        cur = con.cursor()
        cur.execute("SELECT ID, NAME, TEMPLATE FROM FRREPORT WHERE ID = ?", [report_id])
        row = cur.fetchone()
        if not row:
            raise SystemExit(f"FRREPORT.ID={report_id} не найден")
        rid, name, template = row
        blob = template if isinstance(template, (bytes, bytearray)) else bytes(template or b"")
        safe = re.sub(r"[^\w\-]+", "_", (name or f"report_{rid}").strip())[:80]
        fr3_path = out_dir / f"{rid}_{safe}.fr3"
        fr3_path.write_bytes(blob)
        text = _decode_template(blob)
        txt_path = out_dir / f"{rid}_{safe}.txt"
        txt_path.write_text(text, encoding="utf-8", errors="replace")
        # вытащить фрагменты, похожие на SQL
        sql_hints = []
        for m in re.finditer(r"(SELECT[\s\S]{20,800}?)(?:</|\x00|$)", text, re.IGNORECASE):
            frag = m.group(1).strip()
            if "FROM" in frag.upper():
                sql_hints.append(frag)
        if sql_hints:
            sql_path = out_dir / f"{rid}_{safe}_sql_hints.txt"
            sql_path.write_text("\n\n---\n\n".join(sql_hints[:20]), encoding="utf-8")
            print(f"SQL hints: {sql_path}")
    print(f"Saved: {fr3_path} ({len(blob)} bytes)")
    print(f"Text:  {txt_path}")
    return fr3_path


def main() -> None:
    p = argparse.ArgumentParser(description="Извлечение FRREPORT из GEORGIA.GDB")
    p.add_argument("--list", action="store_true", help="Список отчётов в FRREPORT")
    p.add_argument("--search", type=str, default=None, help="Поиск по NAME/TEMPLATE (напр. остат, GDDKT)")
    p.add_argument("--id", type=int, default=None, help="ID отчёта для извлечения")
    p.add_argument("--out", type=Path, default=Path("data/frreport"))
    args = p.parse_args()

    if args.list:
        list_reports()
        return
    if args.search:
        hits = search_reports(args.search)
        if not hits:
            print(f"Ничего не найдено по «{args.search}»")
            print("В локальной копии может не быть полного набора отчётов — попробуйте GDB с сервера.")
            return
        for rid, name in hits:
            print(f"  ID={rid}  NAME={name!r}")
        return
    if args.id is not None:
        extract_report(args.id, args.out)
        return
    p.print_help()


if __name__ == "__main__":
    main()
