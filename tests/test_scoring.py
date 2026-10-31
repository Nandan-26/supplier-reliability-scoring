from pathlib import Path
import sqlite3
import pytest
from src.db import get_connection, initialize_database
from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores, validate_weights, DEFAULT_WEIGHTS

TEST_DB_PATH = Path("data/test_scoring.db")
TEST_GT_PATH = Path("data/test_scoring_gt.json")
TEST_MAL_PATH = Path("data/test_scoring_mal.json")

@pytest.fixture(autouse=True)
def setup_scoring_env():
    for p in [TEST_DB_PATH, TEST_GT_PATH, TEST_MAL_PATH]:
        if p.exists():
            try:
                p.unlink()
            except PermissionError:
                pass
    initialize_database(TEST_DB_PATH)
    generate_synthetic_data(
        db_path=TEST_DB_PATH,
        ground_truth_path=TEST_GT_PATH,
        malformed_path=TEST_MAL_PATH,
        num_suppliers=20,
        num_pos=50,
        num_shipments=50,
        num_inspections=50,
        seed=42
    )
    yield
    for p in [TEST_DB_PATH, TEST_GT_PATH, TEST_MAL_PATH]:
        if p.exists():
            try:
                p.unlink()
            except PermissionError:
                pass

def test_weights_validation():
    validate_weights(DEFAULT_WEIGHTS)
    with pytest.raises(ValueError):
        validate_weights({"delivery": 0.5, "quality": 0.5, "cost": 0.1, "capacity": 0.0, "compliance": 0.0, "disruption": 0.0})
    with pytest.raises(ValueError):
        validate_weights({"delivery": 1.2, "quality": -0.2, "cost": 0.0, "capacity": 0.0, "compliance": 0.0, "disruption": 0.0})
    with pytest.raises(ValueError):
        validate_weights({"delivery": 1.0})

def test_score_ranges_and_persistence():
    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT final_score, delivery_score, quality_score, cost_score, capacity_score, compliance_score, disruption_score FROM supplier_scores WHERE run_id = ?;", (run_id,))
        scores = cursor.fetchall()
    finally:
        conn.close()

    assert len(scores) == 20
    for row in scores:
        for score in row:
            assert score is not None
            assert 0.0 <= score <= 100.0

