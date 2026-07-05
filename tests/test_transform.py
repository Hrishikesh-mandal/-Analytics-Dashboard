"""
Unit tests for the transform stage. Run with: pytest tests/
Focus is on the cleaning invariants that actually matter for data quality -
dedup, FK integrity, and value clipping - since those are the parts a
resume reviewer / interviewer is most likely to probe on.
"""
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.transform import (
    clean_customers, clean_products, clean_orders, clean_order_items,
)


def test_clean_customers_dedups_by_id():
    df = pd.DataFrame({
        "customer_id": ["c1", "c1", "c2"],
        "customer_unique_id": ["u1", "u1", "u2"],
        "signup_date": ["2024-01-01", "2024-01-01", "2024-02-01"],
        "city": [" Mumbai ", " Mumbai ", None],
        "state": ["mh", "mh", "dl"],
    })
    result = clean_customers(df)
    assert len(result) == 2
    assert result["city"].isna().sum() == 0  # unknown fallback applied
    assert set(result["state"]) == {"MH", "DL"}


def test_clean_products_fixes_negative_margin():
    df = pd.DataFrame({
        "product_id": ["p1"],
        "product_category": ["electronics"],
        "product_weight_g": [500.0],
        "unit_cost": [100.0],
        "list_price": [50.0],  # priced below cost - should be corrected
    })
    result = clean_products(df)
    assert result.loc[0, "list_price"] > result.loc[0, "unit_cost"]


def test_clean_orders_drops_orphaned_customer_fk():
    df = pd.DataFrame({
        "order_id": ["o1", "o2"],
        "customer_id": ["c1", "c_missing"],
        "order_status": ["delivered", "delivered"],
        "order_purchase_ts": ["2024-01-01 10:00:00", "2024-01-02 10:00:00"],
        "order_approved_ts": ["2024-01-01 11:00:00", "2024-01-02 11:00:00"],
        "order_delivered_ts": ["2024-01-05 10:00:00", "2024-01-06 10:00:00"],
        "order_estimated_delivery_date": ["2024-01-06", "2024-01-07"],
    })
    result = clean_orders(df, valid_customer_ids={"c1"})
    assert len(result) == 1
    assert result.iloc[0]["order_id"] == "o1"


def test_clean_order_items_enforces_all_fks():
    df = pd.DataFrame({
        "order_id": ["o1", "o1"],
        "order_item_seq": [1, 2],
        "product_id": ["p1", "p_missing"],
        "seller_id": ["s1", "s1"],
        "price": [100.0, 50.0],
        "freight_value": [10.0, -5.0],  # negative should be clipped, row dropped anyway via FK
    })
    result = clean_order_items(
        df, valid_order_ids={"o1"}, valid_product_ids={"p1"}, valid_seller_ids={"s1"}
    )
    assert len(result) == 1
    assert result.iloc[0]["product_id"] == "p1"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
