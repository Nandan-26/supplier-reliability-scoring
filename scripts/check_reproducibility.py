"""Run generation twice in isolated databases and compare every table/export checksum."""
import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator import generate_synthetic_data


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(db_path, export_dir):
    export_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        tables = [row[0] for row in con.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)]
        result = {}
        for table in tables:
            columns = [row[1] for row in con.execute(f'PRAGMA table_info("{table}")')]
            order = ", ".join(f'"{column}"' for column in columns)
            rows = con.execute(f'SELECT * FROM "{table}" ORDER BY {order}').fetchall()
            path = export_dir / f"{table}.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(columns)
                writer.writerows(rows)
            result[table] = {
                "row_count": len(rows),
                "csv_sha256": digest(path),
            }
        return result
    finally:
        con.close()


def run_check(output_path, seed, suppliers, pos, shipments, inspections):
    with tempfile.TemporaryDirectory(prefix="supplier-repro-") as tmp:
        root = Path(tmp)
        runs = []
        for index in (1, 2):
            folder = root / f"run_{index}"
            folder.mkdir()
            db, truth, malformed = folder / "data.db", folder / "ground_truth.json", folder / "malformed_cases.json"
            generate_synthetic_data(
                db_path=db, ground_truth_path=truth, malformed_path=malformed,
                num_suppliers=suppliers, num_pos=pos,
                num_shipments=shipments, num_inspections=inspections, seed=seed,
            )
            table_snapshot = snapshot(db, folder / "exports")
            runs.append({
                "tables": table_snapshot,
                "ground_truth_sha256": digest(truth),
                "malformed_cases_sha256": digest(malformed),
            })

        table_names = sorted(set(runs[0]["tables"]) | set(runs[1]["tables"]))
        differences = []
        for table in table_names:
            left, right = runs[0]["tables"].get(table), runs[1]["tables"].get(table)
            if left != right:
                differences.append({"table": table, "run_1": left, "run_2": right})
        for field in ("ground_truth_sha256", "malformed_cases_sha256"):
            if runs[0][field] != runs[1][field]:
                differences.append({"artifact": field, "run_1": runs[0][field], "run_2": runs[1][field]})

        report = {
            "seed": seed,
            "configuration": {
                "suppliers": suppliers, "purchase_orders": pos,
                "shipments": shipments, "inspections": inspections,
            },
            "tables_compared": len(table_names),
            "csv_exports_compared": len(table_names) * 1,
            "ground_truth_compared": True,
            "malformed_cases_compared": True,
            "differences": differences,
            "overall_passed": not differences,
            "comparison_method": "SHA-256 of deterministic ordered CSV exports and JSON artifacts; row counts included per table",
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        if differences:
            raise SystemExit(1)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--suppliers", type=int, default=1000)
    parser.add_argument("--pos", type=int, default=10000)
    parser.add_argument("--shipments", type=int, default=15000)
    parser.add_argument("--inspections", type=int, default=20000)
    parser.add_argument("--output", default="data/reproducibility_report.json")
    args = parser.parse_args()
    run_check(args.output, args.seed, args.suppliers, args.pos, args.shipments, args.inspections)
