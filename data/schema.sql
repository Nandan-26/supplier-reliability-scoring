PRAGMA foreign_keys = ON;

-- 1. Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    country TEXT,
    status TEXT CHECK(status IN ('Active', 'Inactive', 'Probation')),
    created_at TEXT NOT NULL,
    system_available_at TEXT NOT NULL
);

-- 2. Sites (Composite PK enables cross-supplier site validation)
CREATE TABLE IF NOT EXISTS sites (
    site_id TEXT,
    supplier_id TEXT NOT NULL,
    site_name TEXT NOT NULL,
    location TEXT,
    is_active INTEGER DEFAULT 1,
    system_available_at TEXT NOT NULL,
    PRIMARY KEY (site_id, supplier_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);

-- 3. Contracts (Composite PK prevents cross-supplier contract linkage)
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT,
    supplier_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    agreed_terms TEXT,
    system_available_at TEXT NOT NULL,
    PRIMARY KEY (contract_id, supplier_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    CHECK (start_date <= end_date)
);

-- 4. Purchase Orders (Ensures site and contract belong to the correct supplier)
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    contract_id TEXT,
    order_date TEXT NOT NULL,
    status TEXT CHECK(status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled')),
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY (site_id, supplier_id) REFERENCES sites(site_id, supplier_id),
    FOREIGN KEY (contract_id, supplier_id) REFERENCES contracts(contract_id, supplier_id)
);

-- 5. PO Lines (Core grain for Capacity & Delivery evaluation)
CREATE TABLE IF NOT EXISTS po_lines (
    po_line_id TEXT,
    po_id TEXT NOT NULL,
    item_code TEXT NOT NULL,
    ordered_qty REAL NOT NULL CHECK(ordered_qty > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    requested_delivery_date TEXT NOT NULL,
    system_available_at TEXT NOT NULL,
    PRIMARY KEY (po_line_id, po_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE
);

-- 6. Shipments
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    po_line_id TEXT NOT NULL,
    po_id TEXT NOT NULL,
    shipped_qty REAL NOT NULL CHECK(shipped_qty >= 0),
    dispatch_date TEXT NOT NULL,
    expected_delivery_date TEXT NOT NULL,
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (po_line_id, po_id) REFERENCES po_lines(po_line_id, po_id) ON DELETE CASCADE,
    CHECK (dispatch_date <= expected_delivery_date)
);

-- 7. Delivery Events
CREATE TABLE IF NOT EXISTS delivery_events (
    delivery_event_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    actual_delivery_date TEXT NOT NULL,
    delivered_qty REAL NOT NULL CHECK(delivered_qty >= 0),
    receiver_notes TEXT,
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE
);

-- Trigger: Ensure delivery date is not before shipment dispatch date
CREATE TRIGGER IF NOT EXISTS trg_check_delivery_after_dispatch
BEFORE INSERT ON delivery_events
BEGIN
    SELECT RAISE(ABORT, 'Delivery date cannot be earlier than shipment dispatch date.')
    FROM shipments
    WHERE shipments.shipment_id = NEW.shipment_id
      AND NEW.actual_delivery_date < shipments.dispatch_date;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_delivery_date_after_dispatch_update
BEFORE UPDATE OF actual_delivery_date, shipment_id ON delivery_events
BEGIN
    SELECT RAISE(ABORT, 'Delivery date cannot be earlier than shipment dispatch date.')
    FROM shipments
    WHERE shipments.shipment_id = NEW.shipment_id
      AND NEW.actual_delivery_date < shipments.dispatch_date;
END;

-- 8. Inspections (Checks defective vs inspected quantity logic)
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id TEXT PRIMARY KEY,
    delivery_event_id TEXT NOT NULL,
    inspection_date TEXT NOT NULL,
    inspected_qty REAL NOT NULL CHECK(inspected_qty > 0),
    defective_qty REAL NOT NULL CHECK(defective_qty >= 0),
    result_status TEXT CHECK(result_status IN ('Passed', 'Failed', 'Conditionally Accepted')),
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (delivery_event_id) REFERENCES delivery_events(delivery_event_id) ON DELETE CASCADE,
    CHECK (defective_qty <= inspected_qty)
);

-- Trigger: Ensure inspection date is not before delivery event date
CREATE TRIGGER IF NOT EXISTS trg_check_inspection_after_delivery
BEFORE INSERT ON inspections
BEGIN
    SELECT RAISE(ABORT, 'Inspection date cannot be earlier than delivery event date.')
    FROM delivery_events
    WHERE delivery_events.delivery_event_id = NEW.delivery_event_id
      AND NEW.inspection_date < delivery_events.actual_delivery_date;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_inspection_date_after_delivery_update
BEFORE UPDATE OF inspection_date, delivery_event_id ON inspections
BEGIN
    SELECT RAISE(ABORT, 'Inspection date cannot be earlier than delivery event date.')
    FROM delivery_events
    WHERE delivery_events.delivery_event_id = NEW.delivery_event_id
      AND NEW.inspection_date < delivery_events.actual_delivery_date;
END;

-- 9. Invoices (Composite PK enables strict invoice line matching)
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT,
    po_id TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    status TEXT CHECK(status IN ('Matched', 'Discrepancy', 'Paid')),
    system_available_at TEXT NOT NULL,
    PRIMARY KEY (invoice_id, po_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE
);

-- 10. Invoice Lines (Ensures invoice line belongs to the same invoice AND same PO)
CREATE TABLE IF NOT EXISTS invoice_lines (
    invoice_line_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    po_id TEXT NOT NULL,
    po_line_id TEXT NOT NULL,
    invoiced_qty REAL NOT NULL CHECK(invoiced_qty >= 0),
    billed_unit_price REAL NOT NULL CHECK(billed_unit_price >= 0),
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (invoice_id, po_id) REFERENCES invoices(invoice_id, po_id) ON DELETE CASCADE,
    FOREIGN KEY (po_line_id, po_id) REFERENCES po_lines(po_line_id, po_id) ON DELETE CASCADE
);

-- 11. Risk Signals
CREATE TABLE IF NOT EXISTS risk_signals (
    risk_signal_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    category TEXT CHECK(category IN ('Compliance', 'Disruption')),
    severity TEXT CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    description TEXT,
    system_available_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);

-- Quarantine Log (For malformed challenge data testing)
CREATE TABLE IF NOT EXISTS quarantine_log (
    quarantine_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    logged_at TEXT NOT NULL
);

-- Score Runs & Supplier Scores
CREATE TABLE IF NOT EXISTS score_runs (
    run_id TEXT PRIMARY KEY,
    run_timestamp TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    config_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    random_seed INTEGER
);

CREATE TABLE IF NOT EXISTS supplier_scores (
    score_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    delivery_score REAL,
    delivery_sample_count INTEGER DEFAULT 0,
    delivery_confidence TEXT,
    quality_score REAL,
    quality_sample_count INTEGER DEFAULT 0,
    quality_confidence TEXT,
    cost_score REAL,
    cost_sample_count INTEGER DEFAULT 0,
    cost_confidence TEXT,
    capacity_score REAL,
    capacity_sample_count INTEGER DEFAULT 0,
    capacity_confidence TEXT,
    compliance_score REAL,
    compliance_sample_count INTEGER DEFAULT 0,
    compliance_confidence TEXT,
    disruption_score REAL,
    disruption_sample_count INTEGER DEFAULT 0,
    disruption_confidence TEXT,
    final_score REAL,
    overall_confidence_tier TEXT,
    FOREIGN KEY (run_id) REFERENCES score_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);

-- Target indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_lines_po ON po_lines(po_id, po_line_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_po_line ON invoice_lines(po_id, po_line_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date, system_available_at);
CREATE INDEX IF NOT EXISTS idx_shipments_po_line ON shipments(po_line_id);
CREATE INDEX IF NOT EXISTS idx_delivery_events_shipment ON delivery_events(shipment_id);
CREATE INDEX IF NOT EXISTS idx_inspections_delivery ON inspections(delivery_event_id);

-- Business-rule triggers: enforce cumulative quantities across child rows.
CREATE TRIGGER IF NOT EXISTS trg_prevent_cancelled_po_shipment
BEFORE INSERT ON shipments
BEGIN
    SELECT RAISE(ABORT, 'Cancelled purchase orders cannot receive shipments.')
    WHERE EXISTS (
        SELECT 1 FROM purchase_orders
        WHERE po_id = NEW.po_id AND status = 'Cancelled'
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_shipped_qty_insert
BEFORE INSERT ON shipments
BEGIN
    SELECT RAISE(ABORT, 'Cumulative shipped quantity cannot exceed ordered quantity.')
    WHERE COALESCE((
        SELECT SUM(shipped_qty) FROM shipments
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
    ), 0) + NEW.shipped_qty > (
        SELECT ordered_qty FROM po_lines
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_shipped_qty_update
BEFORE UPDATE OF shipped_qty, po_id, po_line_id ON shipments
BEGIN
    SELECT RAISE(ABORT, 'Cumulative shipped quantity cannot exceed ordered quantity.')
    WHERE COALESCE((
        SELECT SUM(shipped_qty) FROM shipments
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
          AND shipment_id != OLD.shipment_id
    ), 0) + NEW.shipped_qty > (
        SELECT ordered_qty FROM po_lines
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_cancelled_po_shipment_update
BEFORE UPDATE OF po_id ON shipments
BEGIN
    SELECT RAISE(ABORT, 'Cancelled purchase orders cannot receive shipments.')
    WHERE EXISTS (
        SELECT 1 FROM purchase_orders
        WHERE po_id = NEW.po_id AND status = 'Cancelled'
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_cancelling_po_with_shipments
BEFORE UPDATE OF status ON purchase_orders
WHEN NEW.status = 'Cancelled'
BEGIN
    SELECT RAISE(ABORT, 'A purchase order with shipments cannot be cancelled.')
    WHERE EXISTS (
        SELECT 1 FROM shipments WHERE po_id = OLD.po_id
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_delivered_qty_insert
BEFORE INSERT ON delivery_events
BEGIN
    SELECT RAISE(ABORT, 'Cumulative delivered quantity cannot exceed shipped quantity.')
    WHERE COALESCE((
        SELECT SUM(delivered_qty) FROM delivery_events
        WHERE shipment_id = NEW.shipment_id
    ), 0) + NEW.delivered_qty > (
        SELECT shipped_qty FROM shipments WHERE shipment_id = NEW.shipment_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_delivered_qty_update
BEFORE UPDATE OF delivered_qty, shipment_id ON delivery_events
BEGIN
    SELECT RAISE(ABORT, 'Cumulative delivered quantity cannot exceed shipped quantity.')
    WHERE COALESCE((
        SELECT SUM(delivered_qty) FROM delivery_events
        WHERE shipment_id = NEW.shipment_id
          AND delivery_event_id != OLD.delivery_event_id
    ), 0) + NEW.delivered_qty > (
        SELECT shipped_qty FROM shipments WHERE shipment_id = NEW.shipment_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_inspected_qty_insert
BEFORE INSERT ON inspections
BEGIN
    SELECT RAISE(ABORT, 'Cumulative inspected quantity cannot exceed delivered quantity.')
    WHERE COALESCE((
        SELECT SUM(inspected_qty) FROM inspections
        WHERE delivery_event_id = NEW.delivery_event_id
    ), 0) + NEW.inspected_qty > (
        SELECT delivered_qty FROM delivery_events
        WHERE delivery_event_id = NEW.delivery_event_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_inspected_qty_update
BEFORE UPDATE OF inspected_qty, delivery_event_id ON inspections
BEGIN
    SELECT RAISE(ABORT, 'Cumulative inspected quantity cannot exceed delivered quantity.')
    WHERE COALESCE((
        SELECT SUM(inspected_qty) FROM inspections
        WHERE delivery_event_id = NEW.delivery_event_id
          AND inspection_id != OLD.inspection_id
    ), 0) + NEW.inspected_qty > (
        SELECT delivered_qty FROM delivery_events
        WHERE delivery_event_id = NEW.delivery_event_id
    ) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_invoice_date_after_delivery
BEFORE INSERT ON invoices
BEGIN
    SELECT RAISE(ABORT, 'Invoice date cannot be earlier than the latest delivery on the PO.')
    WHERE (
        SELECT MAX(de.actual_delivery_date)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id
    ) IS NOT NULL
    AND NEW.invoice_date < (
        SELECT MAX(de.actual_delivery_date)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_invoice_for_cancelled_po
BEFORE INSERT ON invoices
BEGIN
    SELECT RAISE(ABORT, 'Cancelled purchase orders cannot be invoiced.')
    WHERE EXISTS (
        SELECT 1 FROM purchase_orders
        WHERE po_id = NEW.po_id AND status = 'Cancelled'
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_check_invoice_date_after_delivery_update
BEFORE UPDATE OF invoice_date, po_id ON invoices
BEGIN
    SELECT RAISE(ABORT, 'Invoice date cannot be earlier than the latest delivery on the PO.')
    WHERE (
        SELECT MAX(de.actual_delivery_date)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id
    ) IS NOT NULL
    AND NEW.invoice_date < (
        SELECT MAX(de.actual_delivery_date)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_invoiced_qty_insert
BEFORE INSERT ON invoice_lines
BEGIN
    SELECT RAISE(ABORT, 'Cumulative invoiced quantity cannot exceed delivered quantity.')
    WHERE COALESCE((
        SELECT SUM(invoiced_qty) FROM invoice_lines
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
    ), 0) + NEW.invoiced_qty > COALESCE((
        SELECT SUM(de.delivered_qty)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id AND s.po_line_id = NEW.po_line_id
    ), 0) + 0.000001;
END;

CREATE TRIGGER IF NOT EXISTS trg_check_cumulative_invoiced_qty_update
BEFORE UPDATE OF invoiced_qty, po_id, po_line_id ON invoice_lines
BEGIN
    SELECT RAISE(ABORT, 'Cumulative invoiced quantity cannot exceed delivered quantity.')
    WHERE COALESCE((
        SELECT SUM(invoiced_qty) FROM invoice_lines
        WHERE po_id = NEW.po_id AND po_line_id = NEW.po_line_id
          AND invoice_line_id != OLD.invoice_line_id
    ), 0) + NEW.invoiced_qty > COALESCE((
        SELECT SUM(de.delivered_qty)
        FROM shipments s
        JOIN delivery_events de ON de.shipment_id = s.shipment_id
        WHERE s.po_id = NEW.po_id AND s.po_line_id = NEW.po_line_id
    ), 0) + 0.000001;
END;

CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_scores_run_supplier
ON supplier_scores(run_id, supplier_id);

CREATE INDEX IF NOT EXISTS idx_risk_signals_supplier ON risk_signals(supplier_id, category);
CREATE INDEX IF NOT EXISTS idx_suppliers_point_in_time ON suppliers(created_at, system_available_at);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_dates ON purchase_orders(supplier_id, order_date, system_available_at);
CREATE INDEX IF NOT EXISTS idx_shipments_po_line_composite ON shipments(po_id, po_line_id, system_available_at);
CREATE INDEX IF NOT EXISTS idx_delivery_events_point_in_time ON delivery_events(actual_delivery_date, system_available_at, shipment_id);
CREATE INDEX IF NOT EXISTS idx_inspections_point_in_time ON inspections(inspection_date, system_available_at, delivery_event_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_point_in_time ON invoice_lines(system_available_at, po_id, po_line_id);
CREATE INDEX IF NOT EXISTS idx_risk_signals_point_in_time ON risk_signals(signal_date, system_available_at, supplier_id);