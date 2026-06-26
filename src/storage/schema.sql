-- DDL для PostgreSQL (цель). При SQLite-fallback таблицы создаются через pandas.to_sql.
-- Запуск: psql -d granit_rests -f src/storage/schema.sql

CREATE TABLE IF NOT EXISTS products (
    product_key    TEXT PRIMARY KEY,
    label          TEXT NOT NULL,
    kind           TEXT NOT NULL,          -- sku | group
    unit           TEXT NOT NULL,          -- pcs | kg
    target_qty     DOUBLE PRECISION,
    product_id     INTEGER,
    group_ids      TEXT,
    name           TEXT,
    code           TEXT,
    group_name     TEXT,
    safety_stock   DOUBLE PRECISION,       -- GOODS.SQNT
    current_stock  DOUBLE PRECISION,
    unit_purchase_price_gel DOUBLE PRECISION,  -- средневзв. GDDKT.PRICE по приходам
    demand_source  TEXT DEFAULT 'sales',       -- sales | inflow
    note           TEXT
);

CREATE TABLE IF NOT EXISTS weekly_sales (
    product_key TEXT NOT NULL,
    week_start  DATE NOT NULL,
    iso_year    INTEGER NOT NULL,
    iso_week    INTEGER NOT NULL,
    qty         DOUBLE PRECISION,
    amount      DOUBLE PRECISION,
    PRIMARY KEY (product_key, week_start)
);

CREATE TABLE IF NOT EXISTS weekly_stock (
    product_key TEXT NOT NULL,
    week_start  DATE NOT NULL,
    iso_year    INTEGER NOT NULL,
    iso_week    INTEGER NOT NULL,
    stock_end   DOUBLE PRECISION,
    on_hand     DOUBLE PRECISION,
    inflow      DOUBLE PRECISION,
    outflow     DOUBLE PRECISION,
    PRIMARY KEY (product_key, week_start)
);

CREATE TABLE IF NOT EXISTS weekly_demand (
    product_key   TEXT NOT NULL,
    week_start    DATE NOT NULL,
    iso_year      INTEGER NOT NULL,
    iso_week      INTEGER NOT NULL,
    observed_sales DOUBLE PRECISION,
    outflow       DOUBLE PRECISION,
    stock_end     DOUBLE PRECISION,
    stockout_flag INTEGER,
    true_demand   DOUBLE PRECISION,
    PRIMARY KEY (product_key, week_start)
);

CREATE TABLE IF NOT EXISTS recommendations (
    product_key          TEXT PRIMARY KEY,
    as_of_date           DATE,
    current_stock        DOUBLE PRECISION,
    safety_stock_target  DOUBLE PRECISION,
    weekly_consumption   DOUBLE PRECISION,
    demand_class         TEXT,
    lead_time_weeks      DOUBLE PRECISION,
    safety_stock_calc    DOUBLE PRECISION,
    reorder_point        DOUBLE PRECISION,
    weeks_to_stockout    DOUBLE PRECISION,
    depletion_date       DATE,
    reorder_date         DATE,
    recommended_order_qty DOUBLE PRECISION,
    order_cycle_weeks      DOUBLE PRECISION,
    is_urgent              INTEGER,
    service_level        DOUBLE PRECISION,
    unit_purchase_price_gel DOUBLE PRECISION,
    estimated_order_cost_gel DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS replenishment_stats (
    product_key              TEXT PRIMARY KEY,
    order_count              INTEGER,
    last_order_date          DATE,
    last_order_qty           DOUBLE PRECISION,
    median_batch             DOUBLE PRECISION,
    median_interval_weeks    DOUBLE PRECISION,
    implied_cover_weeks      DOUBLE PRECISION,
    order_cycle_weeks        DOUBLE PRECISION,
    model_cycle_weeks        DOUBLE PRECISION,
    cycle_reliable           INTEGER,
    data_note                TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);
