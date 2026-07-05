-- =============================================================================
-- RFM Customer Segmentation (Recency, Frequency, Monetary)
-- Scores every customer 1-5 on each dimension using NTILE, then buckets
-- them into human-readable segments. Standard technique for the "customer
-- analytics" page of the dashboard.
-- Demonstrates: NTILE window function, CASE-based business-rule mapping.
-- =============================================================================

WITH customer_orders AS (
    SELECT
        o.customer_id,
        MAX(o.order_purchase_ts)::date                    AS last_order_date,
        COUNT(DISTINCT o.order_id)                         AS frequency,
        SUM(oi.price + oi.freight_value)                   AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status IN ('delivered', 'shipped')
    GROUP BY o.customer_id
),
rfm_base AS (
    SELECT
        customer_id,
        (CURRENT_DATE - last_order_date)  AS recency_days,
        frequency,
        monetary
    FROM customer_orders
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- lower recency_days = better, so invert the tiling direction
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_base
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score)                  AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'champions'
        WHEN r_score >= 4 AND f_score >= 3                  THEN 'loyal_customers'
        WHEN r_score >= 4 AND f_score <= 2                   THEN 'new_customers'
        WHEN r_score BETWEEN 2 AND 3 AND f_score >= 3        THEN 'at_risk'
        WHEN r_score <= 2 AND f_score >= 4                   THEN 'cant_lose_them'
        WHEN r_score <= 2 AND f_score <= 2                   THEN 'hibernating'
        ELSE 'needs_attention'
    END                                             AS customer_segment
FROM rfm_scored
ORDER BY rfm_total DESC;
