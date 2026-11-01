from pathlib import Path

from src.db import get_connection
from src.generator import generate_synthetic_data

DB = Path("data/test_lifecycle_events.db")
GT = Path("data/test_lifecycle_ground_truth.json")
MAL = Path("data/test_lifecycle_malformed.json")


def test_purchase_order_status_events_capture_initial_and_fulfilled_states():
    generate_synthetic_data(
        db_path=DB, ground_truth_path=GT, malformed_path=MAL,
        num_suppliers=30, num_pos=80, num_shipments=80,
        num_inspections=80, seed=20261022,
    )
    con = get_connection(DB)
    try:
        po_count = con.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
        initial_count = con.execute(
            "SELECT COUNT(*) FROM purchase_order_status_events WHERE previous_status IS NULL"
        ).fetchone()[0]
        assert initial_count == po_count

        transitions = con.execute("""
            SELECT COUNT(*)
            FROM purchase_order_status_events
            WHERE previous_status = 'Issued' AND new_status = 'Fulfilled'
        """).fetchone()[0]
        fulfilled = con.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE status = 'Fulfilled'"
        ).fetchone()[0]
        assert transitions == fulfilled

        mismatch = con.execute("""
            SELECT COUNT(*)
            FROM purchase_orders po
            JOIN purchase_order_status_events ev ON ev.po_id = po.po_id
            WHERE ev.event_id = (
                SELECT e2.event_id FROM purchase_order_status_events e2
                WHERE e2.po_id = po.po_id
                ORDER BY e2.changed_at DESC, e2.event_id DESC LIMIT 1
            )
            AND ev.new_status <> po.status
        """).fetchone()[0]
        assert mismatch == 0
    finally:
        con.close()
        for path in (DB, GT, MAL):
            if path.exists():
                path.unlink()
