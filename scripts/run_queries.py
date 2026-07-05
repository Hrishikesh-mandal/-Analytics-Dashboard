"""
Runs every .sql file in sql_queries/ against the database and writes results
to data/processed/<query_name>.csv. Handles files that contain multiple
statements (separated by blank-line-preceded comments) by executing each
top-level statement and keeping only the last result set per file, OR
exports each statement to its own numbered CSV — see EXPORT_MODE below.

Useful for a quick sanity-check preview of what Power BI would show,
without needing Power BI installed.

Run: python -m scripts.run_queries
"""
import os
import sys
import glob
import pandas as pd
import sqlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.load import get_engine
from config.config import PIPELINE

QUERY_DIR = "sql_queries"
OUTPUT_DIR = PIPELINE.processed_data_dir


def run_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    engine = get_engine()

    for filepath in sorted(glob.glob(f"{QUERY_DIR}/*.sql")):
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        with open(filepath) as f:
            sql_text = f.read()

        raw_statements = [s.strip() for s in sqlparse.split(sql_text) if s.strip()]
        # Strip comments before execution: psycopg2's pyformat paramstyle chokes
        # on a bare literal "%" inside a comment (e.g. "-- growth %"), so comments
        # need to go before the query reaches the DBAPI driver, not just be
        # filtered out when they're the *only* content in a chunk.
        statements = []
        for s in raw_statements:
            stripped = sqlparse.format(s, strip_comments=True).strip()
            if stripped:
                statements.append(stripped)

        with engine.connect() as conn:
            for i, stmt in enumerate(statements, start=1):
                try:
                    df = pd.read_sql_query(stmt, conn)
                except Exception as e:
                    print(f"  [skip] {base_name} statement {i}: {e}")
                    continue
                out_path = os.path.join(OUTPUT_DIR, f"{base_name}_{i}.csv")
                df.to_csv(out_path, index=False)
                print(f"  wrote {out_path}  ({len(df)} rows)")


if __name__ == "__main__":
    run_all()
