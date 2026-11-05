"""Create the SQLite dataset and scoring run required by the read-only API.

WARNING: the generator resets its target database. Run this only for a fresh
deployment database, never against a database whose scoring history matters.
"""
import os
from pathlib import Path

from src.db import DEFAULT_DB_PATH
from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores

DB_PATH = Path(os.getenv("SUPPLIER_DB_PATH", str(DEFAULT_DB_PATH)))


def main() -> None:
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        print(f"Database already exists; leaving it unchanged: {DB_PATH}")
        return
    counts = {
        "num_suppliers": int(os.getenv("SUPPLIER_NUM_SUPPLIERS", "1000")),
        "num_pos": int(os.getenv("SUPPLIER_NUM_POS", "10000")),
        "num_shipments": int(os.getenv("SUPPLIER_NUM_SHIPMENTS", "15000")),
        "num_inspections": int(os.getenv("SUPPLIER_NUM_INSPECTIONS", "20000")),
        "seed": int(os.getenv("SUPPLIER_RANDOM_SEED", "20261022")),
    }
    print(f"Generating deployment dataset at {DB_PATH}: {counts}")
    generated = generate_synthetic_data(db_path=DB_PATH, **counts)
    run_id = calculate_supplier_scores(
        as_of_date=os.getenv("SUPPLIER_AS_OF_DATE", "2026-12-31"), db_path=DB_PATH
    )
    print(f"API database ready. Counts: {generated}; scoring run: {run_id}")


if __name__ == "__main__":
    main()