def test_missing_history_fallback():
    run_id = calculate_supplier_scores(as_of_date="2020-01-01", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT delivery_score, delivery_sample_count, delivery_confidence FROM supplier_scores WHERE run_id = ?;", (run_id,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    for row in rows:
        assert row["delivery_score"] == 50.0
        assert row["delivery_sample_count"] == 0
        assert row["delivery_confidence"] == "No Data"

def test_rigorous_as_of_date_leakage_protection():
    run_id_initial = calculate_supplier_scores(as_of_date="2026-02-01", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT final_score, delivery_sample_count FROM supplier_scores WHERE run_id = ? AND supplier_id = 'SUP-000001';", (run_id_initial,))
        initial_row = cursor.fetchone()
    finally:
        conn.close()

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO suppliers VALUES ('SUP-000001', 'Test Sup', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO sites VALUES ('SITE-SUP-000001-1', 'SUP-000001', 'Plant', 'USA', 1, '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO contracts VALUES ('CON-SUP-000001', 'SUP-000001', '2026-01-01', '2026-12-31', 'Net30', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO purchase_orders VALUES ('PO-FUTURE', 'SUP-000001', 'SITE-SUP-000001-1', 'CON-SUP-000001', '2026-01-02', 'Fulfilled', '2026-01-02');")
        cursor.execute("INSERT OR IGNORE INTO po_lines VALUES ('LINE-FUTURE', 'PO-FUTURE', 'ITEM-1', 100, 10.0, '2026-06-01', '2026-01-02');")

        cursor.execute("INSERT INTO shipments VALUES ('SHP-FUT', 'LINE-FUTURE', 'PO-FUTURE', 50, '2026-05-25', '2026-06-01', '2026-06-01');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-FUT', 'SHP-FUT', '2026-06-01', 50, 'Late', '2026-06-01');")

        cursor.execute("INSERT INTO shipments VALUES ('SHP-LATE', 'LINE-FUTURE', 'PO-FUTURE', 50, '2026-01-03', '2026-01-05', '2026-07-01');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-LATE', 'SHP-LATE', '2026-01-05', 50, 'Late reported', '2026-07-01');")

        conn.commit()
    finally:
        conn.close()

    run_id_recalc = calculate_supplier_scores(as_of_date="2026-02-01", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT final_score, delivery_sample_count FROM supplier_scores WHERE run_id = ? AND supplier_id = 'SUP-000001';", (run_id_recalc,))
        recalc_row = cursor.fetchone()
    finally:
        conn.close()

    assert initial_row["final_score"] == recalc_row["final_score"]
    assert initial_row["delivery_sample_count"] == recalc_row["delivery_sample_count"]

def test_capacity_multi_delivery_inflation():
    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO suppliers VALUES ('SUP-CAP', 'Cap Sup', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO sites VALUES ('SITE-CAP', 'SUP-CAP', 'Plant', 'USA', 1, '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO contracts VALUES ('CON-CAP', 'SUP-CAP', '2026-01-01', '2026-12-31', 'Net30', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO purchase_orders VALUES ('PO-CAP', 'SUP-CAP', 'SITE-CAP', 'CON-CAP', '2026-01-02', 'Fulfilled', '2026-01-02');")
        cursor.execute("INSERT OR IGNORE INTO po_lines VALUES ('LINE-CAP', 'PO-CAP', 'ITEM-1', 100, 10.0, '2026-01-10', '2026-01-02');")

        cursor.execute("INSERT INTO shipments VALUES ('SHP-CAP', 'LINE-CAP', 'PO-CAP', 100, '2026-01-05', '2026-01-09', '2026-01-05');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-CAP-1', 'SHP-CAP', '2026-01-09', 50, 'Part 1', '2026-01-09');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-CAP-2', 'SHP-CAP', '2026-01-09', 50, 'Part 2', '2026-01-09');")

        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT capacity_score FROM supplier_scores WHERE run_id = ? AND supplier_id = 'SUP-CAP';", (run_id,))
        cap_score = cursor.fetchone()[0]
    finally:
        conn.close()

    assert cap_score == 100.0

def test_inspection_aggregation_and_sample_count():
    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO suppliers VALUES ('SUP-INSP', 'Insp Sup', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO sites VALUES ('SITE-INSP', 'SUP-INSP', 'Plant', 'USA', 1, '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO contracts VALUES ('CON-INSP', 'SUP-INSP', '2026-01-01', '2026-12-31', 'Terms', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO purchase_orders VALUES ('PO-INSP', 'SUP-INSP', 'SITE-INSP', 'CON-INSP', '2026-01-02', 'Issued', '2026-01-02');")
        cursor.execute("INSERT OR IGNORE INTO po_lines VALUES ('LINE-INSP', 'PO-INSP', 'ITEM-X', 100, 10.0, '2026-01-10', '2026-01-02');")
        cursor.execute("INSERT OR IGNORE INTO shipments VALUES ('SHP-INSP', 'LINE-INSP', 'PO-INSP', 100, '2026-01-05', '2026-01-09', '2026-01-05');")
        cursor.execute("INSERT OR IGNORE INTO delivery_events VALUES ('DEL-INSP', 'SHP-INSP', '2026-01-09', 100, 'OK', '2026-01-09');")

        cursor.execute("INSERT INTO inspections VALUES ('INS-LOT-1', 'DEL-INSP', '2026-01-10', 50, 0, 'Passed', '2026-01-10');")
        cursor.execute("INSERT INTO inspections VALUES ('INS-LOT-2', 'DEL-INSP', '2026-01-10', 50, 10, 'Failed', '2026-01-10');")

        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT quality_score, quality_sample_count FROM supplier_scores WHERE run_id = ? AND supplier_id = 'SUP-INSP';", (run_id,))
        row = cursor.fetchone()
    finally:
        conn.close()

    assert row["quality_score"] == 90.0
    assert row["quality_sample_count"] == 2

def test_delivery_partials_evaluation():
    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO suppliers VALUES ('SUP-PART', 'Part Sup', 'Tech', 'USA', 'Active', '2026-01-01', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO sites VALUES ('SITE-PART', 'SUP-PART', 'Plant', 'USA', 1, '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO contracts VALUES ('CON-PART', 'SUP-PART', '2026-01-01', '2026-12-31', 'Net30', '2026-01-01');")
        cursor.execute("INSERT OR IGNORE INTO purchase_orders VALUES ('PO-PART', 'SUP-PART', 'SITE-PART', 'CON-PART', '2026-01-02', 'Fulfilled', '2026-01-02');")
        cursor.execute("INSERT OR IGNORE INTO po_lines VALUES ('LINE-PART', 'PO-PART', 'ITEM-1', 100, 10.0, '2026-01-10', '2026-01-02');")

        cursor.execute("INSERT INTO shipments VALUES ('SHP-P1', 'LINE-PART', 'PO-PART', 50, '2026-01-05', '2026-01-10', '2026-01-05');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-P1', 'SHP-P1', '2026-01-08', 50, 'Partial on time', '2026-01-08');")

        cursor.execute("INSERT INTO shipments VALUES ('SHP-P2', 'LINE-PART', 'PO-PART', 50, '2026-01-08', '2026-01-10', '2026-01-08');")
        cursor.execute("INSERT INTO delivery_events VALUES ('DEL-P2', 'SHP-P2', '2026-01-15', 50, 'Balance late', '2026-01-15');")

        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)

    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT delivery_score FROM supplier_scores WHERE run_id = ? AND supplier_id = 'SUP-PART';", (run_id,))
        del_score = cursor.fetchone()[0]
    finally:
        conn.close()

    assert del_score == 0.0

def test_delivery_score_never_exceeds_100_with_multiple_events():
    conn = get_connection(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO suppliers VALUES "
            "('SUP-DEL-BOUND', 'Delivery Bound Test', 'Tech', 'USA', "
            "'Active', '2026-01-01', '2026-01-01');"
        )
        cursor.execute(
            "INSERT INTO sites VALUES "
            "('SITE-DEL-BOUND', 'SUP-DEL-BOUND', 'Plant', 'USA', 1, '2026-01-01');"
        )
        cursor.execute(
            "INSERT INTO contracts VALUES "
            "('CON-DEL-BOUND', 'SUP-DEL-BOUND', '2026-01-01', "
            "'2026-12-31', 'Net30', '2026-01-01');"
        )
        cursor.execute(
            "INSERT INTO purchase_orders VALUES "
            "('PO-DEL-BOUND', 'SUP-DEL-BOUND', 'SITE-DEL-BOUND', "
            "'CON-DEL-BOUND', '2026-01-02', 'Fulfilled', '2026-01-02');"
        )
        cursor.execute(
            "INSERT INTO po_lines VALUES "
            "('LINE-DEL-BOUND', 'PO-DEL-BOUND', 'ITEM-1', 100, 10.0, "
            "'2026-01-10', '2026-01-02');"
        )
        cursor.execute(
            "INSERT INTO shipments VALUES "
            "('SHP-DEL-BOUND', 'LINE-DEL-BOUND', 'PO-DEL-BOUND', 100, "
            "'2026-01-05', '2026-01-09', '2026-01-05');"
        )
        cursor.execute(
            "INSERT INTO delivery_events VALUES "
            "('DEL-BOUND-1', 'SHP-DEL-BOUND', '2026-01-09', 50, "
            "'Partial 1', '2026-01-09');"
        )
        cursor.execute(
            "INSERT INTO delivery_events VALUES "
            "('DEL-BOUND-2', 'SHP-DEL-BOUND', '2026-01-09', 50, "
            "'Partial 2', '2026-01-09');"
        )
        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(
        as_of_date="2026-12-31",
        db_path=TEST_DB_PATH,
    )

    conn = get_connection(TEST_DB_PATH)
    try:
        row = conn.execute(
            "SELECT delivery_score FROM supplier_scores "
            "WHERE run_id = ? AND supplier_id = 'SUP-DEL-BOUND';",
            (run_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert 0.0 <= row[0] <= 100.0
    assert row[0] == 100.0


def test_compliance_and_disruption_without_signals_are_neutral_and_unobserved():
    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)
    conn = get_connection(TEST_DB_PATH)
    try:
        row = conn.execute("""
            SELECT compliance_score, compliance_sample_count, compliance_confidence,
                   disruption_score, disruption_sample_count, disruption_confidence
            FROM supplier_scores
            WHERE run_id = ? AND supplier_id = 'SUP-000001';
        """, (run_id,)).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == 50.0
    assert row[1] == 0
    assert row[2] == "No Data"
    assert row[3] == 50.0
    assert row[4] == 0
    assert row[5] == "No Data"


@pytest.mark.parametrize("invalid_date", ["2026-2-01", "not-a-date", "", None])
def test_invalid_as_of_date_is_rejected(invalid_date):
    with pytest.raises(ValueError, match="as_of_date"):
        calculate_supplier_scores(as_of_date=invalid_date, db_path=TEST_DB_PATH)


def test_supplier_created_or_available_after_as_of_date_is_not_scored():
    conn = get_connection(TEST_DB_PATH)
    try:
        conn.execute(
            "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?, ?, ?);",
            (
                "SUP-FUTURE", "Future Supplier", "Tech", "USA", "Active",
                "2026-03-01", "2026-03-03"
            )
        )
        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(
        as_of_date="2026-02-28", db_path=TEST_DB_PATH
    )

    conn = get_connection(TEST_DB_PATH)
    try:
        future_rows = conn.execute(
            "SELECT COUNT(*) FROM supplier_scores "
            "WHERE run_id = ? AND supplier_id = 'SUP-FUTURE';",
            (run_id,)
        ).fetchone()[0]
        eligible_rows = conn.execute(
            "SELECT COUNT(*) FROM supplier_scores WHERE run_id = ?;",
            (run_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    assert future_rows == 0
    assert eligible_rows == 20


def test_score_run_metadata_does_not_claim_an_unknown_generation_seed():
    run_id = calculate_supplier_scores(as_of_date="2026-12-31", db_path=TEST_DB_PATH)
    conn = get_connection(TEST_DB_PATH)
    try:
        row = conn.execute("""
            SELECT random_seed, config_version, config_hash, generator_version
            FROM score_runs WHERE run_id = ?;
        """, (run_id,)).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] is None
    assert row[1] == "v1.1"
    assert len(row[2]) == 12
    assert row[3] == "1.1.0"


def test_delivery_join_respects_composite_po_line_key():
    conn = get_connection(TEST_DB_PATH)
    try:
        conn.execute(
            "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("SUP-DUPLINE", "Duplicate Line Supplier", "Tech", "USA",
             "Active", "2026-01-01", "2026-01-01")
        )
        conn.execute(
            "INSERT INTO sites VALUES (?, ?, ?, ?, ?, ?);",
            ("SITE-DUPLINE", "SUP-DUPLINE", "Plant", "USA", 1, "2026-01-01")
        )
        conn.execute(
            "INSERT INTO contracts VALUES (?, ?, ?, ?, ?, ?);",
            ("CON-DUPLINE", "SUP-DUPLINE", "2026-01-01", "2026-12-31",
             "Net30", "2026-01-01")
        )
        for index, status in ((1, "Fulfilled"), (2, "Fulfilled")):
            po_id = f"PO-DUPLINE-{index}"
            shipment_id = f"SHP-DUPLINE-{index}"
            delivery_id = f"DEL-DUPLINE-{index}"
            conn.execute(
                "INSERT INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?, ?);",
                (po_id, "SUP-DUPLINE", "SITE-DUPLINE", "CON-DUPLINE",
                 "2026-01-02", status, "2026-01-02")
            )
            conn.execute(
                "INSERT INTO po_lines VALUES (?, ?, ?, ?, ?, ?, ?);",
                ("LINE-SHARED", po_id, "ITEM-1", 100, 10.0,
                 "2026-01-10", "2026-01-02")
            )
            conn.execute(
                "INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?);",
                (shipment_id, "LINE-SHARED", po_id, 100, "2026-01-05",
                 "2026-01-10", "2026-01-05")
            )
            actual_date = "2026-01-09" if index == 1 else "2026-01-15"
            conn.execute(
                "INSERT INTO delivery_events VALUES (?, ?, ?, ?, ?, ?);",
                (delivery_id, shipment_id, actual_date, 100, "Test", actual_date)
            )
        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(
        as_of_date="2026-01-31", db_path=TEST_DB_PATH
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        row = conn.execute(
            "SELECT delivery_score, delivery_sample_count FROM supplier_scores "
            "WHERE run_id=? AND supplier_id='SUP-DUPLINE';",
            (run_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row == (50.0, 2)


def test_risk_dimension_confidence_uses_sample_size():
    conn = get_connection(TEST_DB_PATH)
    try:
        conn.executemany(
            "INSERT INTO risk_signals VALUES (?, ?, ?, ?, ?, ?, ?);",
            [
                (f"RS-TEST-{i}", "SUP-000001", "2026-01-20",
                 "Compliance", "Low", "Test compliance signal", "2026-01-20")
                for i in range(1, 6)
            ] + [
                ("RS-TEST-D", "SUP-000001", "2026-01-20",
                 "Disruption", "Low", "Test disruption signal", "2026-01-20")
            ]
        )
        conn.commit()
    finally:
        conn.close()

    run_id = calculate_supplier_scores(
        as_of_date="2026-12-31", db_path=TEST_DB_PATH
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        row = conn.execute("""
            SELECT compliance_sample_count, compliance_confidence,
                   disruption_sample_count, disruption_confidence
            FROM supplier_scores
            WHERE run_id=? AND supplier_id='SUP-000001';
        """, (run_id,)).fetchone()
    finally:
        conn.close()

    assert row == (5, "High", 1, "Low (Sparse Data)")


@pytest.mark.parametrize("bad_weight", [float("nan"), float("inf"), True])
def test_weights_reject_non_finite_and_boolean_values(bad_weight):
    invalid = dict(DEFAULT_WEIGHTS)
    invalid["delivery"] = bad_weight
    with pytest.raises(ValueError):
        validate_weights(invalid)


def test_late_available_po_line_is_excluded_from_all_operational_dimensions():
    before_run = calculate_supplier_scores(
        as_of_date="2026-02-01", db_path=TEST_DB_PATH
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        before = conn.execute("""
            SELECT delivery_score, delivery_sample_count,
                   quality_score, quality_sample_count,
                   cost_score, cost_sample_count,
                   capacity_score, capacity_sample_count
            FROM supplier_scores
            WHERE run_id=? AND supplier_id='SUP-000001';
        """, (before_run,)).fetchone()

        conn.execute(
            "INSERT INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("PO-LATE-ARRIVAL", "SUP-000001", "SITE-SUP-000001-1",
             "CON-SUP-000001", "2026-01-02", "Issued", "2026-01-02")
        )
        conn.execute(
            "INSERT INTO po_lines VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("LINE-LATE-ARRIVAL", "PO-LATE-ARRIVAL", "ITEM-LATE",
             100, 10.0, "2026-01-10", "2026-07-01")
        )
        conn.execute(
            "INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("SHP-LATE-ARRIVAL", "LINE-LATE-ARRIVAL", "PO-LATE-ARRIVAL",
             100, "2026-01-05", "2026-01-10", "2026-01-05")
        )
        conn.execute(
            "INSERT INTO delivery_events VALUES (?, ?, ?, ?, ?, ?);",
            ("DEL-LATE-ARRIVAL", "SHP-LATE-ARRIVAL", "2026-01-09",
             100, "Late-reported source line", "2026-01-09")
        )
        conn.execute(
            "INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("INS-LATE-ARRIVAL", "DEL-LATE-ARRIVAL", "2026-01-10",
             100, 20, "Failed", "2026-01-10")
        )
        conn.execute(
            "INSERT INTO invoices VALUES (?, ?, ?, ?, ?);",
            ("INV-LATE-ARRIVAL", "PO-LATE-ARRIVAL", "2026-01-10",
             "Discrepancy", "2026-01-10")
        )
        conn.execute(
            "INSERT INTO invoice_lines VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("IL-LATE-ARRIVAL", "INV-LATE-ARRIVAL", "PO-LATE-ARRIVAL",
             "LINE-LATE-ARRIVAL", 100, 12.0, "2026-01-10")
        )
        conn.commit()
    finally:
        conn.close()

    after_run = calculate_supplier_scores(
        as_of_date="2026-02-01", db_path=TEST_DB_PATH
    )
    conn = get_connection(TEST_DB_PATH)
    try:
        after = conn.execute("""
            SELECT delivery_score, delivery_sample_count,
                   quality_score, quality_sample_count,
                   cost_score, cost_sample_count,
                   capacity_score, capacity_sample_count
            FROM supplier_scores
            WHERE run_id=? AND supplier_id='SUP-000001';
        """, (after_run,)).fetchone()
    finally:
        conn.close()

    assert after == before
