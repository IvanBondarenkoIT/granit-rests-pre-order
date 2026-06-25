"""Курируемый список критических расходников с сопоставлением к БД (GOODS.ID / группы).

Источник: docs/CRITICAL_PRODUCTS.md (сопоставлено пробингом, 15/16).
- kind="sku":   один товар, product_id = GOODS.ID
- kind="group": агрегат по группе(ам) GOODSGROUPS — суммируем все GOODS с OWNER в group_ids
target_qty — типичный объём последнего заказа (партия-ориентир), не GOODS.SQNT.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CriticalItem:
    key: str
    label: str
    kind: str  # "sku" | "group"
    unit: str  # "pcs" | "kg"
    target_qty: float | None
    product_id: int | None = None
    group_ids: tuple[int, ...] = field(default_factory=tuple)
    param_ids: tuple[int, int] | None = None  # (GDSPARAMPRM.ID, GDSPARAMVAL.ID) e.g. Продукция=Кофе(кг)
    note: str = ""


CRITICAL_ITEMS: list[CriticalItem] = [
    CriticalItem("bag_paper", "Bag paper", "sku", "pcs", 300, product_id=24286,
                 note="бесплатный расходник: спрос из приходов GDDKT, не из продаж"),
    CriticalItem("coffee", "Coffee", "group", "kg", 1700,
                 param_ids=(2, 3),
                 note="Параметр Продукция=Кофе(кг); агрегат одной строкой (сумма кг)"),
    CriticalItem("caotina", "Caotina", "group", "kg", 250, group_ids=(22939,),
                 note="агрегат группы 22939 (все фасовки Caotina)"),
    CriticalItem("caotina_100_dark", "Caotina 100г dark", "sku", "pcs", 30, product_id=25979),
    CriticalItem("caotina_100_original", "Caotina 100г original", "sku", "pcs", 30, product_id=25920),
    CriticalItem("cup_12oz", "Cup 12 oz", "sku", "pcs", 2000, product_id=26213),
    CriticalItem("cup_8oz", "Cup 8 oz", "sku", "pcs", 2000, product_id=24500),
    CriticalItem("cup_4oz", "Cup 4 oz", "sku", "pcs", 500, product_id=24790),
    CriticalItem("drip_ethiopia", "Drip Ethiopia", "sku", "pcs", 30, product_id=27248),
    CriticalItem("drip_lilla_rose", "Drip Lilla&Rose", "sku", "pcs", 30, product_id=26498),
    CriticalItem("dlsc002", "DeLonghi DLSC002", "sku", "pcs", 300, product_id=24227),
    CriticalItem("dlsc500", "DeLonghi DLSC500", "sku", "pcs", 500, product_id=22284,
                 note="Delonghi Liquid for descaling 500ml, CODE AS00006183"),
    CriticalItem("dlsc550", "DeLonghi DLSC550", "sku", "pcs", 30, product_id=24980),
    CriticalItem("dlsc060", "DeLonghi DLSC060", "sku", "pcs", 5, product_id=25027),
    CriticalItem("dlsc069", "DeLonghi DLSC069", "sku", "pcs", 5, product_id=25594),
    CriticalItem("dlsc058", "DeLonghi DLSC058", "sku", "pcs", 5, product_id=24999),
    CriticalItem("sugar", "Sugar", "sku", "kg", 50, product_id=22267),
]


def resolved_items() -> list[CriticalItem]:
    """Только позиции, сопоставленные с БД (есть product_id, group_ids или param_ids)."""
    return [i for i in CRITICAL_ITEMS if i.product_id is not None or i.group_ids or i.param_ids]


def unmatched_items() -> list[CriticalItem]:
    return [i for i in CRITICAL_ITEMS
            if i.product_id is None and not i.group_ids and not i.param_ids]
