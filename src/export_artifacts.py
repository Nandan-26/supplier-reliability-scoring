import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "supplier_scoring.db"
EXPORTS = DATA / "exports"

EXPECTED_COUNTS = {
    "suppliers": 1000,
    "purchase_orders": 10000,
    "shipments": 15000,
    "delivery_events": 15000,
    "inspections": 20000,
}

SCORE_COLUMNS = [
    "delivery_score",
    "quality_score",
    "cost_score",
    "capacity_score",
    "compliance_score",
    "disruption_score",
    "final_score",
]

TIMESTAMP_CANDIDATES = [
    "created_at",
    "run_timestamp",
    "started_at",
    "completed_at",
    "created_at_utc",
    "timestamp",
]

SOURCE_FILES = [
    ROOT / "src" / "generator.py",
    ROOT / "src" / "scoring.py",
    ROOT / "src" / "export_artifacts.py",
    ROOT / "data" / "schema.sql",
    ROOT / "scripts" / "validate_full_dataset.py",
    ROOT / "scripts" / "refresh_dataset.py",
    ROOT / "data" / "DATA_DICTIONARY.md",
]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_latest_run_id(con, tables):
    if "score_runs" not in tables:
        raise RuntimeError("The score_runs table is missing.")

    run_columns = [
        row[1]
        for row in con.execute('PRAGMA table_info("score_runs")')
    ]

    if "run_id" not in run_columns:
        raise RuntimeError("The score_runs table has no run_id column.")

    timestamp_column = next(
        (name for name in TIMESTAMP_CANDIDATES if name in run_columns),
        None,
    )

    if timestamp_column:
        query = (
            f'SELECT "run_id" FROM "score_runs" '
            f'ORDER BY "{timestamp_column}" DESC, rowid DESC LIMIT 1'
        )
    else:
        query = 'SELECT "run_id" FROM "score_runs" ORDER BY rowid DESC LIMIT 1'

    row = con.execute(query).fetchone()

    if row is None:
        raise RuntimeError("No scoring runs were found.")

    return row[0], timestamp_column


def count_invalid_scores(con, column, run_id=None):
    query = (
        f'SELECT COUNT(*) FROM "supplier_scores" '
        f'WHERE "{column}" IS NOT NULL '
        f'AND ("{column}" < 0 OR "{column}" > 100)'
    )
    parameters = ()

    if run_id is not None:
        query += ' AND "run_id" = ?'
        parameters = (run_id,)

    return con.execute(query, parameters).fetchone()[0]


