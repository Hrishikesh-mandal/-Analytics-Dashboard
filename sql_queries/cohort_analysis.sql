-- =============================================================================
-- Cohort Retention Analysis
-- Groups customers by signup month, tracks what % of each cohort placed an
-- order in each subsequent month. Classic SaaS/e-commerce retention view.
-- Demonstrates: multi-step CTEs, DATE_TRUNC, self-referential month math.
-- =============================================================================

WITH customer_cohort AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date) AS cohort_month
    FROM customers
),
customer_orders_monthly AS (
    SELECT DISTINCT
        o.customer_id,
        DATE_TRUNC('month', o.order_purchase_ts) AS order_month
    FROM orders o
    WHERE o.order_status IN ('delivered', 'shipped')
),
cohort_activity AS (
    SELECT
        cc.cohort_month,
        com.order_month,
        -- months elapsed since cohort start (0 = signup month itself)
        (EXTRACT(YEAR FROM com.order_month) - EXTRACT(YEAR FROM cc.cohort_month)) * 12
          + (EXTRACT(MONTH FROM com.order_month) - EXTRACT(MONTH FROM cc.cohort_month)) AS month_number,
        com.customer_id
    FROM customer_cohort cc
    JOIN customer_orders_monthly com ON com.customer_id = cc.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM customer_cohort
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_customers,
    ca.month_number,
    COUNT(DISTINCT ca.customer_id)                                       AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_customers, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs ON cs.cohort_month = ca.cohort_month
WHERE ca.month_number BETWEEN 0 AND 11   -- first 12 months of cohort life
GROUP BY ca.cohort_month, cs.cohort_customers, ca.month_number
ORDER BY ca.cohort_month, ca.month_number;
