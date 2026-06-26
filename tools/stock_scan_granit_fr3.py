"""Поиск и извлечение SQL из шаблонов FastReport Granit (.frf / .fr3) в data/input/GRANIT."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_ROOT = Path("data/input/GRANIT/FrfStor")
DEFAULT_OUT = Path("data/frreport")

_SQL_MARKERS = (
    "select", " from ", "gdddt_", "gddkt", "userggrp", "movegoods", "qend",
    "остат", "налич", "доступн",
)


def _decode_blob(raw: bytes) -> str:
    for enc in ("cp1251", "utf-8", "latin1"):
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue
    return raw.decode("latin1", errors="ignore")


def _extract_sql_hints(text: str, limit: int = 12) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"(?is)(select[\s\S]{15,1200})", text):
        block = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\n", m.group(1)).strip()
        if " from " not in block.lower():
            continue
        key = block[:100].lower()
        if key in seen:
            continue
        seen.add(key)
        hints.append(block[:900])
        if len(hints) >= limit:
            break
    for m in re.finditer(r"(?is)(select[\s\S]{0,80}?gdddt_movegoods[a-z]*\([\s\S]{0,400})", text):
        block = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\n", m.group(1)).strip()
        key = block[:80].lower()
        if key not in seen:
            seen.add(key)
            hints.append(block[:900])
    return hints


def _iter_templates(root: Path) -> list[Path]:
    files: list[Path] = []
    for ext in ("*.frf", "*.fr3", "*.FRF", "*.FR3"):
        files.extend(root.rglob(ext))
    return sorted(set(files))


def list_templates(root: Path) -> None:
    files = _iter_templates(root)
    print(f"{root}: {len(files)} шаблонов (.frf/.fr3)")
    for path in files:
        print(f"  {path.relative_to(root)}")


def search_templates(root: Path, keyword: str) -> list[Path]:
    kw = keyword.lower()
    hits: list[Path] = []
    for path in _iter_templates(root):
        text = _decode_blob(path.read_bytes()).lower()
        if kw in path.name.lower() or kw in text or any(m in text for m in _SQL_MARKERS if m in kw):
            hits.append(path)
    return hits


def extract_template(path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = path.read_bytes()
    text = _decode_blob(raw)
    safe = re.sub(r"[^\w\-]+", "_", path.stem)[:80]
    bin_path = out_dir / f"{safe}{path.suffix.lower()}"
    bin_path.write_bytes(raw)
    txt_path = out_dir / f"{safe}.txt"
    txt_path.write_text(text, encoding="utf-8", errors="replace")
    hints = _extract_sql_hints(text)
    sql_path = out_dir / f"{safe}_sql.txt"
    sql_path.write_text("\n\n---\n\n".join(hints) if hints else "(SQL не найден)", encoding="utf-8")
    print(f"Saved: {bin_path}")
    print(f"Text:  {txt_path}")
    print(f"SQL:   {sql_path} ({len(hints)} блоков)")
    return sql_path


def find_by_name(root: Path, name_part: str) -> Path | None:
    needle = name_part.lower()
    for path in _iter_templates(root):
        if needle in path.name.lower():
            return path
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="Скан шаблонов Granit FrfStor (.frf/.fr3)")
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--list", action="store_true", help="Список всех шаблонов")
    p.add_argument("--search", type=str, default=None, help="Поиск по содержимому/имени")
    p.add_argument("--extract", type=str, default=None, help="Извлечь SQL (часть имени файла)")
    args = p.parse_args()
    root = args.root
    if not root.is_dir():
        raise SystemExit(f"Каталог не найден: {root}")
    if args.list:
        list_templates(root)
        return
    if args.search:
        hits = search_templates(root, args.search)
        if not hits:
            print(f"Ничего не найдено по «{args.search}»")
            return
        print(f"Найдено: {len(hits)}")
        for path in hits:
            print(f"  {path.relative_to(root)}")
        return
    if args.extract:
        path = find_by_name(root, args.extract)
        if path is None:
            raise SystemExit(f"Шаблон не найден: {args.extract!r}")
        extract_template(path, args.out)
        return
    p.print_help()


if __name__ == "__main__":
    main()
