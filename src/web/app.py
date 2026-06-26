"""Flask-приложение: Обзор / Товар / Заказ."""
from __future__ import annotations

import json

import pandas as pd
from flask import Blueprint, Flask, jsonify, render_template, request

from src.analysis import recommend
from src.config import SETTINGS
from src.storage import db
from src.web.services import catalog, charts, status

overview_bp = Blueprint("overview", __name__)
product_bp = Blueprint("product", __name__)
order_bp = Blueprint("order", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")

BORDER = {
    status.STATUS_ORDER_NOW: "border-red-500",
    status.STATUS_SOON: "border-amber-500",
    status.STATUS_OK: "border-green-600",
}


@overview_bp.route("/")
def index():
    data = catalog.load_tables()
    cat = catalog.merged_catalog(data)
    lt = catalog.lead_time_weeks()
    filter_mode = request.args.get("filter", "all")

    if cat.empty:
        return render_template(
            "overview.html", active_tab="overview", has_data=False,
            counts={"order_now": 0, "soon": 0, "ok": 0}, items=[], filter_mode=filter_mode,
        )

    rows = []
    for _, row in cat.iterrows():
        st = status.urgency_status(row, lead_time_weeks=lt)
        if filter_mode == "urgent" and st == status.STATUS_OK:
            continue
        wts = row.get("weeks_to_stockout")
        cover = f"{wts:.0f} нед" if pd.notna(wts) else ">104 нед"
        badge_label, badge_class = status.STATUS_BADGE[st]
        rows.append({
            "product_key": row["product_key"],
            "label": row["label"],
            "unit": row.get("unit", ""),
            "current_stock": float(row.get("current_stock") or 0),
            "cover": cover,
            "reorder_date": status.format_date(row.get("reorder_date")),
            "demand_source": row.get("demand_source") or "sales",
            "badge_label": badge_label,
            "badge_class": badge_class,
            "border_class": BORDER[st],
            "_sort": {status.STATUS_ORDER_NOW: 0, status.STATUS_SOON: 1, status.STATUS_OK: 2}[st],
            "_wts": float(wts) if pd.notna(wts) else 9999,
        })
    rows.sort(key=lambda x: (x["_sort"], x["_wts"]))

    return render_template(
        "overview.html",
        active_tab="overview",
        has_data=True,
        counts=status.status_summary(cat, lead_time_weeks=lt),
        items=rows,
        filter_mode=filter_mode,
    )


@product_bp.route("/product")
def index():
    data = catalog.load_tables()
    cat = catalog.merged_catalog(data)
    if cat.empty:
        return render_template("product.html", active_tab="product", has_product=False)

    keys = cat["product_key"].tolist()
    key = request.args.get("key", keys[0])
    if key not in keys:
        key = keys[0]
    chart = request.args.get("chart", "season")
    if chart not in ("season", "stock", "forecast"):
        chart = "season"

    prow = cat[cat["product_key"] == key].iloc[0]
    sales, stock, demand = catalog.product_series(data, key)
    current_stock = float(prow.get("current_stock") or 0)
    safety = float(prow.get("safety_stock") or 0)

    payload = charts.build_chart_payload(chart, sales, stock, demand, current_stock, safety)
    payload["productKey"] = key

    price = prow.get("unit_purchase_price_gel")
    price_f = float(price) if price is not None and pd.notna(price) else None
    years_filter = charts.season_years(sales) if chart == "season" else None
    rep_row = data.get("replenishment_stats", pd.DataFrame())
    rep_stats = None
    if not rep_row.empty:
        m = rep_row[rep_row["product_key"] == key]
        if not m.empty:
            rep_stats = m.iloc[0].to_dict()
    metrics = charts.product_metrics(
        demand, current_stock, safety, years=years_filter, unit_price=price_f,
        target_qty=float(prow.get("target_qty") or 0) or None,
        rep_stats=rep_stats,
    )
    fmt = charts.format_metrics_display(metrics)

    captions = {
        "season": (
            "Продажи по календарным неделям (ось — даты). "
            "Средняя — жирная зелёная линия поверх годов."
        ),
        "stock": f"Остаток на складе (приход − продажи). Якорь = текущий остаток {current_stock:,.0f}.",
        "forecast": "Прогноз исчерпания от текущего остатка.",
    }

    return render_template(
        "product.html",
        active_tab="product",
        has_product=True,
        product=prow,
        products=cat[["product_key", "label"]].to_dict("records"),
        chart=chart,
        chart_json=json.dumps(payload),
        chart_caption=captions[chart],
        stock_fmt=f"{current_stock:,.0f}".replace(",", " "),
        consumption_fmt=fmt["consumption_fmt"],
        reorder_date=fmt["reorder_date"],
        depletion_date=fmt["depletion_date"],
        qty_fmt=fmt["qty_fmt"],
        rop_fmt=fmt["rop_fmt"],
        policy_note=fmt["policy_note"],
        is_urgent=fmt["is_urgent"],
        cost_gel=fmt["cost_gel"],
        replenishment=rep_stats,
    )


@api_bp.route("/product/<product_key>/metrics")
def product_metrics(product_key: str):
    years = request.args.getlist("years", type=int) or None
    data = catalog.load_tables()
    cat = catalog.merged_catalog(data)
    prow = cat[cat["product_key"] == product_key]
    if prow.empty:
        return jsonify({"error": "not found"}), 404
    row = prow.iloc[0]
    _, _, demand = catalog.product_series(data, product_key)
    price = row.get("unit_purchase_price_gel")
    price_f = float(price) if price is not None and pd.notna(price) else None
    rep_stats = None
    if db.table_exists("replenishment_stats"):
        rs = db.read_df("replenishment_stats")
        m = rs[rs["product_key"] == product_key]
        if not m.empty:
            rep_stats = m.iloc[0].to_dict()
    metrics = charts.product_metrics(
        demand,
        float(row.get("current_stock") or 0),
        float(row.get("safety_stock") or 0),
        years=years,
        unit_price=price_f,
        target_qty=float(row.get("target_qty") or 0) or None,
        rep_stats=rep_stats,
    )
    return jsonify(metrics)


@api_bp.route("/product/<product_key>/chart-data")
def chart_data(product_key: str):
    chart = request.args.get("chart", "season")
    data = catalog.load_tables()
    cat = catalog.merged_catalog(data)
    prow = cat[cat["product_key"] == product_key]
    if prow.empty:
        return jsonify({"error": "not found"}), 404
    row = prow.iloc[0]
    sales, stock, demand = catalog.product_series(data, product_key)
    years = request.args.getlist("years", type=int) or None
    payload = charts.build_chart_payload(
        chart, sales, stock, demand,
        float(row.get("current_stock") or 0),
        float(row.get("safety_stock") or 0),
        years=years,
    )
    return jsonify(payload)


@order_bp.route("/order", methods=["GET", "POST"])
def index():
    data = catalog.load_tables()
    cat = catalog.merged_catalog(data)
    if cat.empty:
        return render_template("order.html", active_tab="order", has_data=False)

    default_cycle = int(SETTINGS.default_lead_time_weeks)
    if request.method == "POST":
        cycle = int(request.form.get("cycle", default_cycle))
    else:
        cycle = int(request.args.get("cycle", default_cycle))
    cycle = max(2, min(26, cycle))
    mip = recommend.multi_item_plan(cycle_weeks=cycle)
    mip = mip.merge(cat[["product_key", "unit_purchase_price_gel"]], on="product_key", how="left")
    plan = recommend.sync_plan(cat)
    sync_date = plan["sync_order_date"].iloc[0] if not plan.empty else "—"

    export_lines = None
    if request.method == "POST" and request.form.get("action") == "export":
        lines = []
        for _, row in mip.iterrows():
            key = row["product_key"]
            if request.form.get(f"sel_{key}"):
                qty = float(request.form.get(f"qty_{key}", 0) or 0)
                if qty > 0:
                    price = row.get("unit_purchase_price_gel")
                    cost = ""
                    if price is not None and pd.notna(price):
                        cost = f" · {status.format_gel(qty * float(price))}"
                    lines.append(f"- {row['label']}: {qty:,.0f} {row['unit']}{cost}")
        export_lines = "\n".join(lines) if lines else "Нет выбранных позиций"

    rows = []
    total_gel = 0.0
    total_count = 0
    for _, row in mip.iterrows():
        key = row["product_key"]
        qty = float(row["order_qty_sync"])
        checked = qty > 0
        if request.method == "POST":
            checked = bool(request.form.get(f"sel_{key}"))
            qty = float(request.form.get(f"qty_{key}", qty) or 0)
        price = row.get("unit_purchase_price_gel")
        line_cost = float(qty) * float(price) if price is not None and pd.notna(price) else None
        cost_str = status.format_gel(line_cost) if line_cost else "—"
        if checked and qty > 0:
            total_count += 1
            if line_cost:
                total_gel += line_cost
        rows.append({
            "product_key": key,
            "label": row["label"],
            "unit": row.get("unit", ""),
            "stock_fmt": f"{row['current_stock']:,.0f}".replace(",", " "),
            "qty": qty,
            "cost": cost_str,
            "checked": checked,
        })

    return render_template(
        "order.html",
        active_tab="order",
        has_data=True,
        sync_date=sync_date,
        cycle=cycle,
        default_cycle=default_cycle,
        rows=rows,
        total_count=total_count,
        total_gel=status.format_gel(total_gel) if total_gel else "—",
        export_lines=export_lines,
    )


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.register_blueprint(overview_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(api_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
