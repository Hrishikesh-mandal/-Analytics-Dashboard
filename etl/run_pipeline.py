"""
Pipeline orchestrator. Single entry point that runs the full
extract -> transform -> load flow with structured logging and timing,
the way you'd wire this into a scheduler (cron / Airflow) in production.

Run: python -m etl.run_pipeline
"""
import logging
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.extract import extract_all
from etl.transform import transform_all
from etl.load import load_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("run_pipeline")


def main():
    start = time.time()
    logger.info("=== ETL pipeline started ===")

    logger.info("Stage 1/3: extract")
    raw = extract_all()

    logger.info("Stage 2/3: transform")
    cleaned = transform_all(raw)

    logger.info("Stage 3/3: load")
    load_all(cleaned)

    elapsed = time.time() - start
    logger.info("=== ETL pipeline finished in %.2fs ===", elapsed)


if __name__ == "__main__":
    main()
