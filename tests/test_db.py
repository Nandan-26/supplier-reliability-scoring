from pathlib import Path
import sqlite3
import pytest
from src.db import get_connection, initialize_database

TEST_DB_PATH = Path("data/test_supplier_scoring.db")
SCHEMA_PATH = Path("data/schema.sql")

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        initialize_database(TEST_DB_PATH, SCHEMA_PATH)
        yield
    finally:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

def test_foreign_keys_enabled_on_connection():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys;")
    result = cursor.fetchone()
    conn.close()
    assert result[0] == 1, "Foreign key enforcement is not enabled on connection!"

def test_database_tables_exist():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {
        "suppliers", "sites", "contracts", "purchase_orders", "po_lines",
        "shipments", "delivery_events", "inspections", "invoices", "invoice_lines",
        "risk_signals", "quarantine_log", "score_runs", "supplier_scores"
    }
    assert expected_tables.issubset(tables)

def test_cross_supplier_site_constraint():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-1', 'Supplier A', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO sites VALUES ('SITE-A', 'SUP-1', 'Main Plant', 'NY', 1, '2026-01-01');")
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-2', 'Supplier B', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO contracts VALUES ('CON-1', 'SUP-2', '2026-01-01', '2026-12-31', 'Net30', '2026-01-01');")

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO purchase_orders VALUES ('PO-1', 'SUP-2', 'SITE-A', 'CON-1', '2026-02-01', 'Issued', '2026-02-01');"
            )
    finally:
        conn.close()

def test_cross_supplier_contract_constraint():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-1', 'Supplier A', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-2', 'Supplier B', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO sites VALUES ('SITE-A', 'SUP-1', 'Main Plant', 'NY', 1, '2026-01-01');")
        cursor.execute("INSERT INTO sites VALUES ('SITE-B', 'SUP-2', 'Main Plant', 'CA', 1, '2026-01-01');")
        cursor.execute("INSERT INTO contracts VALUES ('CON-1', 'SUP-1', '2026-01-01', '2026-12-31', 'Net30', '2026-01-01');")

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO purchase_orders VALUES ('PO-1', 'SUP-2', 'SITE-B', 'CON-1', '2026-02-01', 'Issued', '2026-02-01');"
            )
    finally:
        conn.close()

def test_mismatched_invoice_po_line():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-1', 'Supplier A', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO sites VALUES ('SITE-A', 'SUP-1', 'Main', 'NY', 1, '2026-01-01');")
        cursor.execute("INSERT INTO contracts VALUES ('CON-1', 'SUP-1', '2026-01-01', '2026-12-31', 'Terms', '2026-01-01');")

        # Create PO-1 and PO-2
        cursor.execute("INSERT INTO purchase_orders VALUES ('PO-1', 'SUP-1', 'SITE-A', 'CON-1', '2026-01-02', 'Issued', '2026-01-02');")
        cursor.execute("INSERT INTO purchase_orders VALUES ('PO-2', 'SUP-1', 'SITE-A', 'CON-1', '2026-01-02', 'Issued', '2026-01-02');")

        cursor.execute("INSERT INTO po_lines VALUES ('LINE-1', 'PO-1', 'ITEM-X', 100, 10.0, '2026-01-10', '2026-01-02');")

        # Invoice created for PO-2
        cursor.execute("INSERT INTO invoices VALUES ('INV-1', 'PO-2', '2026-01-15', 'Matched', '2026-01-15');")

        # Attempt to link Invoice (for PO-2) to PO-1's line (Should fail due to composite FK)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO invoice_lines VALUES ('IL-1', 'INV-1', 'PO-2', 'LINE-1', 100, 10.0, '2026-01-15');"
            )
    finally:
        conn.close()

def test_inspection_quantity_constraint():
    conn = get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO suppliers VALUES ('SUP-1', 'Supplier A', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT INTO sites VALUES ('SITE-A', 'SUP-1', 'Main', 'NY', 1, '2026-01-01');")
        cursor.execute("INSERT INTO contracts VALUES ('CON-1', 'SUP-1', '2026-01-01', '2026-12-31', 'Terms', '2026-01-01');")
        cursor.execute("INSERT INTO purchase_orders VALUES ('PO-1', 'SUP-1', 'SITE-A', 'CON-1', '2026-01-02', 'Issued', '2026-01-02');")
        cursor.execute("INSERT INTO po_lines VALUES ('LINE-1', 'PO-1', 'ITEM-X', 100, 10.0, '2026-01-10', '2026-01-02');")
        cursor.execute("INSERT INTO shipments VALUES ('SHP-1', 'LINE-1', 'PO-1', 100, '2026-01-05', '2026-01-09', '2026-01-05');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-1', 'SHP-1', '2026-01-09', 100, 'OK', '2026-01-09');")

        # Attempt inspection where defective_qty > inspected_qty
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO inspections VALUES ('INS-1', 'DEL-1', '2026-01-10', 50, 60, 'Failed', '2026-01-10');"
            )
    finally:
        conn.close()
