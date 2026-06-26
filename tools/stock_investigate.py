"""CLI: детальный разбор движений товара для калибровки остатков."""
from __future__ import annotations

import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.analysis.stock_investigate import gddktqnt_by_stor, movement_detail, movement_summary


def main() -> None:
    p = argparse.ArgumentParser(description="Разбор движений GDDKT для GOODS.ID")
    p.add_argument("goods_id", type=int, help="GOODS.ID (напр. 24227 для DLSC002)")
    p.add_argument("--benchmark", type=float, default=None, help="Эталонное кол-во из отчёта")
    p.add_argument("--json", action="store_true", help="Вывод summary в JSON")
    args = p.parse_args()

    summary = movement_summary(args.goods_id)
    if args.benchmark is not None:
        summary["benchmark"] = args.benchmark
        summary["delta"] = round(summary["ledger_all"] - args.benchmark, 4)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"GOODS.ID={args.goods_id}")
        print(f"ledger_all={summary['ledger_all']} nonzero_rows={summary['nonzero_rows']}")
        if args.benchmark is not None:
            print(f"benchmark={args.benchmark} delta={summary['delta']}")
        print("by_typ:", summary["by_typ"])
        for c in summary["cutoffs"]:
            d = summary["cutoffs"][c]
            extra = ""
            if args.benchmark is not None:
                extra = f" (Δ к отчёту: {d - args.benchmark:+.1f})"
            print(f"  {c}: {d}{extra}")
        print("\nДвижения (QUANT <> 0):")
        print(movement_detail(args.goods_id).to_string(index=False))
        stor = gddktqnt_by_stor(args.goods_id)
        if not stor.empty:
            print("\nGDDKTQNT по складам:")
            print(stor.to_string(index=False))


if __name__ == "__main__":
    main()
