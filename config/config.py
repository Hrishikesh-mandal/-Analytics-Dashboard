"""
Centralized configuration for the e-commerce analytics pipeline.
Reads DB credentials and pipeline settings from environment variables
so no secrets are hard-coded in source. Falls back to sane local
defaults for development.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # loads .env if present; no-op in prod where env vars are set directly


@dataclass(frozen=True)
class DBConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "ecommerce_analytics")
    user: str = os.getenv("DB_USER", "analyst")
    password: str = os.getenv("DB_PASSWORD", "analyst_pass")

    @property
    def sqlalchemy_uri(self) -> str:
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class PipelineConfig:
    raw_data_dir: str = os.getenv("RAW_DATA_DIR", "data/raw")
    processed_data_dir: str = os.getenv("PROCESSED_DATA_DIR", "data/processed")
    n_customers: int = int(os.getenv("N_CUSTOMERS", "5000"))
    n_orders: int = int(os.getenv("N_ORDERS", "20000"))
    n_products: int = int(os.getenv("N_PRODUCTS", "800"))
    n_sellers: int = int(os.getenv("N_SELLERS", "150"))
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))


DB = DBConfig()
PIPELINE = PipelineConfig()
