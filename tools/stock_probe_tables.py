"""CLI: таблицы с полями товара/количества."""
from __future__ import annotations

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.analysis.stock_balance import probe_stock_tables


def main() -> None:
    p = argparse.ArgumentParser(description="Пробы таблиц GDSKEY/QUANT на local .GDB")
    p.add_argument("--limit", type=int, default=40)
    args = p.parse_args()
    df = probe_stock_tables(limit=args.limit)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
