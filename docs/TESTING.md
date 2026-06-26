# Чеклист тестирования (gate перед коммитом этапа)

Обязательный минимум — см. `AGENTS.md` §8.

## Общий gate

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m src.analysis.recommend
```

**DLSC002:** `current_stock` > 0, `weekly_consumption` ~30–45, `on_hand` в последней неделе ≈ `current_stock`.

При изменении ETL:

```powershell
.\.venv\Scripts\python.exe -m src.etl.run_etl
```

## Flask UI (этап 9)

| Авто | Ручной smoke |
|------|----------------|
| `pytest tests/test_web.py` | `python -m src.web.app` → http://localhost:5000 |
| | Нижняя навигация: Обзор / Товар / Заказ |
| | Обзор: KPI + фильтр «Срочные», DLSC002 в списке |
| | Товар: переключатель Сезон / Остаток / Прогноз (один график) |
| | Сезон: средняя — жирная зелёная; годы — близкие оттенки |
| | Остаток: линия `on_hand`, маркеры прихода |
| | Заказ: чекбоксы, итог ₾ |
