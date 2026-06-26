# Roadmap — granit-rests-pre-order

## Сделано (v1)
- [x] **Этап 0.** Фундамент: `AGENTS.md`, `requirements.txt`, `.gitignore`, `.env(.example)`,
      структура `src/`, `config.py`.
- [x] **Этап 1.** Разведка БД: `SQNT` = страховой запас, остаток = нараст. сумма `GDDKT.QUANT`
      по `DGVKT.DAT_`, расход — из `STORZAKAZDT`. См. `docs/DB_SCHEMA.md`.
- [x] **Этап 2.** DAL: `source/` (FB embedded + SQL), `storage/` (SQLAlchemy PG/SQLite + DDL), ETL.
- [x] **Этап 3.** Отбор: курируемый список `critical_products.py` (16 позиций, агрегаты раскрыты).
- [x] **Этап 4.** История: `weekly_sales`, `weekly_stock` по ISO-неделям.
- [x] **Этап 4.5.** Сигнал спроса: `weekly_demand` (true_demand = продажи; каркас unconstraining).
- [x] **Этап 5.** Аналитика: классификация (ADI/CV²), прогноз с сезонностью, страховой запас
      (с потолком), ROP, дата исчерпания/заказа, объём.
- [x] **Этап 5.5.** Многотоварное пополнение: общий горизонт покрытия (`multi_item_plan`).
- [x] **Этап 6.** GUI (Streamlit + Plotly): хронология, сезонность, прогноз остатка, сводка.
- [x] **Этап 7.** Валидация на `DLSC002` + юнит-тесты расчётов.

## Дальше (калибровка/уточнения)
- [x] **DLSC500** — `GOODS.ID=22284`, `AS00006183`, descaling 500ml (2026-06-25).
- [x] Coffee: отбор по параметру «Продукция»=«Кофе(кг)» (`FIXVAL=3`), агрегат одной строкой.
- [x] **G3 MOQ:** без округления; расчётное qty как есть; упаковку — вручную при заказе.
- [x] **A1:** «Страх.остаток 300/0/3» → рабочее число = `GOODS.SQNT` (300).
- [x] **Расходники (inflow):** Bag paper, Cup 12/8/4 oz, Sugar — спрос по приходам GDDKT (`demand_source=inflow`).
- [ ] Точный исторический on-hand → censored demand.
- [ ] PostgreSQL, Proxy API инкремент.
- [ ] **Этап 8 — UI Stitch (mobile-first)** — gate: `docs/TESTING.md`
  - [x] **8.0** Git baseline + `design/stitch/`
  - [x] **8.1** Тема (`theme.py`, `stitch.css`) + multipage
  - [x] **8.2** Экран «Обзор» (KPI, фильтры, карточки срочности)
  - [x] **8.3** Экран «Товар» (метрики, кривая исчерпания, рекомендация)
  - [x] **8.4** График сезонности (годы + средняя + остаток)
  - [x] **8.5** Экран «Заказ» + `unit_purchase_price_gel` (сумма в ₾)
- [x] **Этап 9 — Flask UI (концепт A)** — замена Streamlit
  - [x] `on_hand` в ETL (приход − продажи, якорь на current_stock)
  - [x] Flask: Обзор / Товар / Заказ, Chart.js, нижняя навигация
