from pathlib import Path
import json
import sqlite3
import pytest
from src.db import get_connection, initialize_database
from src.generator import generate_synthetic_data, validate_payload

TEST_DB_PATH = Path("data/test_generator.db")
TEST_GT_PATH = Path("data/test_ground_truth.json")
TEST_MAL_PATH = Path("data/test_malformed.json")

@pytest.fixture(autouse=True)
def cleanup():
    yield
    for p in [TEST_DB_PATH, TEST_GT_PATH, TEST_MAL_PATH]:
        if p.exists():
            try:
                p.unlink()
            except PermissionError:
                pass

def test_exact_requested_counts():
    counts = generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=40, num_pos=100, num_shipments=150, num_inspections=200, seed=42
    )
    assert counts["suppliers"] == 40
    assert counts["purchase_orders"] == 100
    assert counts["shipments"] == 150
    assert counts["inspections"] == 200


def test_risk_signal_provenance_and_supplier_scoped_ids():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH, num_suppliers=40,
        num_pos=100, num_shipments=150, num_inspections=200, seed=42
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        rows = conn.execute(
            "SELECT risk_signal_id, supplier_id, source FROM risk_signals"
        ).fetchall()
    finally:
        conn.close()
    for signal_id, supplier_id, source in rows:
        assert signal_id.startswith(f"RSK-{supplier_id}-2026-")
        assert source == "synthetic_generator"

def test_repeated_generation_runs_safe():
    # Run twice to verify safe reset and foreign key preservation
    counts1 = generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=20, num_pos=50, num_shipments=50, num_inspections=50, seed=42
    )
    counts2 = generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=20, num_pos=50, num_shipments=50, num_inspections=50, seed=42
    )
    assert counts1 == counts2

def test_zero_or_negative_config_raises_error():
    with pytest.raises(ValueError):
        generate_synthetic_data(
            db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
            num_suppliers=0, num_pos=10, num_shipments=10, num_inspections=10
        )

