"""Тесты загрузки benchmark и выбора формул (без БД)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.analysis.stock_balance import (
    BenchmarkItem,
    _parse_as_of,
    default_formulas,
    load_benchmark,
)


def test_parse_as_of():
    assert _parse_as_of("2024-06-25") == date(2024, 6, 25)
    assert _parse_as_of(None) is None


def test_load_benchmark_orientation(tmp_path: Path):
    payload = {
        "as_of": "2024-06-25",
        "groups": {
            "26761": {
                "name": "Cleaning",
                "items_by_article": {
                    "5513292811": {"name": "DLSC002", "qty": 1105, "goods_id": 24227}
                },
            }
        },
    }
    path = tmp_path / "bench.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    as_of, items = load_benchmark(path)
    assert as_of == date(2024, 6, 25)
    assert len(items) == 1
    assert items[0].goods_id == 24227
    assert items[0].qty == 1105.0


def test_default_formulas_includes_as_of():
    assert "ledger_as_of" in default_formulas(as_of=date(2024, 6, 25))
    assert "ledger_as_of" not in default_formulas(as_of=None)


def test_default_formulas_includes_cutoff():
    assert "ledger_before_cutoff" in default_formulas(as_of=None, cutoff=date(2026, 6, 23))
    assert "ledger_before_cutoff" not in default_formulas(as_of=None, cutoff=None)


def test_default_formulas_includes_report_qend():
    formulas = default_formulas(as_of=date(2026, 6, 25))
    assert "report_qend" in formulas
    assert "report_qend_usergrp" in formulas
