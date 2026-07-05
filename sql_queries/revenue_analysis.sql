-- =============================================================================
-- Revenue Analysis: monthly trend, running totals, MoM growth
-- Demonstrates: window functions (SUM OVER, LAG), CTEs
-- =============================================================================

-- 1. Monthly revenue with running total and month-over-month growth %
WITH monthly_revenue AS (
    SELECT
        order_month,
        SUM(item_total_value) AS revenue,
        COUNT(DISTINCT order_id) AS order_count
    FROM mv_order_facts
    WHERE order_status IN ('delivered', 'shipped')
    GROUP BY order_month
)
SELECT
    order_month,
    revenue,
    order_count,
    ROUND(revenue / NULLIF(order_count, 0), 2)                         AS avg_order_value,
    SUM(revenue) OVER (ORDER BY order_month)                           AS running_total_revenue,
    LAG(revenue) OVER (ORDER BY order_month)                           AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
        / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 2
    )                                                                   AS mom_growth_pct
FROM monthly_revenue
ORDER BY order_month;

-- 2. Revenue by state, ranked, with each state's share of total revenue
WITH state_revenue AS (
    SELECT customer_state, SUM(item_total_value) AS revenue
    FROM mv_order_facts
    WHERE order_status IN ('delivered', 'shipped')
    GROUP BY customer_state
)
SELECT
    customer_state,
    revenue,
    RANK() OVER (ORDER BY revenue DESC)                     AS revenue_rank,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)        AS pct_of_total_revenue
FROM state_revenue
ORDER BY revenue_rank;

-- 3. Top 5 revenue-generating product categories per state (window + filter pattern)
WITH category_state_revenue AS (
    SELECT
        customer_state,
        product_category,
        SUM(item_total_value) AS revenue
    FROM mv_order_facts
    WHERE order_status IN ('delivered', 'shipped')
    GROUP BY customer_state, product_category
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY revenue DESC) AS rn
    FROM category_state_revenue
)
SELECT customer_state, product_category, revenue
FROM ranked
WHERE rn <= 5
ORDER BY customer_state, revenue DESC;
