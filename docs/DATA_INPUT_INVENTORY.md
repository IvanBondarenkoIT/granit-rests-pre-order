# Инвентарь `data/input/`

Локальные материалы для калибровки остатков (не в git — см. `.gitignore`).

## `data/input/db/`

| Файл | Описание |
|------|----------|
| `GEORGIA.GDB` | Копия Firebird 2.5 (~1.6 GB), ODS 11. Основной источник для `GDB_PATH`. |
| `ShopSeller.7z` | Кассовое ПО (.NET), не ERP. |
| `IBE/` | IBExpert + `PrintData.fr3` (вспомогательные инструменты). |

**`FRREPORT` в этой GDB:** 5 записей (накладные, КП) — **отчёта остатков нет**.

**`OURORGNID`:** `12978` (из `STORLIST`).

## `data/input/GRANIT/`

Полная копия клиента Granit ERP (Delphi / FastReport).

| Компонент | Назначение |
|-----------|------------|
| `Stor32.exe` | Модуль складского учёта; форма `GoodsFree` («Товар в наличии»). |
| `frvw32.exe` | Просмотр/редактирование шаблонов FastReport. |
| `accnstor.cnt` / `Accnstor.hlp` | Справка: «Склад: Товар в наличии» (`hc_StorGoodsFree`). |
| `FrfStor/` | **530 × `.frf`** + 4 × `.fr3` — шаблоны складских отчётов. |
| `FrfAccn/`, `FrfKass/` | Бухгалтерия, кassa. |
| `*.bpl` | Delphi-пакеты (`bpl_common.bpl` содержит `GoodsFree`, `GDDKT`). |

### Отчёт остатков (целевой)

```
FrfStor/Наличие товара/Остаток товара (по доступным группам).frf
```

SQL — в [`STOCK_REPORT_SQL.md`](STOCK_REPORT_SQL.md).

### Скан шаблонов

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe tools/stock_scan_granit_fr3.py --search остат
.\.venv\Scripts\python.exe tools/stock_scan_granit_fr3.py --extract "по доступным группам"
```

Промежуточный скан (55 отчётов): `data/frreport/_granit_frf_scan.txt`.

## Рекомендуемый `.env`

```env
GDB_PATH=data/input/db/GEORGIA.GDB
OURORGNID=12978
STOCK_REPORT_USER_ID=1
```
