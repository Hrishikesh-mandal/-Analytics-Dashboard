-- =============================================================================
-- Product Performance Analysis
-- Demonstrates: aggregate joins across order_items/products/reviews,
-- HAVING clause, correlated subqueries.
-- =============================================================================

-- 1. Product category performance: revenue, units sold, avg review score
SELECT
    p.product_category,
    COUNT(DISTINCT oi.order_id)                              AS orders_containing_category,
    SUM(oi.price + oi.freight_value)                          AS total_revenue,
    ROUND(AVG(oi.price), 2)                                   AS avg_item_price,
    ROUND(AVG(r.review_score), 2)                             AS avg_review_score
FROM order_items oi
JOIN products p   ON p.product_id = oi.product_id
JOIN orders o     ON o.order_id = oi.order_id
LEFT JOIN reviews r ON r.order_id = o.order_id
WHERE o.order_status IN ('delivered', 'shipped')
GROUP BY p.product_category
HAVING SUM(oi.price + oi.freight_value) > 0
ORDER BY total_revenue DESC;

-- 2. Bottom 10 products by revenue with at least 5 orders (underperformers
--    worth flagging, not just "never sold" noise)
SELECT
    p.product_id,
    p.product_category,
    COUNT(DISTINCT oi.order_id)      AS order_count,
    SUM(oi.price + oi.freight_value) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o   ON o.order_id = oi.order_id
WHERE o.order_status IN ('delivered', 'shipped')
GROUP BY p.product_id, p.product_category
HAVING COUNT(DISTINCT oi.order_id) >= 5
ORDER BY total_revenue ASC
LIMIT 10;

-- =============================================================================
-- Delivery & Operations Analysis
-- Demonstrates: date arithmetic, conditional aggregation, seller-level rollups.
-- =============================================================================

-- 3. Late delivery rate and avg delivery time by state
SELECT
    customer_state,
    COUNT(*)                                                          AS delivered_orders,
    ROUND(AVG(delivery_days), 2)                                      AS avg_delivery_days,
    SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)                 AS late_deliveries,
    ROUND(100.0 * SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                               AS late_delivery_pct
FROM mv_order_facts
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL
GROUP BY customer_state
ORDER BY late_delivery_pct DESC;

-- 4. Seller performance scorecard: revenue, avg delivery time, review score,
--    ranked so the ops team can spot underperforming sellers fast
WITH seller_stats AS (
    SELECT
        f.seller_id,
        f.seller_state,
        SUM(f.item_total_value)               AS revenue,
        COUNT(DISTINCT f.order_id)            AS orders_fulfilled,
        ROUND(AVG(f.delivery_days), 2)        AS avg_delivery_days
    FROM mv_order_facts f
    WHERE f.order_status = 'delivered'
    GROUP BY f.seller_id, f.seller_state
)
SELECT
    ss.*,
    r.avg_review_score,
    RANK() OVER (ORDER BY ss.revenue DESC) AS revenue_rank
FROM seller_stats ss
LEFT JOIN (
    SELECT oi.seller_id, ROUND(AVG(rv.review_score), 2) AS avg_review_score
    FROM order_items oi
    JOIN reviews rv ON rv.order_id = oi.order_id
    GROUP BY oi.seller_id
) r ON r.seller_id = ss.seller_id
ORDER BY revenue_rank;
