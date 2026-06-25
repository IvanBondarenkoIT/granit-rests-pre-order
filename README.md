# Granit Rests Pre-Order

Система контроля остатков и предзаказов критических расходников: прогноз исчерпания запаса,
дата заказа и рекомендуемый объём с учётом сезонности и срока поставки.

**Репозиторий:** [github.com/IvanBondarenkoIT/granit-rests-pre-order](https://github.com/IvanBondarenkoIT/granit-rests-pre-order)

## Что делает
- Тянет историю из локальной копии боевой БД (Firebird 2.5, `GEORGIA.GDB`) офлайн.
- Строит недельные ряды **продаж** (спрос) и **остатков** (леджер `GDDKT`) по ISO-неделям.
- Классифицирует спрос (smooth / intermittent / erratic / lumpy), прогнозирует с сезонностью.
- Считает страховой запас (по уровню сервиса), точку заказа (ROP), дату исчерпания,
  дату заказа, рекомендуемый объём; даёт совместный (многотоварный) план пополнения.
- **GUI (Streamlit, mobile-first Stitch):** Обзор срочности, карточка товара с кривой исчерпания,
  сезонность, экран совместного заказа с суммой в **₾**.

## Архитектура
```
src/
  config.py            # настройки из .env
  critical_products.py # курируемый список с ID из БД
  source/              # доступ к Firebird (embedded) + SQL
  storage/             # локальное хранилище (SQLAlchemy: PostgreSQL/SQLite) + schema.sql
  etl/                 # источник -> недельные ряды -> хранилище
  analysis/            # классификация, прогноз, параметры запаса, рекомендации
  gui/                 # Streamlit multipage (Stitch UI)
    pages/             # 1_Обзор, 2_Товар, 3_Заказ
design/stitch/         # HTML-референсы и DESIGN.md
docs/                  # схема БД, тесты, roadmap
tests/                 # юнит-тесты
```

## Ключевые правила домена
- **Остаток** = нарастающая сумма `GDDKT.QUANT` по дате `DGVKT.DAT_` (проверено ~99.76%).
- **Спрос/расход** = недельные продажи `STORZAKAZDT`+`STORZDTGDS`, `CSDTKTHBID IN (1,2,3,5)`.
- **Страховой запас (карточка)** = `GOODS.SQNT`.
- **Закупка** = средневзв. `GDDKT.PRICE` по приходам (GEL, ₾).

## Установка
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # при необходимости поправить пути/БД
```
Для чтения `.GDB` нужен Firebird 2.5 embedded в `tools/fb25` (`fbembed.dll`).

## Запуск
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m src.etl.run_etl        # загрузка истории в хранилище
.\.venv\Scripts\python.exe -m src.analysis.recommend # пересчёт рекомендаций
.\.venv\Scripts\python.exe -m streamlit run src/gui/app.py
```

Навигация: **Обзор** → **Товар** → **Заказ** (боковое меню Streamlit).

## Тестирование
Чеклист по этапам: `docs/TESTING.md`.

```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests -q
```

## Хранилище
По умолчанию SQLite (`data/granit_rests.sqlite3`). Цель — PostgreSQL: запустите службу,
создайте БД и пропишите в `.env`:
```
DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5432/granit_rests
```
DDL: `src/storage/schema.sql`.

## Открытые вопросы / калибровка
См. `docs/REQUIREMENTS_WORKSHEET.md`.
