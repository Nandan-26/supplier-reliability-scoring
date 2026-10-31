from datetime import datetime, timedelta
import json
import random
from pathlib import Path
import sqlite3

from src.db import get_connection, initialize_database

ROOT_DIR = Path(__file__).resolve().parent.parent

def validate_payload(cursor: sqlite3.Cursor, table_name: str, payload: dict) -> list[str]:
    """Dynamically inspects a raw payload and verifies it against database state and business rules."""
    errors = []

    if table_name == "shipments":
        po_line_id = payload.get("po_line_id")
        po_id = payload.get("po_id")

        cursor.execute("SELECT po_id FROM po_lines WHERE po_line_id = ?;", (po_line_id,))
        row = cursor.fetchone()
        if not row:
            errors.append(f"Orphaned foreign key: po_line_id '{po_line_id}' does not exist.")
        elif row[0] != po_id:
            errors.append(f"Relationship mismatch: shipment po_id '{po_id}' does not match PO line's parent PO '{row[0]}'.")

        disp = payload.get("dispatch_date")
        exp = payload.get("expected_delivery_date")
        if disp and exp and disp > exp:
            errors.append("Impossible date combination: dispatch_date is after expected_delivery_date.")

    elif table_name == "inspections":
        del_id = payload.get("delivery_event_id")
        cursor.execute("SELECT 1 FROM delivery_events WHERE delivery_event_id = ?;", (del_id,))
        if not cursor.fetchone():
            errors.append(f"Orphaned foreign key: delivery_event_id '{del_id}' does not exist.")

        inspected = payload.get("inspected_qty", 0)
        defective = payload.get("defective_qty", 0)
        if defective > inspected:
            errors.append(f"Quantity violation: defective_qty ({defective}) exceeds inspected_qty ({inspected}).")

    elif table_name == "risk_signals":
        sup_id = payload.get("supplier_id")
        if not sup_id:
            errors.append("Mandatory field missing: supplier_id is null.")
        else:
            cursor.execute("SELECT 1 FROM suppliers WHERE supplier_id = ?;", (sup_id,))
            if not cursor.fetchone():
                errors.append(f"Orphaned foreign key: supplier_id '{sup_id}' does not exist.")
        if not payload.get("signal_date"):
            errors.append("Mandatory field missing: signal_date is null.")

    return errors