def main(
    db_path: str | Path = DB,
    exports_dir: str | Path = EXPORTS,
    validation_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
):
    db_path = Path(db_path)
    exports_dir = Path(exports_dir)
    validation_path = (
        Path(validation_path) if validation_path is not None
        else db_path.parent / "validation_summary.json"
    )
    manifest_path = (
        Path(manifest_path) if manifest_path is not None
        else db_path.parent / "source_manifest.json"
    )

    def display_path(path):
        try:
            return str(Path(path).relative_to(ROOT))
        except ValueError:
            return str(Path(path))

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Generate the dataset first."
        )

    exports_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = [
            list(row) for row in con.execute("PRAGMA foreign_key_check")
        ]

        tables = [
            row[0]
            for row in con.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
        ]

        row_counts = {}
        exported_files = []

        for table in tables:
            columns = [
                row[1]
                for row in con.execute(
                    f'PRAGMA table_info("{table}")'
                )
            ]

            rows = con.execute(f'SELECT * FROM "{table}"')
            csv_path = exports_dir / f"{table}.csv"

            with csv_path.open(
                "w", newline="", encoding="utf-8-sig"
            ) as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerows(rows)

            count = con.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            row_counts[table] = count
            exported_files.append(display_path(csv_path))

        expected_checks = {
            table: {
                "expected": expected,
                "actual": row_counts.get(table, 0),
                "passed": row_counts.get(table, 0) == expected,
            }
            for table, expected in EXPECTED_COUNTS.items()
        }

        # Cross-table business checks complement SQLite's structural checks.
        business_checks = {
            "cancelled_purchase_orders_have_no_shipments": con.execute("""
                SELECT COUNT(*)
                FROM shipments s
                JOIN purchase_orders po ON po.po_id = s.po_id
                WHERE po.status = 'Cancelled'
            """).fetchone()[0],
            "cancelled_purchase_orders_have_no_invoices": con.execute("""
                SELECT COUNT(*)
                FROM invoices i
                JOIN purchase_orders po ON po.po_id = i.po_id
                WHERE po.status = 'Cancelled'
            """).fetchone()[0],
            "over_shipped_po_lines": con.execute("""
                SELECT COUNT(*) FROM (
                    SELECT pl.po_id, pl.po_line_id
                    FROM po_lines pl
                    JOIN shipments s
                      ON s.po_id = pl.po_id AND s.po_line_id = pl.po_line_id
                    GROUP BY pl.po_id, pl.po_line_id, pl.ordered_qty
                    HAVING SUM(s.shipped_qty) > pl.ordered_qty + 0.000001
                )
            """).fetchone()[0],
            "delivery_quantity_over_shipment": con.execute("""
                SELECT COUNT(*) FROM (
                    SELECT s.shipment_id
                    FROM shipments s
                    JOIN delivery_events de ON de.shipment_id = s.shipment_id
                    GROUP BY s.shipment_id, s.shipped_qty
                    HAVING SUM(de.delivered_qty) > s.shipped_qty + 0.000001
                )
            """).fetchone()[0],
            "fulfilled_purchase_orders_with_short_lines": con.execute("""
                SELECT COUNT(*)
                FROM purchase_orders po
                WHERE po.status = 'Fulfilled'
                  AND EXISTS (
                    SELECT 1
                    FROM po_lines pl
                    LEFT JOIN (
                        SELECT po_id, po_line_id, SUM(shipped_qty) AS qty
                        FROM shipments GROUP BY po_id, po_line_id
                    ) sh ON sh.po_id = pl.po_id AND sh.po_line_id = pl.po_line_id
                    WHERE pl.po_id = po.po_id
                      AND COALESCE(sh.qty, 0) < pl.ordered_qty - 0.000001
                  )
            """).fetchone()[0],
            "quarantine_rows_without_reason": con.execute("""
                SELECT COUNT(*) FROM quarantine_log
                WHERE TRIM(error_reason) = ''
            """).fetchone()[0],
            "duplicate_supplier_scores_within_run": con.execute("""
                SELECT COUNT(*) FROM (
                    SELECT run_id, supplier_id
                    FROM supplier_scores
                    GROUP BY run_id, supplier_id
                    HAVING COUNT(*) > 1
                )
            """).fetchone()[0],
            "inspection_quantity_over_delivery": con.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT de.delivery_event_id
                    FROM delivery_events de
                    JOIN inspections ins ON ins.delivery_event_id = de.delivery_event_id
                    GROUP BY de.delivery_event_id, de.delivered_qty
                    HAVING SUM(ins.inspected_qty) > de.delivered_qty + 0.000001
                )
            """).fetchone()[0],
            "invoice_quantity_over_delivery": con.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT il.invoice_line_id
                    FROM invoice_lines il
                    JOIN shipments s
                      ON s.po_line_id = il.po_line_id AND s.po_id = il.po_id
                    JOIN delivery_events de ON de.shipment_id = s.shipment_id
                    GROUP BY il.invoice_line_id, il.invoiced_qty
                    HAVING il.invoiced_qty > SUM(de.delivered_qty) + 0.000001
                )
            """).fetchone()[0],
            "invoice_before_latest_delivery": con.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT i.invoice_id
                    FROM invoices i
                    JOIN shipments s ON s.po_id = i.po_id
                    JOIN delivery_events de ON de.shipment_id = s.shipment_id
                    GROUP BY i.invoice_id, i.invoice_date
                    HAVING i.invoice_date < MAX(de.actual_delivery_date)
                )
            """).fetchone()[0],
        }
        business_checks_passed = all(value == 0 for value in business_checks.values())

        score_checks = []
        latest_run_id = None
        timestamp_column = None
        latest_run_passed = False

        if "supplier_scores" in tables:
            score_table_columns = [
                row[1]
                for row in con.execute(
                    'PRAGMA table_info("supplier_scores")'
                )
            ]

            if "run_id" not in score_table_columns:
                raise RuntimeError(
                    "The supplier_scores table has no run_id column."
                )

            actual_score_columns = [
                column for column in SCORE_COLUMNS
                if column in score_table_columns
            ]

            if not actual_score_columns:
                raise RuntimeError(
                    "No recognized numeric score columns were found."
                )

            latest_run_id, timestamp_column = get_latest_run_id(
                con, tables
            )

            for column in actual_score_columns:
                historical_invalid = count_invalid_scores(con, column)
                latest_invalid = count_invalid_scores(
                    con, column, latest_run_id
                )

                score_checks.append({
                    "column": column,
                    "historical_values_outside_0_to_100": historical_invalid,
                    "latest_run_values_outside_0_to_100": latest_invalid,
                    "historical_passed": historical_invalid == 0,
                    "latest_run_passed": latest_invalid == 0,
                })

            latest_run_metadata = con.execute(
                'SELECT as_of_date FROM "score_runs" WHERE run_id = ?',
                (latest_run_id,),
            ).fetchone()
            latest_run_count = con.execute(
                'SELECT COUNT(*) FROM "supplier_scores" WHERE run_id = ?',
                (latest_run_id,),
            ).fetchone()[0]
            latest_run_unique_count = con.execute(
                'SELECT COUNT(DISTINCT supplier_id) FROM "supplier_scores" WHERE run_id = ?',
                (latest_run_id,),
            ).fetchone()[0]
            eligible_supplier_count = 0
            if latest_run_metadata:
                eligible_supplier_count = con.execute("""
                    SELECT COUNT(*) FROM suppliers
                    WHERE created_at <= ? AND system_available_at <= ?
                """, (latest_run_metadata[0], latest_run_metadata[0])).fetchone()[0]

            latest_run_passed = (
                latest_run_count == eligible_supplier_count
                and latest_run_unique_count == eligible_supplier_count
                and all(item["latest_run_passed"] for item in score_checks)
            )

        validation = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": display_path(db_path),
            "sqlite_integrity_check": integrity,
            "sqlite_integrity_passed": integrity == "ok",
            "foreign_key_violation_count": len(foreign_key_violations),
            "foreign_key_check_passed": len(foreign_key_violations) == 0,
            "expected_record_counts": expected_checks,
            "business_rule_violation_counts": business_checks,
            "business_rule_checks_passed": business_checks_passed,
            "score_range_checks": score_checks,
            "latest_run_id": latest_run_id,
            "latest_run_timestamp_column": timestamp_column,
            "latest_run_passed": latest_run_passed,
            "table_row_counts": row_counts,
            "foreign_key_violations": foreign_key_violations,
        }

        validation["historical_score_checks_passed"] = all(
            item["historical_passed"] for item in score_checks
        )

        validation["overall_passed"] = all([
            validation["sqlite_integrity_passed"],
            validation["foreign_key_check_passed"],
            all(item["passed"] for item in expected_checks.values()),
            validation["business_rule_checks_passed"],
            validation["historical_score_checks_passed"],
        ])

        validation_path.write_text(
            json.dumps(validation, indent=2),
            encoding="utf-8",
        )

        source_manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": display_path(db_path),
            "database_sha256": sha256(db_path),
            "configured_default_seed": 20261022,
            "seed_note": (
                "score_runs.random_seed records the generation seed when "
                "known; NULL means the scorer could not verify it. "
                "configured_default_seed is the generator default, not "
                "proof that an older database used that seed."
            ),
            "table_row_counts": row_counts,
            "source_files": {
                str(path.relative_to(ROOT)): sha256(path)
                for path in SOURCE_FILES if path.exists()
            },
            "csv_exports": exported_files,
            "validation_summary": str(
                display_path(validation_path)
            ),
        }

        generation_metadata_path = db_path.parent / "generation_metadata.json"
        if generation_metadata_path.exists():
            source_manifest["generation_metadata"] = display_path(
                generation_metadata_path
            )
            source_manifest["generation_metadata_sha256"] = sha256(
                generation_metadata_path
            )

        manifest_path.write_text(
            json.dumps(source_manifest, indent=2),
            encoding="utf-8",
        )

        print(f"CSV exports created: {len(exported_files)}")
        print(f"Source manifest: {manifest_path}")
        print(f"Validation summary: {validation_path}")
        print("SQLite integrity:", integrity)
        print("Foreign-key violations:", len(foreign_key_violations))
        print("Expected record counts:")

        for table, result in expected_checks.items():
            print(
                f"  {table}: {result['actual']} / "
                f"{result['expected']} — "
                f"{'PASS' if result['passed'] else 'FAIL'}"
            )

        print("\nScore validation by column:")
        for item in score_checks:
            print(
                f"  {item['column']}: "
                f"historical invalid={item['historical_values_outside_0_to_100']}, "
                f"latest-run invalid={item['latest_run_values_outside_0_to_100']}"
            )

        print("\nLatest scoring run:", latest_run_id)
        print(
            "LATEST RUN VALIDATION:",
            "PASS" if latest_run_passed else "FAIL",
        )
        print(
            "HISTORICAL SCORE VALIDATION:",
            "PASS" if validation["historical_score_checks_passed"] else "FAIL",
        )
        print(
            "OVERALL DATABASE VALIDATION:",
            "PASS" if validation["overall_passed"] else "FAIL",
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()
