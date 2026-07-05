"""
Extract stage: reads raw CSV exports into pandas DataFrames.
Kept deliberately dumb — no cleaning logic here, that belongs in transform.py.
Separation matters so each stage is independently testable.
"""
import logging
import os
import pandas as pd
from config.config import PIPELINE

logger = logging.getLogger(__name__)

RAW_FILES = {
    "customers": "customers.csv",
    "sellers": "sellers.csv",
    "products": "products.csv",
    "orders": "orders.csv",
    "order_items": "order_items.csv",
    "payments": "payments.csv",
    "reviews": "reviews.csv",
}


def extract_all(raw_dir: str = None) -> dict[str, pd.DataFrame]:
    raw_dir = raw_dir or PIPELINE.raw_data_dir
    dataframes = {}
    for key, filename in RAW_FILES.items():
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Expected raw file not found: {path}. "
                f"Run `python -m etl.data_generator` first."
            )
        df = pd.read_csv(path)
        logger.info("Extracted %s: %d rows", key, len(df))
        dataframes[key] = df
    return dataframes