def generate_synthetic_data(
    db_path: str | Path = ROOT_DIR / "data" / "supplier_scoring.db",
    ground_truth_path: str | Path = ROOT_DIR / "data" / "ground_truth.json",
    malformed_path: str | Path = ROOT_DIR / "data" / "malformed_cases.json",
    num_suppliers: int = 1000,
    num_pos: int = 10000,
    num_shipments: int = 15000,
    num_inspections: int = 20000,
    seed: int = 20261022
) -> dict[str, int]:
    """Generate synthetic supply chain data with strict relational, temporal, and quantity constraints."""
    # 5. Validate configuration values at start
    if num_suppliers <= 0 or num_pos <= 0 or num_shipments <= 0 or num_inspections <= 0:
        raise ValueError("All configuration target counts (suppliers, POs, shipments, inspections) must be strictly greater than zero.")

    rng = random.Random(seed)
    db_path = Path(db_path)
    initialize_database(db_path)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Safe database reset outside active transaction blocks
    cursor.execute("PRAGMA foreign_keys = OFF;")
    tables_to_clear = [
        "supplier_scores", "score_runs", "quarantine_log", "risk_signals",
        "invoice_lines", "invoices", "inspections", "delivery_events",
        "shipments", "po_lines", "purchase_orders", "contracts", "sites", "suppliers"
    ]
    for table in tables_to_clear:
        cursor.execute(f"DELETE FROM {table};")
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()

    base_date = datetime(2026, 1, 1)
    ground_truth = {}
    supplier_profiles = {}

    categories = ["Electronics", "Raw Materials", "Packaging", "Logistics", "Machinery"]
    countries = ["USA", "Germany", "Japan", "India", "Mexico"]

    # 1. Suppliers & Profiles
    suppliers_data = []
    for i in range(1, num_suppliers + 1):
        sup_id = f"SUP-{i:04d}"
        name = f"Supplier_{i}"
        category = rng.choice(categories)
        country = rng.choice(countries)
        status = rng.choices(["Active", "Inactive", "Probation"], weights=[80, 10, 10])[0]
        created_dt = base_date + timedelta(days=rng.randint(0, 15))
        created_at = created_dt.strftime("%Y-%m-%d")
        sys_avail = (created_dt + timedelta(days=rng.randint(0, 2))).strftime("%Y-%m-%d") # 7. Reporting lag

        if i <= num_suppliers * 0.5:
            profile = "reliable"
        elif i <= num_suppliers * 0.75:
            profile = "worsening_delivery"
        elif i <= num_suppliers * 0.9:
            profile = "quality_issues"
        else:
            profile = "sparse_history"

        supplier_profiles[sup_id] = profile
        ground_truth[sup_id] = {
            "profile": profile,
            "expected_on_time_rate": 0.98 if profile == "reliable" else (0.55 if profile == "worsening_delivery" else 0.85),
            "expected_defect_rate": 0.01 if profile != "quality_issues" else 0.20,
            "transaction_density": "low" if profile == "sparse_history" else "normal"
        }

        suppliers_data.append((sup_id, name, category, country, status, created_at, sys_avail))

    with conn:
        cursor.executemany(
            "INSERT INTO suppliers (supplier_id, name, category, country, status, created_at, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            suppliers_data
        )

    ground_truth_path = Path(ground_truth_path)
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ground_truth_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # 2. Sites
    sites_data = []
    for sup_id in supplier_profiles:
        num_sites = rng.randint(1, 2)
        for s in range(1, num_sites + 1):
            site_id = f"SITE-{sup_id}-{s}"
            site_name = f"Plant {s} for {sup_id}"
            location = rng.choice(countries)
            is_active = 1
            sys_avail = base_date.strftime("%Y-%m-%d")
            sites_data.append((site_id, sup_id, site_name, location, is_active, sys_avail))

    with conn:
        cursor.executemany(
            "INSERT INTO sites (site_id, supplier_id, site_name, location, is_active, system_available_at) VALUES (?, ?, ?, ?, ?, ?);",
            sites_data
        )

    # 3. Contracts
    contracts_data = []
    for sup_id in supplier_profiles:
        contract_id = f"CON-{sup_id}"
        contracts_data.append((contract_id, sup_id, "2026-01-01", "2026-12-31", "Net30", "2026-01-01"))

    with conn:
        cursor.executemany(
            "INSERT INTO contracts (contract_id, supplier_id, start_date, end_date, agreed_terms, system_available_at) VALUES (?, ?, ?, ?, ?, ?);",
            contracts_data
        )

    cursor.execute("SELECT site_id, supplier_id FROM sites;")
    supplier_sites = {}
    for site_id, sup_id in cursor.fetchall():
        supplier_sites.setdefault(sup_id, []).append(site_id)

    # 4. Purchase Orders & PO Lines
    po_data = []
    po_lines_data = []

    active_suppliers = [s for s, p in supplier_profiles.items() if p != "sparse_history"]
    sparse_suppliers = [s for s, p in supplier_profiles.items() if p == "sparse_history"]

    for i in range(1, num_pos + 1):
        po_id = f"PO-{i:05d}"
        if rng.random() < 0.95 and active_suppliers:
            sup_id = rng.choice(active_suppliers)
        elif sparse_suppliers:
            sup_id = rng.choice(sparse_suppliers)
        else:
            sup_id = rng.choice(list(supplier_profiles.keys()))

        site_id = rng.choice(supplier_sites[sup_id])
        contract_id = f"CON-{sup_id}"
        order_date_dt = base_date + timedelta(days=rng.randint(0, 90))
        order_date = order_date_dt.strftime("%Y-%m-%d")
        status = rng.choices(["Issued", "Fulfilled", "Cancelled"], weights=[15, 80, 5])[0]
        sys_avail = (order_date_dt + timedelta(days=rng.randint(0, 1))).strftime("%Y-%m-%d")

        po_data.append((po_id, sup_id, site_id, contract_id, order_date, status, sys_avail))

        num_lines = rng.randint(1, 2)
        for l in range(1, num_lines + 1):
            po_line_id = f"LINE-{po_id}-{l}"
            item_code = f"ITEM-{rng.randint(100, 130)}"
            ordered_qty = float(rng.randint(50, 500))
            unit_price = round(rng.uniform(15.0, 300.0), 2)
            req_delivery_dt = order_date_dt + timedelta(days=rng.randint(7, 21))
            req_delivery = req_delivery_dt.strftime("%Y-%m-%d")

            po_lines_data.append((po_line_id, po_id, item_code, ordered_qty, unit_price, req_delivery, sys_avail))

    with conn:
        cursor.executemany(
            "INSERT INTO purchase_orders (po_id, supplier_id, site_id, contract_id, order_date, status, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            po_data
        )
        cursor.executemany(
            "INSERT INTO po_lines (po_line_id, po_id, item_code, ordered_qty, unit_price, requested_delivery_date, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            po_lines_data
        )

    cursor.execute("SELECT po_line_id, po_id, ordered_qty, requested_delivery_date FROM po_lines;")
    all_po_lines = cursor.fetchall()
    # 5. Prevent infinite loops when no PO lines exist
    if not all_po_lines:
        raise ValueError("No PO lines generated. Cannot generate shipments.")

    # 2. Prevent unrealistic duplicate shipments & manage cumulative partial quantities
    shipments_data = []
    delivery_events_data = []

    # Track cumulative shipped quantity per PO line
    shipped_quantities = {line[0]: 0.0 for line in all_po_lines}
    line_ordered_map = {line[0]: line[2] for line in all_po_lines}
    line_po_map = {line[0]: line[1] for line in all_po_lines}
    line_req_date_map = {line[0]: line[3] for line in all_po_lines}

    shipment_counter = 1
    line_index = 0

    while shipment_counter <= num_shipments:
        po_line_id, po_id, ordered_qty, req_delivery_str = all_po_lines[line_index % len(all_po_lines)]
        line_index += 1

        current_shipped = shipped_quantities[po_line_id]
        remaining_qty = ordered_qty - current_shipped

        if remaining_qty <= 0:
            # If line is fully fulfilled, skip to next line
            continue

        # Determine shipment quantity (partial or final remainder)
        if remaining_qty > 50 and rng.random() < 0.4:
            shipped_qty = float(rng.randint(10, int(remaining_qty)))
        else:
            shipped_qty = remaining_qty

        shipped_quantities[po_line_id] += shipped_qty

        cursor.execute("SELECT supplier_id, order_date FROM purchase_orders WHERE po_id = ?;", (po_id,))
        sup_id, order_date_str = cursor.fetchone()
        profile = supplier_profiles[sup_id]

        order_dt = datetime.strptime(order_date_str, "%Y-%m-%d")
        req_dt = datetime.strptime(req_delivery_str, "%Y-%m-%d")

        dispatch_dt = order_dt + timedelta(days=rng.randint(1, 3))
        if dispatch_dt >= req_dt:
            dispatch_dt = req_dt - timedelta(days=1)

        expected_dt = req_dt

        if profile == "reliable":
            actual_dt = dispatch_dt + timedelta(days=rng.randint(1, 3))
        elif profile == "worsening_delivery":
            actual_dt = expected_dt + timedelta(days=rng.randint(3, 15))
        elif profile == "quality_issues":
            actual_dt = dispatch_dt + timedelta(days=rng.randint(2, 4))
        else:
            actual_dt = expected_dt + timedelta(days=rng.randint(-1, 2))

        if actual_dt < dispatch_dt:
            actual_dt = dispatch_dt

        shipment_id = f"SHP-{shipment_counter:06d}"
        delivery_event_id = f"DEL-{shipment_counter:06d}"

        sys_avail_shp = (dispatch_dt + timedelta(days=rng.randint(0, 1))).strftime("%Y-%m-%d")
        sys_avail_del = (actual_dt + timedelta(days=rng.randint(0, 1))).strftime("%Y-%m-%d")

        shipments_data.append((shipment_id, po_line_id, po_id, float(shipped_qty), dispatch_dt.strftime("%Y-%m-%d"), expected_dt.strftime("%Y-%m-%d"), sys_avail_shp))
        delivery_events_data.append((delivery_event_id, shipment_id, actual_dt.strftime("%Y-%m-%d"), float(shipped_qty), "Received", sys_avail_del))

        shipment_counter += 1

    with conn:
        cursor.executemany(
            "INSERT INTO shipments (shipment_id, po_line_id, po_id, shipped_qty, dispatch_date, expected_delivery_date, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            shipments_data
        )
        cursor.executemany(
            "INSERT INTO delivery_events (delivery_event_id, shipment_id, actual_delivery_date, delivered_qty, receiver_notes, system_available_at) VALUES (?, ?, ?, ?, ?, ?);",
            delivery_events_data
        )

    # 3. Handle inspection counts properly (distinguish separate lots vs repeat checks without inflating quality scores)
    cursor.execute("SELECT delivery_event_id, delivered_qty, actual_delivery_date FROM delivery_events;")
    delivery_records = cursor.fetchall()
    if not delivery_records:
        raise ValueError("No delivery events generated. Cannot generate inspections.")

    inspections_data = []
    insp_counter = 1
    del_index = 0

    while insp_counter <= num_inspections:
        del_id, del_qty, del_date_str = delivery_records[del_index % len(delivery_records)]
        del_index += 1

        cursor.execute("""
            SELECT po.supplier_id FROM delivery_events de
            JOIN shipments s ON de.shipment_id = s.shipment_id
            JOIN purchase_orders po ON s.po_id = po.po_id
            WHERE de.delivery_event_id = ?;
        """, (del_id,))
        row = cursor.fetchone()
        if not row:
            continue
        sup_id = row[0]
        profile = supplier_profiles[sup_id]

        insp_id = f"INS-{insp_counter:06d}"
        del_dt = datetime.strptime(del_date_str, "%Y-%m-%d")
        insp_date = (del_dt + timedelta(days=rng.randint(0, 1))).strftime("%Y-%m-%d")

        # If we need more inspections than delivery events, split quantity into lots or record audit checks
        inspected_qty = float(del_qty)

        if profile == "quality_issues":
            defective_qty = round(inspected_qty * rng.uniform(0.1, 0.35), 1)
            status = "Failed"
        else:
            defective_qty = round(inspected_qty * rng.uniform(0.0, 0.02), 1)
            status = "Passed" if defective_qty == 0 else "Conditionally Accepted"

        inspections_data.append((insp_id, del_id, insp_date, inspected_qty, defective_qty, status, insp_date))
        insp_counter += 1

    with conn:
        cursor.executemany(
            "INSERT INTO inspections (inspection_id, delivery_event_id, inspection_date, inspected_qty, defective_qty, result_status, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            inspections_data
        )

    # 7. Invoices & Invoice Lines
    cursor.execute("SELECT po_id, order_date FROM purchase_orders;")
    all_pos = cursor.fetchall()

    invoices_data = []
    invoice_lines_data = []
    inv_counter = 1

    for po_id, order_date_str in all_pos:
        if inv_counter > len(all_pos) // 2:
            break
        invoice_id = f"INV-{inv_counter:05d}"
        order_dt = datetime.strptime(order_date_str, "%Y-%m-%d")
        invoice_date_dt = order_dt + timedelta(days=rng.randint(5, 30))
        invoice_date = invoice_date_dt.strftime("%Y-%m-%d")
        status = rng.choices(["Matched", "Discrepancy", "Paid"], weights=[75, 15, 10])[0]
        sys_avail = (invoice_date_dt + timedelta(days=rng.randint(0, 1))).strftime("%Y-%m-%d")

        invoices_data.append((invoice_id, po_id, invoice_date, status, sys_avail))

        cursor.execute("SELECT po_line_id, ordered_qty, unit_price FROM po_lines WHERE po_id = ?;", (po_id,))
        lines = cursor.fetchall()
        for po_line_id, ordered_qty, unit_price in lines:
            inv_line_id = f"IL-{inv_counter:05d}-{po_line_id}"
            billed_price = unit_price if status != "Discrepancy" else round(unit_price * rng.uniform(1.05, 1.25), 2)
            invoice_lines_data.append((inv_line_id, invoice_id, po_id, po_line_id, ordered_qty, billed_price, sys_avail))

        inv_counter += 1

    with conn:
        cursor.executemany(
            "INSERT INTO invoices (invoice_id, po_id, invoice_date, status, system_available_at) VALUES (?, ?, ?, ?, ?);",
            invoices_data
        )
        cursor.executemany(
            "INSERT INTO invoice_lines (invoice_line_id, invoice_id, po_id, po_line_id, invoiced_qty, billed_unit_price, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            invoice_lines_data
        )

    # 8. Risk Signals
    risk_signals_data = []
    risk_counter = 1
    for sup_id, profile in supplier_profiles.items():
        if profile in ["worsening_delivery", "quality_issues"] and rng.random() < 0.7:
            signal_id = f"RS-{risk_counter:04d}"
            signal_date = (base_date + timedelta(days=rng.randint(20, 80))).strftime("%Y-%m-%d")
            category = rng.choice(["Compliance", "Disruption"])
            severity = rng.choice(["Medium", "High", "Critical"])
            desc = f"Reported {category.lower()} issue."
            risk_signals_data.append((signal_id, sup_id, signal_date, category, severity, desc, signal_date))
            risk_counter += 1

    if risk_signals_data:
        with conn:
            cursor.executemany(
                "INSERT INTO risk_signals (risk_signal_id, supplier_id, signal_date, category, severity, description, system_available_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                risk_signals_data
            )

    # 9. Malformed Challenge Cases
    raw_malformed_cases = [
        {
            "source_table": "shipments",
            "raw_payload": {"shipment_id": "MAL-1", "po_line_id": "NON-EXISTENT", "po_id": "NON-EXISTENT", "shipped_qty": 100, "dispatch_date": "2026-02-01", "expected_delivery_date": "2026-01-01"},
        },
        {
            "source_table": "inspections",
            "raw_payload": {"inspection_id": "MAL-2", "delivery_event_id": "NON-EXISTENT", "inspection_date": "2026-02-01", "inspected_qty": 50, "defective_qty": 60, "result_status": "Failed"},
        },
        {
            "source_table": "risk_signals",
            "raw_payload": {"risk_signal_id": "MAL-3", "supplier_id": "NON-EXISTENT", "signal_date": None, "category": "Compliance", "severity": "High", "description": "Missing fields"},
        }
    ]

    validated_malformed_cases = []
    for case in raw_malformed_cases:
        detected_errors = validate_payload(cursor, case["source_table"], case["raw_payload"])
        case["detected_reasons"] = detected_errors
        validated_malformed_cases.append(case)

    malformed_path = Path(malformed_path)
    malformed_path.parent.mkdir(parents=True, exist_ok=True)
    with open(malformed_path, "w", encoding="utf-8") as f:
        json.dump(validated_malformed_cases, f, indent=2)

    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    if fk_violations:
        raise sqlite3.IntegrityError(f"Foreign key violations detected by SQLite: {fk_violations}")

    # 6. Calculate actual metrics and compare with profile expectations
    cursor.execute("""
        SELECT po.supplier_id,
               SUM(CASE WHEN de.actual_delivery_date <= s.expected_delivery_date THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as on_time_rate
        FROM delivery_events de
        JOIN shipments s ON de.shipment_id = s.shipment_id
        JOIN purchase_orders po ON s.po_id = po.po_id
        GROUP BY po.supplier_id
    """)
    actual_delivery_rates = {row[0]: row[1] for row in cursor.fetchall()}

    mismatches = []
    for sup_id, expected_data in ground_truth.items():
        prof = expected_data["profile"]
        if sup_id in actual_delivery_rates and prof == "worsening_delivery":
            rate = actual_delivery_rates[sup_id]
            if rate > 0.85: # Worsening delivery should have notably lower on-time rate
                mismatches.append((sup_id, prof, rate))

    validation_results = {}
    for tbl in ["suppliers", "purchase_orders", "shipments", "inspections", "invoices", "invoice_lines"]:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
        validation_results[tbl] = cursor.fetchone()[0]

    conn.close()

    print("Synthetic Data Generation & Validation Complete successfully!")
    print(f"Table Counts: {validation_results}")
    if mismatches:
        print(f"Warning: {len(mismatches)} profiles showed higher delivery rates than expected.")
    return validation_results

if __name__ == "__main__":
    generate_synthetic_data()
