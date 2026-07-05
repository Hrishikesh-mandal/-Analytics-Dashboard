-- =============================================================================
-- Analytics Views (BI Consumption Layer)
-- =============================================================================
-- Power BI connects to these views/materialized views directly rather than
-- to raw OLTP tables — this keeps modeling logic in SQL (single source of
-- truth, version-controlled) instead of duplicated inside Power Query.
--
-- Refresh materialized views on a schedule (see docs/powerbi_connection_guide.md
-- for the recommended cron/pg_cron setup).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- mv_order_facts: one row per order-item, pre-joined and denormalized.
-- This is the primary fact table Power BI's data model is built around.
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_order_facts CASCADE;
CREATE MATERIALIZED VIEW mv_order_facts AS
SELECT
    o.order_id,
    o.customer_id,
    c.state                                  AS customer_state,
    c.city                                   AS customer_city,
    o.order_status,
    o.order_purchase_ts,
    DATE_TRUNC('month', o.order_purchase_ts) AS order_month,
    o.order_delivered_ts,
    o.order_estimated_delivery_date,
    CASE
        WHEN o.order_delivered_ts IS NOT NULL
        THEN EXTRACT(DAY FROM (o.order_delivered_ts - o.order_purchase_ts))
    END                                        AS delivery_days,
    CASE
        WHEN o.order_delivered_ts IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
        THEN (o.order_delivered_ts::date > o.order_estimated_delivery_date)
    END                                        AS is_late_delivery,
    oi.product_id,
    p.product_category,
    oi.seller_id,
    s.seller_state,
    oi.price,
    oi.freight_value,
    (oi.price + oi.freight_value)             AS item_total_value
FROM order_items oi
JOIN orders o     ON o.order_id = oi.order_id
JOIN customers c  ON c.customer_id = o.customer_id
JOIN products p   ON p.product_id = oi.product_id
JOIN sellers s    ON s.seller_id = oi.seller_id;

CREATE UNIQUE INDEX idx_mv_order_facts_pk ON mv_order_facts(order_id, product_id, seller_id);
CREATE INDEX idx_mv_order_facts_month     ON mv_order_facts(order_month);
CREATE INDEX idx_mv_order_facts_category  ON mv_order_facts(product_category);

-- -----------------------------------------------------------------------------
-- mv_customer_metrics: one row per customer with RFM + lifetime metrics,
-- refreshed alongside mv_order_facts. Feeds the customer analytics page.
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_customer_metrics CASCADE;
CREATE MATERIALIZED VIEW mv_customer_metrics AS
WITH order_level AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.order_purchase_ts,
        SUM(oi.price + oi.freight_value) AS order_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status IN ('delivered', 'shipped')
    GROUP BY o.customer_id, o.order_id, o.order_purchase_ts
)
SELECT
    c.customer_id,
    c.state,
    c.signup_date,
    COUNT(ol.order_id)                                   AS total_orders,
    COALESCE(SUM(ol.order_value), 0)                      AS lifetime_value,
    COALESCE(AVG(ol.order_value), 0)                      AS avg_order_value,
    MAX(ol.order_purchase_ts)                             AS last_order_ts,
    (CURRENT_DATE - MAX(ol.order_purchase_ts)::date)      AS days_since_last_order
FROM customers c
LEFT JOIN order_level ol ON ol.customer_id = c.customer_id
GROUP BY c.customer_id, c.state, c.signup_date;

CREATE UNIQUE INDEX idx_mv_customer_metrics_pk ON mv_customer_metrics(customer_id);

-- Convenience function to refresh both views in one call (used by scheduler)
CREATE OR REPLACE FUNCTION refresh_analytics_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_order_facts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_customer_metrics;
END;
$$ LANGUAGE plpgsql;
