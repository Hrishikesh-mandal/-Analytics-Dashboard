"""
Simulates raw, messy source-system exports for the e-commerce platform.

In a real project this step wouldn't exist (you'd pull from Kaggle's Olist
dataset or a production DB dump). It's included here so the pipeline is fully
self-contained and reproducible, and — deliberately — the generated data is
NOT clean: it has duplicate rows, missing values, inconsistent casing/whitespace,
and a few out-of-order timestamps. This mirrors what raw exports actually look
like and gives the transform step (etl/transform.py) real work to do.

Run: python -m etl.data_generator
"""
import os
import random
import string
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import PIPELINE

fake = Faker()
Faker.seed(PIPELINE.random_seed)
random.seed(PIPELINE.random_seed)
np.random.seed(PIPELINE.random_seed)

INDIAN_STATES = ["MH", "DL", "KA", "TN", "WB", "GJ", "UP", "RJ", "TG", "MP"]
CATEGORIES = [
    "electronics", "home_furniture", "fashion_apparel", "beauty_personal_care",
    "sports_fitness", "books_stationery", "toys_games", "grocery",
    "mobile_accessories", "kitchen_appliances",
]
PAYMENT_TYPES = ["credit_card", "debit_card", "upi", "wallet", "cod"]
ORDER_STATUSES_WEIGHTED = (
    ["delivered"] * 78 + ["shipped"] * 8 + ["canceled"] * 6 +
    ["processing"] * 5 + ["returned"] * 3
)

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 12, 31)


def _random_id(prefix: str, n: int = 12) -> str:
    return prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _random_date_in_range(start: datetime, end: datetime) -> datetime:
    """Weighted towards recent months + light seasonality bump in Oct-Dec (festive season)."""
    delta_days = (end - start).days
    day_offset = int(np.random.beta(2, 1.3) * delta_days)  # skew towards more recent dates
    d = start + timedelta(days=day_offset)
    return d


def _messify_text(value: str) -> str:
    """Randomly inject casing/whitespace inconsistencies to mimic real dirty data."""
    r = random.random()
    if r < 0.15:
        return value.upper()
    if r < 0.30:
        return f"  {value}  "
    if r < 0.35:
        return value.title()
    return value


def generate_customers(n: int) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        signup = _random_date_in_range(START_DATE, END_DATE)
        rows.append({
            "customer_id": _random_id("cust_"),
            "customer_unique_id": _random_id("cu_"),
            "signup_date": signup.date().isoformat(),
            "city": _messify_text(fake.city()),
            "state": random.choice(INDIAN_STATES),
        })
    df = pd.DataFrame(rows)
    # inject a few exact duplicate rows, and a few missing cities (real-world messiness)
    dupes = df.sample(frac=0.01, random_state=PIPELINE.random_seed)
    df = pd.concat([df, dupes], ignore_index=True)
    null_idx = df.sample(frac=0.02, random_state=PIPELINE.random_seed + 1).index
    df.loc[null_idx, "city"] = None
    return df


def generate_sellers(n: int) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rows.append({
            "seller_id": _random_id("sell_"),
            "seller_city": _messify_text(fake.city()),
            "seller_state": random.choice(INDIAN_STATES),
            "joined_date": _random_date_in_range(START_DATE, END_DATE).date().isoformat(),
        })
    return pd.DataFrame(rows)


def generate_products(n: int) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        category = random.choice(CATEGORIES)
        unit_cost = round(np.random.gamma(shape=2.0, scale=250), 2)
        margin_multiplier = np.random.uniform(1.25, 2.2)
        rows.append({
            "product_id": _random_id("prod_"),
            "product_category": _messify_text(category),
            "product_weight_g": round(np.random.gamma(2.0, 400), 2),
            "unit_cost": unit_cost,
            "list_price": round(unit_cost * margin_multiplier, 2),
        })
    return pd.DataFrame(rows)


