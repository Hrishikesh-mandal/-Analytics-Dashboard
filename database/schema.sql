-- =============================================================================
-- E-Commerce Analytics Platform - Database Schema
-- =============================================================================
-- Design notes:
--   - Modeled after real-world e-commerce marketplaces (Olist-style: multi-seller,
--     multi-item orders, separate payment and review lifecycles).
--   - 3NF normalized OLTP-style schema. Analytical views (star-schema-ish) are
--     built on top of this in database/views.sql for BI consumption.
--   - All surrogate keys use natural business IDs (varchar) where the source
--     system would realistically produce them (order_id, customer_id, etc.),
--     matching how you'd actually receive this data from an ETL feed.
-- =============================================================================

DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- -----------------------------------------------------------------------------
-- customers: one row per unique customer
-- -----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id         VARCHAR(32) PRIMARY KEY,
    customer_unique_id  VARCHAR(32) NOT NULL,
    signup_date         DATE NOT NULL,
    city                VARCHAR(100) NOT NULL,
    state               VARCHAR(2)  NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- sellers: marketplace sellers fulfilling orders
-- -----------------------------------------------------------------------------
CREATE TABLE sellers (
    seller_id    VARCHAR(32) PRIMARY KEY,
    seller_city  VARCHAR(100) NOT NULL,
    seller_state VARCHAR(2)  NOT NULL,
    joined_date  DATE NOT NULL
);

-- -----------------------------------------------------------------------------
-- products: product catalog
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    product_id      VARCHAR(32) PRIMARY KEY,
    product_category VARCHAR(100) NOT NULL,
    product_weight_g NUMERIC(10,2) CHECK (product_weight_g > 0),
    unit_cost        NUMERIC(10,2) NOT NULL CHECK (unit_cost >= 0),
    list_price       NUMERIC(10,2) NOT NULL CHECK (list_price >= 0)
);

-- -----------------------------------------------------------------------------
-- orders: one row per order (order header)
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id             VARCHAR(32) PRIMARY KEY,
    customer_id          VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    order_status         VARCHAR(20) NOT NULL CHECK (order_status IN
                            ('delivered','shipped','canceled','processing','returned')),
    order_purchase_ts    TIMESTAMP NOT NULL,
    order_approved_ts    TIMESTAMP,
    order_delivered_ts   TIMESTAMP,
    order_estimated_delivery_date DATE
);

CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_orders_purchase_ts ON orders(order_purchase_ts);
CREATE INDEX idx_orders_status     ON orders(order_status);

-- -----------------------------------------------------------------------------
-- order_items: line items per order (an order can have multiple products/sellers)
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
    order_id      VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    order_item_seq SMALLINT NOT NULL,
    product_id    VARCHAR(32) NOT NULL REFERENCES products(product_id),
    seller_id     VARCHAR(32) NOT NULL REFERENCES sellers(seller_id),
    price         NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    freight_value NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_seq)
);

CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_order_items_seller  ON order_items(seller_id);

-- -----------------------------------------------------------------------------
-- payments: an order can be paid via multiple installments/methods
-- -----------------------------------------------------------------------------
CREATE TABLE payments (
    order_id        VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    payment_seq     SMALLINT NOT NULL,
    payment_type    VARCHAR(20) NOT NULL CHECK (payment_type IN
                        ('credit_card','debit_card','upi','wallet','cod')),
    installments    SMALLINT NOT NULL DEFAULT 1 CHECK (installments >= 1),
    payment_value   NUMERIC(10,2) NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_seq)
);

-- -----------------------------------------------------------------------------
-- reviews: one review per order (0 or 1 in practice)
-- -----------------------------------------------------------------------------
CREATE TABLE reviews (
    review_id       VARCHAR(32) PRIMARY KEY,
    order_id        VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    review_score    SMALLINT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_created_ts TIMESTAMP NOT NULL
);

CREATE INDEX idx_reviews_order ON reviews(order_id);
