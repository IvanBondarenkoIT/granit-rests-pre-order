"""CLI: сверка формул остатка с orientation-benchmark."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from src.analysis.stock_balance import FORMULA_LABELS, load_benchmark, reconcile_benchmark


def main() -> None:
    p = argparse.ArgumentParser(description="Сверка остатков local .GDB с benchmark JSON")
    p.add_argument("--benchmark", type=Path, default=Path("benchmarks/stock_report_2024-06-25.json"))
    p.add_argument("--group", type=str, default=None, help="Фильтр по ключу группы в JSON")
    p.add_argument("--use-as-of", action="store_true", help="Применять as_of из JSON к формулам (иначе текущий леджер)")
    p.add_argument("--cutoff", type=str, default=None, help="Дата отсечения для ledger_before_cutoff (YYYY-MM-DD)")
    p.add_argument("--report-date", type=str, default=None, help="EDATE для report_qend (YYYY-MM-DD); по умолчанию as_of из JSON или сегодня")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    as_of, items = load_benchmark(args.benchmark)
    if args.group:
        items = [i for i in items if i.group_key == args.group]
    if not items:
        print("Нет позиций для сверки")
        return

    from datetime import date as date_cls
    from src.analysis.stock_balance import _parse_as_of as parse_date

    report_date = parse_date(args.report_date) if args.report_date else (as_of if args.use_as_of else date_cls.today())
    effective_as_of = as_of if args.use_as_of else None
    formula_as_of = report_date if report_date is not None else effective_as_of
    cutoff = None
    if args.cutoff:
        from src.analysis.stock_balance import _parse_as_of
        cutoff = _parse_as_of(args.cutoff)
    df = reconcile_benchmark(items, as_of=formula_as_of, cutoff=cutoff)
    cols = ["group", "goods_id", "name", "benchmark", "best_formula", "best_value", "delta", "abs_delta"]
    if args.verbose:
        for fid in FORMULA_LABELS:
            if fid in df.columns:
                cols.append(fid)
    print(f"benchmark_as_of={as_of} report_date={report_date} formulas_as_of={formula_as_of} cutoff={cutoff}")
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
