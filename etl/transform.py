"""
Transform stage: cleans raw dataframes and enforces the invariants the
database schema expects (no dupes, consistent casing/whitespace, valid
foreign keys, parsed timestamps). This is the module that actually earns
the "data cleaning" line on a resume — every step below fixes a specific
kind of mess introduced in etl/data_generator.py (or that you'd find in any
real raw export).
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def _clean_text_column(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().replace({"none": None, "nan": None})


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["customer_id"]).copy()
    df["city"] = _clean_text_column(df["city"])
    df["city"] = df["city"].fillna("unknown")
    df["state"] = df["state"].str.upper().str.strip()
    df["signup_date"] = pd.to_datetime(df["signup_date"]).dt.date
    logger.info("customers: %d -> %d rows after dedup", before, len(df))
    return df


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["seller_id"]).copy()
    df["seller_city"] = _clean_text_column(df["seller_city"]).fillna("unknown")
    df["seller_state"] = df["seller_state"].str.upper().str.strip()
    df["joined_date"] = pd.to_datetime(df["joined_date"]).dt.date
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["product_id"]).copy()
    df["product_category"] = _clean_text_column(df["product_category"])
    # guard against bad economics: list_price should never be below unit_cost
    bad = df["list_price"] < df["unit_cost"]
    if bad.any():
        logger.warning("Fixing %d products with list_price < unit_cost", bad.sum())
        df.loc[bad, "list_price"] = df.loc[bad, "unit_cost"] * 1.2
    return df


def clean_orders(df: pd.DataFrame, valid_customer_ids: set) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"]).copy()
    df = df[df["customer_id"].isin(valid_customer_ids)]  # drop orphaned FK rows
    for col in ["order_purchase_ts", "order_approved_ts", "order_delivered_ts"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["order_estimated_delivery_date"] = pd.to_datetime(
        df["order_estimated_delivery_date"], errors="coerce"
    ).dt.date
    df["order_status"] = df["order_status"].str.strip().str.lower()
    logger.info("orders: %d -> %d rows after cleaning/FK validation", before, len(df))
    return df


def clean_order_items(df: pd.DataFrame, valid_order_ids: set,
                       valid_product_ids: set, valid_seller_ids: set) -> pd.DataFrame:
    before = len(df)
    df = df[
        df["order_id"].isin(valid_order_ids)
        & df["product_id"].isin(valid_product_ids)
        & df["seller_id"].isin(valid_seller_ids)
    ].copy()
    df = df.drop_duplicates(subset=["order_id", "order_item_seq"])
    df["price"] = df["price"].clip(lower=0)
    df["freight_value"] = df["freight_value"].clip(lower=0)
    logger.info("order_items: %d -> %d rows after cleaning/FK validation", before, len(df))
    return df


def clean_payments(df: pd.DataFrame, valid_order_ids: set) -> pd.DataFrame:
    df = df[df["order_id"].isin(valid_order_ids)].copy()
    df = df.drop_duplicates(subset=["order_id", "payment_seq"])
    df["payment_value"] = df["payment_value"].clip(lower=0)
    return df


def clean_reviews(df: pd.DataFrame, valid_order_ids: set) -> pd.DataFrame:
    df = df[df["order_id"].isin(valid_order_ids)].copy()
    df = df.drop_duplicates(subset=["review_id"])
    df["review_score"] = df["review_score"].clip(lower=1, upper=5)
    df["review_created_ts"] = pd.to_datetime(df["review_created_ts"], errors="coerce")
    df = df.dropna(subset=["review_created_ts"])
    return df


def transform_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Runs cleaning in FK-safe order: parents before children."""
    customers = clean_customers(raw["customers"])
    sellers = clean_sellers(raw["sellers"])
    products = clean_products(raw["products"])

    orders = clean_orders(raw["orders"], set(customers["customer_id"]))
    order_items = clean_order_items(
        raw["order_items"],
        valid_order_ids=set(orders["order_id"]),
        valid_product_ids=set(products["product_id"]),
        valid_seller_ids=set(sellers["seller_id"]),
    )
    payments = clean_payments(raw["payments"], set(orders["order_id"]))
    reviews = clean_reviews(raw["reviews"], set(orders["order_id"]))

    return {
        "customers": customers,
        "sellers": sellers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "reviews": reviews,
    }
