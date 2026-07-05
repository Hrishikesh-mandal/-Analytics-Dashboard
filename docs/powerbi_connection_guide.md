# Power BI Connection Guide

## 1. Connect Power BI Desktop to PostgreSQL

1. Open Power BI Desktop → **Get Data** → **More...** → search **PostgreSQL database**.
2. Server: `localhost` (or your DB host) — Database: `ecommerce_analytics`.
3. Choose **Import** mode (not DirectQuery) for this data volume — faster
   visuals, and the materialized views already do the heavy lifting.
4. Credentials: use the `analyst` role from `.env`. If Power BI complains about
   SSL, set `sslmode=disable` for local dev connections only (never in prod).
5. In Navigator, select these objects (do **not** import raw OLTP tables directly):
   - `mv_order_facts`
   - `mv_customer_metrics`
   - `customers` (small dimension table, useful for slicers on raw fields)

## 2. Data model relationships

Set these relationships in Power BI's Model view:

| From                  | To                     | Cardinality |
|-----------------------|------------------------|-------------|
| mv_order_facts[customer_id] | mv_customer_metrics[customer_id] | Many-to-one |

Everything else (product, seller, state) is already denormalized flat into
`mv_order_facts`, so no further joins are needed for the core dashboard —
this was a deliberate modeling choice to keep the Power BI side simple and
push complexity into SQL where it's testable and version-controlled.

## 3. Suggested report pages

**Page 1 — Executive Overview**
- KPI cards: Total Revenue, Total Orders, Avg Order Value, MoM Growth %
  (pull straight from `sql_queries/revenue_analysis.sql` query 1, or
  recreate as DAX measures over `mv_order_facts`)
- Line chart: revenue by `order_month`
- Map or bar chart: revenue by `customer_state`

**Page 2 — Customer Analytics**
- Table/matrix: cohort retention heatmap (rows = cohort_month, columns =
  month_number, values = retention_pct) — load `sql_queries/cohort_analysis.sql`
  as its own query/table since it's not part of the materialized views
- Donut chart: customer segment distribution (from the RFM query)
- Card: average customer lifetime value (`mv_customer_metrics`)

**Page 3 — Product Performance**
- Bar chart: revenue by `product_category`
- Table: bottom-10 underperforming products
- Scatter: avg_review_score vs total_revenue by category

**Page 4 — Operations / Delivery**
- Bar chart: late delivery % by state
- Table: seller scorecard, sorted by revenue_rank
- Gauge: overall on-time delivery rate

## 4. Refreshing the data

The materialized views are snapshots, not live queries. In production you'd:

- Schedule `SELECT refresh_analytics_views();` via `pg_cron` or a cron job
  calling `psql` right after the nightly ETL run finishes.
- In Power BI Service (not Desktop), set up a **scheduled refresh** against
  the gateway pointed at this Postgres instance, timed to run after the
  materialized view refresh completes.

## 5. Why materialized views instead of raw tables

- Keeps join logic and business rules (e.g. "delivered or shipped counts as
  revenue") in one governed place instead of duplicated across every report page.
- Faster report load — the expensive joins/aggregations run once at refresh
  time, not on every visual interaction.
- Power BI's Import mode then just reads pre-computed flat tables, which is
  exactly what it's fastest at.
