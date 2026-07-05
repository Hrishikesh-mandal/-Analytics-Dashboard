"""
Load stage: writes cleaned dataframes into PostgreSQL.
Loads in explicit FK-safe order (parents before children) and uses
to_sql with method="multi" in chunks for reasonable bulk-insert speed
without needing a separate COPY-based fast path for this data volume.
"""
import logging
import pandas as pd
from sqlalchemy import create_engine
from config.config import DB

logger = logging.getLogger(__name__)

# order matters: referenced tables must load before tables with FKs to them
LOAD_ORDER = ["customers", "sellers", "products", "orders", "order_items", "payments", "reviews"]


def get_engine():
    return create_engine(DB.sqlalchemy_uri)


def load_all(cleaned: dict[str, pd.DataFrame], truncate_first: bool = True) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        if truncate_first:
            # TRUNCATE ... CASCADE handles FK ordering for us on the wipe side
            conn.exec_driver_sql(
                f"TRUNCATE TABLE {', '.join(reversed(LOAD_ORDER))} RESTART IDENTITY CASCADE;"
            )
            logger.info("Truncated existing tables before load")

        for table in LOAD_ORDER:
            df = cleaned[table]
            df.to_sql(table, con=conn, if_exists="append", index=False,
                      method="multi", chunksize=1000)
            logger.info("Loaded %d rows into %s", len(df), table)
