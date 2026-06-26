# Granit Rests Pre-Order

Система контроля остатков и предзаказов критических расходников.

**Репозиторий:** [github.com/IvanBondarenkoIT/granit-rests-pre-order](https://github.com/IvanBondarenkoIT/granit-rests-pre-order)

## Что делает
- ETL из локальной `GEORGIA.GDB` → недельные ряды в SQLite.
- Прогноз исчерпания, ROP, дата заказа, многотоварный план.
- **GUI (Flask, mobile-first):** Обзор · Товар · Заказ; графики Chart.js.

## Архитектура
```
src/
  web/           # Flask: templates + Chart.js
  etl/           # weekly_sales, weekly_stock (+ on_hand), weekly_demand
  analysis/      # рекомендации, прогноз
  source/        # Firebird read-only
  storage/       # SQLAlchemy
design/stitch/   # HTML-референсы
```

## Ключевые метрики остатка
- **`current_stock`** — леджер GDDKT (KPI, прогноз «сейчас»).
- **`on_hand`** — симуляция для графика: приход − продажи по неделям, якорь на `current_stock`.

## Установка
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

## Запуск
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m src.etl.run_etl
.\.venv\Scripts\python.exe -m src.analysis.recommend
.\.venv\Scripts\python.exe -m src.web.app
```

Откройте http://localhost:5000

## Тесты
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests -q
```

См. `docs/TESTING.md`.