def generate_orders_and_items(customers: pd.DataFrame, sellers: pd.DataFrame,
                               products: pd.DataFrame, n_orders: int):
    order_rows, item_rows, payment_rows, review_rows = [], [], [], []
    customer_ids = customers["customer_id"].tolist()
    seller_ids = sellers["seller_id"].tolist()
    product_records = products.to_dict("records")

    for _ in range(n_orders):
        order_id = _random_id("ord_")
        customer_id = random.choice(customer_ids)
        purchase_ts = _random_date_in_range(START_DATE, END_DATE)
        status = random.choice(ORDER_STATUSES_WEIGHTED)

        approved_ts = purchase_ts + timedelta(hours=random.randint(1, 48)) if status != "canceled" else None
        delivered_ts = None
        estimated_delivery = (purchase_ts + timedelta(days=random.randint(4, 12))).date().isoformat()
        if status == "delivered" or status == "returned":
            # occasionally deliver late (useful signal for the delivery/ops queries)
            delivery_days = random.randint(2, 18)
            delivered_ts = purchase_ts + timedelta(days=delivery_days)

        order_rows.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_status": status,
            "order_purchase_ts": purchase_ts.isoformat(sep=" "),
            "order_approved_ts": approved_ts.isoformat(sep=" ") if approved_ts else None,
            "order_delivered_ts": delivered_ts.isoformat(sep=" ") if delivered_ts else None,
            "order_estimated_delivery_date": estimated_delivery,
        })

        n_items = np.random.choice([1, 1, 1, 2, 2, 3], 1)[0]
        for seq in range(1, n_items + 1):
            product = random.choice(product_records)
            item_rows.append({
                "order_id": order_id,
                "order_item_seq": seq,
                "product_id": product["product_id"],
                "seller_id": random.choice(seller_ids),
                "price": product["list_price"],
                "freight_value": round(np.random.uniform(5, 60), 2),
            })

        order_total = sum(i["price"] + i["freight_value"] for i in item_rows if i["order_id"] == order_id)
        n_installments = random.choice([1, 1, 1, 2, 3, 6])
        payment_rows.append({
            "order_id": order_id,
            "payment_seq": 1,
            "payment_type": random.choice(PAYMENT_TYPES),
            "installments": n_installments,
            "payment_value": round(order_total, 2),
        })

        if status in ("delivered", "returned") and random.random() < 0.65:
            score_weights = [3, 5, 12, 35, 45] if status == "delivered" else [30, 30, 20, 15, 5]
            review_rows.append({
                "review_id": _random_id("rev_"),
                "order_id": order_id,
                "review_score": random.choices([1, 2, 3, 4, 5], weights=score_weights)[0],
                "review_created_ts": (delivered_ts + timedelta(days=random.randint(1, 5))).isoformat(sep=" ")
                    if delivered_ts else purchase_ts.isoformat(sep=" "),
            })

    return (pd.DataFrame(order_rows), pd.DataFrame(item_rows),
            pd.DataFrame(payment_rows), pd.DataFrame(review_rows))


def main():
    os.makedirs(PIPELINE.raw_data_dir, exist_ok=True)

    print(f"Generating {PIPELINE.n_customers} customers, {PIPELINE.n_sellers} sellers, "
          f"{PIPELINE.n_products} products, {PIPELINE.n_orders} orders ...")

    customers = generate_customers(PIPELINE.n_customers)
    sellers = generate_sellers(PIPELINE.n_sellers)
    products = generate_products(PIPELINE.n_products)
    orders, order_items, payments, reviews = generate_orders_and_items(
        customers, sellers, products, PIPELINE.n_orders
    )

    customers.to_csv(f"{PIPELINE.raw_data_dir}/customers.csv", index=False)
    sellers.to_csv(f"{PIPELINE.raw_data_dir}/sellers.csv", index=False)
    products.to_csv(f"{PIPELINE.raw_data_dir}/products.csv", index=False)
    orders.to_csv(f"{PIPELINE.raw_data_dir}/orders.csv", index=False)
    order_items.to_csv(f"{PIPELINE.raw_data_dir}/order_items.csv", index=False)
    payments.to_csv(f"{PIPELINE.raw_data_dir}/payments.csv", index=False)
    reviews.to_csv(f"{PIPELINE.raw_data_dir}/reviews.csv", index=False)

    print("Raw CSVs written to", PIPELINE.raw_data_dir)
    print({
        "customers": len(customers), "sellers": len(sellers), "products": len(products),
        "orders": len(orders), "order_items": len(order_items),
        "payments": len(payments), "reviews": len(reviews),
    })


if __name__ == "__main__":
    main()
