"""CLI: обход RDB$DESCRIPTION и поиск кандидатов остатков."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from src.analysis.stock_metadata import scan_metadata, write_scan_outputs


def main() -> None:
    p = argparse.ArgumentParser(description="Скан метаданных Firebird по русским описаниям")
    p.add_argument("--probe-counts", action="store_true", help="SELECT COUNT(*) для таблиц-кандидатов")
    p.add_argument("--json", type=Path, default=Path("data/stock_metadata_scan.json"))
    p.add_argument("--md", type=Path, default=Path("docs/STOCK_METADATA_CANDIDATES.md"))
    args = p.parse_args()

    scan = scan_metadata(probe_counts=args.probe_counts)
    write_scan_outputs(scan, json_path=args.json, md_path=args.md)
    print(f"relations={scan['counts']['relations']} procedures={scan['counts']['procedures']} stock_tables={scan['counts']['stock_field_tables']}")
    print(f"JSON: {args.json}")
    print(f"MD:   {args.md}")


if __name__ == "__main__":
    main()