def test_shipment_to_po_line_consistency():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=20, num_pos=50, num_shipments=50, num_inspections=50, seed=42
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM shipments s
            JOIN po_lines pl ON s.po_line_id = pl.po_line_id AND s.po_id = pl.po_id
        """)
        matched = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM shipments;")
        total = cursor.fetchone()[0]
    finally:
        conn.close()
    assert matched == total

def test_reproducibility_across_all_tables_and_files():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=20, num_pos=50, num_shipments=50, num_inspections=50, seed=99
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT supplier_id, name FROM suppliers ORDER BY supplier_id;")
        run1_suppliers = cursor.fetchall()
        cursor.execute("SELECT shipment_id, shipped_qty FROM shipments ORDER BY shipment_id;")
        run1_shipments = cursor.fetchall()
    finally:
        conn.close()

    with open(TEST_GT_PATH, "r", encoding="utf-8") as f:
        run1_gt = json.load(f)

    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=20, num_pos=50, num_shipments=50, num_inspections=50, seed=99
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT supplier_id, name FROM suppliers ORDER BY supplier_id;")
        run2_suppliers = cursor.fetchall()
        cursor.execute("SELECT shipment_id, shipped_qty FROM shipments ORDER BY shipment_id;")
        run2_shipments = cursor.fetchall()
    finally:
        conn.close()

    with open(TEST_GT_PATH, "r", encoding="utf-8") as f:
        run2_gt = json.load(f)

    assert run1_suppliers == run2_suppliers
    assert run1_shipments == run2_shipments
    assert run1_gt == run2_gt

def test_supplier_profile_behavioral_differences():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH, malformed_path=TEST_MAL_PATH,
        num_suppliers=100, num_pos=300, num_shipments=300, num_inspections=300, seed=42
    )
    with open(TEST_GT_PATH, "r", encoding="utf-8") as f:
        gt = json.load(f)

    reliable_sups = [sup for sup, data in gt.items() if data["profile"] == "reliable"]
    quality_sups = [sup for sup, data in gt.items() if data["profile"] == "quality_issues"]

    conn = get_connection(TEST_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT po.supplier_id, AVG(ins.defective_qty / ins.inspected_qty) as avg_defect_rate
            FROM inspections ins
            JOIN delivery_events de ON ins.delivery_event_id = de.delivery_event_id
            JOIN shipments s ON de.shipment_id = s.shipment_id
            JOIN purchase_orders po ON s.po_id = po.po_id
            GROUP BY po.supplier_id
        """)
        supplier_defect_rates = {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()

    if reliable_sups and quality_sups:
        avg_reliable_defects = sum(supplier_defect_rates.get(s, 0) for s in reliable_sups) / len(reliable_sups)
        avg_quality_defects = sum(supplier_defect_rates.get(s, 0) for s in quality_sups) / len(quality_sups)
        assert avg_quality_defects > avg_reliable_defects

def test_malformed_case_db_detection():
    initialize_database(TEST_DB_PATH)
    conn = get_connection(TEST_DB_PATH)
    try:
        cursor = conn.cursor()
        payload = {"shipment_id": "MAL-99", "po_line_id": "NON-EXISTENT", "po_id": "NON-EXISTENT", "shipped_qty": 100, "dispatch_date": "2026-05-01", "expected_delivery_date": "2026-04-01"}
        errors = validate_payload(cursor, "shipments", payload)
    finally:
        conn.close()

    assert len(errors) >= 2
    assert any("Orphaned" in err for err in errors)
    assert any("Impossible date" in err for err in errors)


def test_cancelled_purchase_orders_have_no_shipments():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH, num_suppliers=40, num_pos=200,
        num_shipments=100, num_inspections=100, seed=314
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        cancelled_shipments = conn.execute("""
            SELECT COUNT(*)
            FROM shipments s
            JOIN purchase_orders po ON po.po_id = s.po_id
            WHERE po.status = 'Cancelled';
        """).fetchone()[0]
    finally:
        conn.close()
    assert cancelled_shipments == 0


def test_inspection_lots_do_not_exceed_delivered_quantity():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH, num_suppliers=40, num_pos=200,
        num_shipments=100, num_inspections=200, seed=2718
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        inspection_count = conn.execute(
            "SELECT COUNT(*) FROM inspections;"
        ).fetchone()[0]
        violations = conn.execute("""
            SELECT de.delivery_event_id
            FROM delivery_events de
            JOIN inspections i ON i.delivery_event_id = de.delivery_event_id
            GROUP BY de.delivery_event_id, de.delivered_qty
            HAVING SUM(i.inspected_qty) > de.delivered_qty + 0.000001;
        """).fetchall()
    finally:
        conn.close()
    assert inspection_count == 200
    assert violations == []


def test_invoice_lines_are_limited_to_delivered_quantities_and_dates():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH, num_suppliers=40, num_pos=200,
        num_shipments=100, num_inspections=100, seed=1618
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        cancelled_invoice_count = conn.execute("""
            SELECT COUNT(*)
            FROM invoices i
            JOIN purchase_orders po ON po.po_id = i.po_id
            WHERE po.status = 'Cancelled';
        """).fetchone()[0]
        quantity_violations = conn.execute("""
            SELECT il.invoice_line_id
            FROM invoice_lines il
            JOIN shipments s
              ON s.po_line_id = il.po_line_id AND s.po_id = il.po_id
            JOIN delivery_events de ON de.shipment_id = s.shipment_id
            GROUP BY il.invoice_line_id, il.invoiced_qty
            HAVING il.invoiced_qty > SUM(de.delivered_qty) + 0.000001;
        """).fetchall()
        date_violations = conn.execute("""
            SELECT i.invoice_id
            FROM invoices i
            JOIN shipments s ON s.po_id = i.po_id
            JOIN delivery_events de ON de.shipment_id = s.shipment_id
            GROUP BY i.invoice_id, i.invoice_date
            HAVING i.invoice_date < MAX(de.actual_delivery_date);
        """).fetchall()
    finally:
        conn.close()
    assert cancelled_invoice_count == 0
    assert quantity_violations == []
    assert date_violations == []


def test_detected_malformed_records_are_persisted_in_quarantine():
    generate_synthetic_data(
        db_path=TEST_DB_PATH, ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH, num_suppliers=20, num_pos=50,
        num_shipments=50, num_inspections=50, seed=4242
    )
    with open(TEST_MAL_PATH, "r", encoding="utf-8") as stream:
        malformed = json.load(stream)

    conn = get_connection(TEST_DB_PATH)
    try:
        rows = conn.execute("""
            SELECT source_table, raw_payload, error_reason
            FROM quarantine_log ORDER BY quarantine_id;
        """).fetchall()
    finally:
        conn.close()

    assert len(rows) == len(malformed) == 3
    assert all(row[2] for row in rows)
    assert all(json.loads(row[1]) for row in rows)
