"""Validate a fresh full-size dataset and audit committed data without modifying it."""
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add the repository root when this file is executed by path from CI.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores
from src.export_artifacts import main as export_artifacts
from src.edge_cases import evaluate_edge_case_catalogue

EXPECTED = {"suppliers": 1000, "purchase_orders": 10000, "shipments": 15000, "inspections": 20000}
SCORES = ("delivery_score", "quality_score", "cost_score", "capacity_score", "compliance_score", "disruption_score", "final_score")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory(prefix="supplier-scoring-") as tmp:
        root = Path(tmp)
        db = root / "full_validation.db"
        truth_path = root / "ground_truth.json"
        malformed_path = root / "malformed_cases.json"
        generated = generate_synthetic_data(
            db_path=db, ground_truth_path=truth_path, malformed_path=malformed_path,
            num_suppliers=1000, num_pos=10000, num_shipments=15000,
            num_inspections=20000, seed=20261022,
        )
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        malformed = json.loads(malformed_path.read_text(encoding="utf-8"))
        check(len(malformed) >= 3 and all(x.get("detected_reasons") for x in malformed),
              "Malformed examples are missing validation reasons.")
        edge_cases_path = Path(__file__).resolve().parents[1] / "data" / "edge_case_fixtures.json"
        edge_cases = json.loads(edge_cases_path.read_text(encoding="utf-8"))["fixtures"]
        edge_case_report = evaluate_edge_case_catalogue(edge_cases)
        check(edge_case_report["total"] == 5 and edge_case_report["overall_passed"],
              "One or more labelled edge-case fixtures failed detection.")
        run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=db)
        export_artifacts(
            db_path=db,
            exports_dir=root / "exports",
            validation_path=root / "validation_summary.json",
            manifest_path=root / "source_manifest.json",
        )
        export_summary = json.loads(
            (root / "validation_summary.json").read_text(encoding="utf-8")
        )
        check(export_summary["overall_passed"],
              "Artifact exporter did not pass isolated full-dataset validation.")

        # Audit the active committed database separately from the fresh
        # temporary dataset. All generated reports and CSVs remain temporary.
        data_dir = Path(__file__).resolve().parents[1] / "data"
        active_dir = root / "active_database_audit"
        active_db = data_dir / "supplier_scoring.db"
        export_artifacts(
            db_path=active_db,
            exports_dir=active_dir / "exports",
            validation_path=active_dir / "validation_summary.json",
            manifest_path=active_dir / "source_manifest.json",
        )
        active_summary = json.loads(
            (active_dir / "validation_summary.json").read_text(encoding="utf-8")
        )
        check(active_summary["overall_passed"],
              "Committed active database failed full artifact validation.")

        # Audit the archived pre-refresh database without modifying it.
        historical_dir = root / "historical_audit"
        archive_databases = sorted((data_dir / "archive").glob("*/supplier_scoring.db"))
        historical_db = (
            archive_databases[0]
            if archive_databases
            else data_dir / "supplier_scoring.db"
        )
        export_artifacts(
            db_path=historical_db,
            exports_dir=historical_dir / "exports",
            validation_path=historical_dir / "validation_summary.json",
            manifest_path=historical_dir / "source_manifest.json",
        )
        historical_summary = json.loads(
            (historical_dir / "validation_summary.json").read_text(encoding="utf-8")
        )
        check(historical_summary["sqlite_integrity_passed"],
              "Committed historical database failed SQLite integrity check.")
        check(historical_summary["foreign_key_check_passed"],
              "Committed historical database has foreign-key violations.")

        con = sqlite3.connect(db)
        try:
            check(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed.")
            check(not con.execute("PRAGMA foreign_key_check").fetchall(), "Foreign-key violations found.")
            counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in (
                "suppliers", "purchase_orders", "po_lines", "shipments", "delivery_events",
                "inspections", "invoices", "invoice_lines", "risk_signals", "score_runs",
                "supplier_scores", "quarantine_log", "purchase_order_status_events"
            )}
            for table, expected in EXPECTED.items():
                check(counts[table] == expected, f"{table}: expected {expected}, got {counts[table]}")
            check(counts["supplier_scores"] == 1000, "Expected one score per supplier in the full run.")
            check(counts["purchase_order_status_events"] >= counts["purchase_orders"],
                  "Every purchase order must have an initial lifecycle event.")
            initial_events = con.execute("""
                SELECT COUNT(*) FROM purchase_order_status_events
                WHERE previous_status IS NULL
            """).fetchone()[0]
            check(initial_events == counts["purchase_orders"],
                  "Every purchase order must have exactly one initial lifecycle event.")
            fulfilled_events = con.execute("""
                SELECT COUNT(*) FROM purchase_order_status_events
                WHERE previous_status = 'Issued' AND new_status = 'Fulfilled'
            """).fetchone()[0]
            fulfilled_pos = con.execute("""
                SELECT COUNT(*) FROM purchase_orders WHERE status = 'Fulfilled'
            """).fetchone()[0]
            check(fulfilled_events == fulfilled_pos,
                  "Fulfilled purchase orders must have a matching lifecycle transition.")
            check(counts["quarantine_log"] == 8,
                  f"Expected three general malformed records plus five labelled edge cases, got {counts['quarantine_log']}.")

            queries = {
                "cancelled_po_shipments": """SELECT COUNT(*) FROM shipments s JOIN purchase_orders p ON p.po_id=s.po_id WHERE p.status='Cancelled'""",
                "cancelled_po_invoices": """SELECT COUNT(*) FROM invoices i JOIN purchase_orders p ON p.po_id=i.po_id WHERE p.status='Cancelled'""",
                "over_shipped_po_lines": """SELECT COUNT(*) FROM (SELECT pl.po_id,pl.po_line_id FROM po_lines pl JOIN shipments s ON s.po_id=pl.po_id AND s.po_line_id=pl.po_line_id GROUP BY pl.po_id,pl.po_line_id,pl.ordered_qty HAVING SUM(s.shipped_qty)>pl.ordered_qty+0.000001)""",
                "delivery_over_shipment": """SELECT COUNT(*) FROM (SELECT s.shipment_id FROM shipments s JOIN delivery_events d ON d.shipment_id=s.shipment_id GROUP BY s.shipment_id,s.shipped_qty HAVING SUM(d.delivered_qty)>s.shipped_qty+0.000001)""",
                "inspection_over_delivery": """SELECT COUNT(*) FROM (SELECT d.delivery_event_id FROM delivery_events d JOIN inspections i ON i.delivery_event_id=d.delivery_event_id GROUP BY d.delivery_event_id,d.delivered_qty HAVING SUM(i.inspected_qty)>d.delivered_qty+0.000001)""",
                "invoice_over_delivery": """SELECT COUNT(*) FROM (SELECT il.invoice_line_id FROM invoice_lines il JOIN shipments s ON s.po_id=il.po_id AND s.po_line_id=il.po_line_id JOIN delivery_events d ON d.shipment_id=s.shipment_id GROUP BY il.invoice_line_id,il.invoiced_qty HAVING il.invoiced_qty>SUM(d.delivered_qty)+0.000001)""",
                "invoice_before_latest_delivery": """SELECT COUNT(*) FROM (SELECT i.invoice_id FROM invoices i JOIN shipments s ON s.po_id=i.po_id JOIN delivery_events d ON d.shipment_id=s.shipment_id GROUP BY i.invoice_id,i.invoice_date HAVING i.invoice_date<MAX(d.actual_delivery_date))""",
                "incorrect_fulfilled_status": """SELECT COUNT(*) FROM purchase_orders p WHERE p.status='Fulfilled' AND EXISTS (SELECT 1 FROM po_lines l LEFT JOIN (SELECT po_id,po_line_id,SUM(shipped_qty) qty FROM shipments GROUP BY po_id,po_line_id) s ON s.po_id=l.po_id AND s.po_line_id=l.po_line_id WHERE l.po_id=p.po_id AND COALESCE(s.qty,0)<l.ordered_qty-0.000001)""",
            }
            violations = {name: con.execute(sql).fetchone()[0] for name, sql in queries.items()}
            for name, n in violations.items():
                check(n == 0, f"{name}: {n} violations.")

            rows = con.execute("SELECT " + ",".join(SCORES) + " FROM supplier_scores WHERE run_id=?", (run_id,)).fetchall()
            check(len(rows) == 1000, f"Expected 1000 scores, got {len(rows)}.")
            for row in rows:
                for name, value in zip(SCORES, row):
                    check(value is not None and 0 <= value <= 100, f"{name} outside 0..100: {value}")

            delivery_rows = con.execute("""SELECT p.supplier_id,SUM(CASE WHEN d.actual_delivery_date<=s.expected_delivery_date THEN 1 ELSE 0 END),COUNT(*) FROM delivery_events d JOIN shipments s ON s.shipment_id=d.shipment_id JOIN purchase_orders p ON p.po_id=s.po_id GROUP BY p.supplier_id""").fetchall()
            delivery_groups = {}
            for sid, ontime, total in delivery_rows:
                group = truth[sid]["profile"]
                acc = delivery_groups.setdefault(group, [0, 0])
                acc[0] += ontime
                acc[1] += total
            for group, (ontime, total) in delivery_groups.items():
                target = next(x["expected_on_time_rate"] for x in truth.values() if x["profile"] == group)
                observed = ontime / total
                check(abs(observed - target) <= 0.06, f"{group} delivery rate {observed:.3f}, target {target:.3f}")

            quality_rows = con.execute("""SELECT p.supplier_id,SUM(i.defective_qty),SUM(i.inspected_qty) FROM inspections i JOIN delivery_events d ON d.delivery_event_id=i.delivery_event_id JOIN shipments s ON s.shipment_id=d.shipment_id JOIN purchase_orders p ON p.po_id=s.po_id GROUP BY p.supplier_id""").fetchall()
            quality_groups = {}
            for sid, defective, inspected in quality_rows:
                group = truth[sid]["profile"]
                acc = quality_groups.setdefault(group, [0.0, 0.0])
                acc[0] += defective
                acc[1] += inspected
            for group, (defective, inspected) in quality_groups.items():
                target = next(x["expected_defect_rate"] for x in truth.values() if x["profile"] == group)
                observed = defective / inspected
                check(abs(observed - target) <= 0.04, f"{group} defect rate {observed:.3f}, target {target:.3f}")

            patterns = {
                "suppliers": ("supplier_id", r"SUP-\d{6}"),
                "purchase_orders": ("po_id", r"PO-2026-\d{6}"),
                "sites": ("site_id", r"SITE-SUP-\d{6}-\d{2}"),
                "shipments": ("shipment_id", r"SHP-2026-\d{6}"),
                "delivery_events": ("delivery_event_id", r"DEL-\d{6}"),
                "inspections": ("inspection_id", r"INS-\d{6}"),
                "invoices": ("invoice_id", r"INV-\d{5}"),
                "risk_signals": ("risk_signal_id", r"RSK-SUP-\d{6}-2026-\d{2,}"),
                "supplier_scores": ("score_id", r"SCORE-2026-\d{6}"),
            }
            for table, (column, pattern) in patterns.items():
                ids = [x[0] for x in con.execute(f"SELECT {column} FROM {table}")]
                check(all(re.fullmatch(pattern, value or "") for value in ids), f"Invalid IDs in {table}.")
        finally:
            con.close()

        print(json.dumps({
            "result": "PASS", "seed": 20261022, "run_id": run_id,
            "generated_counts": generated, "table_counts": counts,
            "business_rule_violations": violations, "score_rows_checked": len(rows),
            "artifact_exporter_overall_passed": export_summary["overall_passed"],
            "artifact_export_count": len(export_summary["table_row_counts"]),
            "active_database_audit": {
                "database_audited": str(active_db.relative_to(data_dir.parent)),
                "overall_passed": active_summary["overall_passed"],
                "business_rule_violation_counts": active_summary["business_rule_violation_counts"],
                "historical_score_checks_passed": active_summary["historical_score_checks_passed"],
                "latest_run_passed": active_summary["latest_run_passed"],
            },
            "historical_database_audit": {
                "database_audited": str(historical_db.relative_to(data_dir.parent)),
                "overall_passed": historical_summary["overall_passed"],
                "business_rule_violation_counts": historical_summary["business_rule_violation_counts"],
                "historical_score_checks_passed": historical_summary["historical_score_checks_passed"],
                "latest_run_passed": historical_summary["latest_run_passed"],
            },
            "delivery_rates_by_profile": {k: round(v[0]/v[1], 4) for k,v in delivery_groups.items()},
            "defect_rates_by_profile": {k: round(v[0]/v[1], 4) for k,v in quality_groups.items()},
            "malformed_examples_detected": len(malformed),
            "edge_case_fixture_validation": edge_case_report,
            "purchase_order_status_event_count": counts["purchase_order_status_events"],
            "database": "temporary; removed after validation",
        }, indent=2))


if __name__ == "__main__":
    main()
