# SQL отчёта «Остаток товара (по доступным группам)»

**Статус:** SQL **извлечён** из шаблона Granit (не из `FRREPORT` в GDB).

## Источник

| Поле | Значение |
|------|----------|
| Файл | `data/input/GRANIT/FrfStor/Наличие товара/Остаток товара (по доступным группам).frf` |
| Формат | FastReport binary (`.frf`), кодировка cp1251 |
| Утилита | `tools/stock_scan_granit_fr3.py --extract "по доступным группам"` (после реализации) |

## SQL запроса отчёта

Параметры FastReport: `:OrgnID` (или `:CURORGNID`), `:EDATE`, `:USERID`.

```sql
Select
  Sum(p.qend) Quant,
  Sum((p.price - p.nds) * p.qend) NSUMMA,
  Sum(p.nds * p.Qend) SUMNDS,
  G.ID,
  G.Name,
  G.Code,
  G.Cod,
  G.One,
  Sum(P.QEnd * P.Price) SUMMA,
  GG.ID GGID,
  GG.Name GGNAME
From GddDt_MoveGoodsAll(:OrgnID, :EDATE, :EDATE) P
Join Goods G on G.ID = P.GID
Join Goods GG on GG.ID = G.Owner
Join UserGGrp UG on UG.GGrpID = GG.ID and UG.UserID = :USERID
Group By G.ID, G.Name, G.Code, G.Cod, G.One, GG.ID, GG.Name
Having Abs(Sum(p.qend)) > 1.0e-10
Order By GG.Name, G.Name, G.Code, G.ID
```

**Ключевые отличия от леджера `SUM(GDDKT.QUANT)`:**

1. Остаток = **`Sum(P.QEND)`** из процедуры **`GddDt_MoveGoodsAll(OrgnID, BDATE, EDATE)`** — оба конца периода = **одна дата** (`:EDATE`).
2. Фильтр **доступных групп** пользователя через **`UserGGrp`** (не все группы из `GOODSGROUPS`).
3. Скрыты нулевые строки: `Having Abs(Sum(p.qend)) > 1.0e-10`.

## Упрощённый запрос для одного SKU (сверка)

```sql
SELECT SUM(P.QEND) AS QUANT
FROM GddDt_MoveGoodsAll(?, CAST(? AS DATE), CAST(? AS DATE)) P
WHERE P.GID = ?
```

Параметры для локальной `GEORGIA.GDB`:

| Параметр | Значение |
|----------|----------|
| `OrgnID` | **12978** (`SELECT DISTINCT OURORGNID FROM STORLIST`) |
| `EDATE` | дата в шапке отчёта |
| `USERID` | ID пользователя Granit (для группы 26761 доступны многие; по умолчанию `1`) |

## Результаты probe (2026-06-25, локальная GDB)

| GOODS.ID | SKU | Benchmark | `SUM(GDDKT)` | `MoveGoodsAll(12978, EDATE, EDATE)` |
|----------|-----|-----------|--------------|-------------------------------------|
| 24227 | DLSC002 | 1105 | 1139 | 1139 при EDATE=2026-06-25 |
| 22284 | DLSC500 | 1124 | 1173 | 1173 |
| 24980 | DLSC550 | 141 | 142 | 142 |

При `EDATE=2024-06-25` на **текущей** копии GDB значения исторические (67 / 631 / 94) — snapshot GDB новее скрина.

**Вывод:** формула отчёта = `MoveGoodsAll`, но benchmark (+34/+49) отражает **момент снятия скрина** (частичный учёт документов 106320/106351 от 23.06.2026), а не другой SQL. На «свежей» дате `QEND` совпадает с леджером.

## Леджер (канон ETL до уточнения)

```sql
SELECT COALESCE(SUM(K.QUANT), 0)
FROM GDDKT K
WHERE K.GDSKEY = :goods_id
  AND K.QUANT IS NOT NULL
```

См. также [`STOCK_CALIBRATION_FINDINGS.md`](STOCK_CALIBRATION_FINDINGS.md).
