from datetime import datetime, timezone
import hashlib
import json
import math
import uuid
from pathlib import Path
import sqlite3

from src.db import get_connection

ROOT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_WEIGHTS = {
    "delivery": 0.25,
    "quality": 0.25,
    "cost": 0.15,
    "capacity": 0.15,
    "compliance": 0.10,
    "disruption": 0.10
}

SEVERITY_PENALTIES = {
    "Low": 10.0,
    "Medium": 25.0,
    "High": 50.0,
    "Critical": 100.0,
}
NO_DATA_SCORE = 50.0

def validate_weights(weights: dict[str, float]) -> None:
    """Validate that weights contain exactly the 6 required dimensions, are non-negative, finite, and sum to 1.0."""
    required_keys = set(DEFAULT_WEIGHTS.keys())
    if set(weights.keys()) != required_keys:
        raise ValueError(f"Weights must contain exactly these dimensions: {required_keys}")

    for k, v in weights.items():
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"Weight for '{k}' must be a finite, non-negative number, got {v}")

    total_weight = sum(weights.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
        raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")

def calculate_supplier_scores(
    as_of_date: str,
    db_path: str | Path = ROOT_DIR / "data" / "supplier_scoring.db",
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    config_version: str = "v1.1"
) -> str:
    """
    Calculate supplier reliability scores as of a specific date using vectorized set-based queries
    to eliminate per-supplier loop overhead and prevent execution hangs.
    """
    validate_weights(weights)
    try:
        parsed_as_of_date = datetime.strptime(as_of_date, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_date must be a valid date in YYYY-MM-DD format.") from exc
    if parsed_as_of_date.strftime("%Y-%m-%d") != as_of_date:
        raise ValueError("as_of_date must use the YYYY-MM-DD format.")

    conn = get_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        run_id = f"RUN-{uuid.uuid4().hex[:8]}"
        run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        config_payload = {
            "weights": weights,
            "severity_penalties": SEVERITY_PENALTIES,
            "no_data_score": NO_DATA_SCORE,
            "scoring_method": "supplier-score-v1.1",
        }
        config_hash = hashlib.sha256(
            json.dumps(config_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        generator_version = "1.1.0"

        # Record Score Run (ensuring interrupted runs don't corrupt prior history)
        cursor.execute(
            """
            INSERT INTO score_runs (run_id, run_timestamp, as_of_date, config_version, config_hash, generator_version, random_seed)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            # The scoring function cannot infer which seed produced an
            # arbitrary existing database. Store NULL rather than a false claim.
            (run_id, run_timestamp, as_of_date, config_version, config_hash, generator_version, None)
        )

        # Score only suppliers that existed and were visible to the system by
        # the requested as-of date. Future-created suppliers are not historical
        # suppliers for this run.
        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE created_at <= ?
              AND system_available_at <= ?
            ORDER BY supplier_id;
        """, (as_of_date, as_of_date))
        suppliers = [row["supplier_id"] for row in cursor.fetchall()]

        # --- VECTORIZED PRE-AGGREGATION (All Suppliers in Single Queries) ---

        # 1. Delivery Aggregation per Supplier
        cursor.execute(
            """
            WITH line_delivery AS (
                SELECT
                    po.supplier_id,
                    pl.po_id,
                    pl.po_line_id,
                    pl.ordered_qty,
                    pl.requested_delivery_date,
                    COALESCE(MAX(de.actual_delivery_date), '9999-12-31') as final_delivery_date,
                    SUM(CASE WHEN de.actual_delivery_date <= pl.requested_delivery_date THEN de.delivered_qty ELSE 0 END) as delivered_on_time_qty
                FROM purchase_orders po
                JOIN po_lines pl ON po.po_id = pl.po_id
                LEFT JOIN shipments s ON pl.po_line_id = s.po_line_id AND s.system_available_at <= ?
                LEFT JOIN delivery_events de ON s.shipment_id = de.shipment_id AND de.actual_delivery_date <= ? AND de.system_available_at <= ?
                WHERE po.status != 'Cancelled'
                  AND po.order_date <= ?
                  AND po.system_available_at <= ?
                  AND pl.requested_delivery_date <= ?
                  AND pl.system_available_at <= ?
                GROUP BY po.supplier_id, pl.po_id, pl.po_line_id
            )
            SELECT
                supplier_id,
                COUNT(po_line_id) as total_lines,
                SUM(CASE WHEN final_delivery_date <= requested_delivery_date OR delivered_on_time_qty >= ordered_qty THEN 1 ELSE 0 END) as on_time_lines
            FROM line_delivery
            GROUP BY supplier_id;
            """,
            (as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date)
        )
        delivery_map = {row["supplier_id"]: (row["total_lines"], row["on_time_lines"]) for row in cursor.fetchall()}

        # 2. Quality Aggregation per Supplier
        cursor.execute(
            """
            WITH ins_summary AS (
                SELECT
                    po.supplier_id,
                    ins.inspection_id,
                    ins.inspected_qty,
                    ins.defective_qty
                FROM purchase_orders po
                JOIN shipments s ON po.po_id = s.po_id
                JOIN delivery_events de ON s.shipment_id = de.shipment_id
                JOIN inspections ins ON de.delivery_event_id = ins.delivery_event_id
                WHERE po.status != 'Cancelled'
                  AND po.order_date <= ?
                  AND po.system_available_at <= ?
                  AND ins.inspection_date <= ?
                  AND ins.system_available_at <= ?
                  AND de.actual_delivery_date <= ?
                  AND de.system_available_at <= ?
                  AND s.system_available_at <= ?
                GROUP BY po.supplier_id, ins.inspection_id
            )
            SELECT
                supplier_id,
                SUM(inspected_qty) as total_inspected,
                SUM(defective_qty) as total_defective,
                COUNT(inspection_id) as insp_count
            FROM ins_summary
            GROUP BY supplier_id;
            """,
            (as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date)
        )
        quality_map = {row["supplier_id"]: (row["total_inspected"], row["total_defective"], row["insp_count"]) for row in cursor.fetchall()}

        # 3. Cost Aggregation per Supplier
        cursor.execute(
            """
            SELECT
                po.supplier_id,
                COUNT(il.invoice_line_id) as total_invoices,
                SUM(CASE WHEN il.billed_unit_price <= pl.unit_price THEN 1 ELSE 0 END) as matching_invoices
            FROM purchase_orders po
            JOIN po_lines pl ON po.po_id = pl.po_id
            JOIN invoice_lines il ON pl.po_line_id = il.po_line_id AND pl.po_id = il.po_id
            JOIN invoices i ON il.invoice_id = i.invoice_id AND il.po_id = i.po_id
            WHERE po.status != 'Cancelled'
              AND po.order_date <= ?
              AND po.system_available_at <= ?
              AND i.invoice_date <= ?
              AND i.system_available_at <= ?
              AND il.system_available_at <= ?
            GROUP BY po.supplier_id;
            """,
            (as_of_date, as_of_date, as_of_date, as_of_date, as_of_date)
        )
        cost_map = {row["supplier_id"]: (row["total_invoices"], row["matching_invoices"]) for row in cursor.fetchall()}

        # 4. Capacity Aggregation per Supplier
        cursor.execute(
            """
            WITH line_delivered AS (
                SELECT po.supplier_id, s.po_id, s.po_line_id,
                       COALESCE(SUM(del_agg.delivered_qty), 0) as delivered_qty
                FROM purchase_orders po
                JOIN shipments s ON po.po_id = s.po_id
                LEFT JOIN (
                    SELECT de.shipment_id, SUM(de.delivered_qty) as delivered_qty
                    FROM delivery_events de
                    WHERE de.system_available_at <= ? AND de.actual_delivery_date <= ?
                    GROUP BY de.shipment_id
                ) del_agg ON s.shipment_id = del_agg.shipment_id
                WHERE s.system_available_at <= ?
                GROUP BY po.supplier_id, s.po_id, s.po_line_id
            )
            SELECT
                po.supplier_id,
                SUM(pl.ordered_qty) as total_ordered,
                COALESCE(SUM(ld.delivered_qty), 0) as total_delivered,
                COUNT(DISTINCT pl.po_line_id || ':' || pl.po_id) as line_count
            FROM purchase_orders po
            JOIN po_lines pl ON po.po_id = pl.po_id
            LEFT JOIN line_delivered ld
              ON pl.po_line_id = ld.po_line_id
             AND pl.po_id = ld.po_id
             AND po.supplier_id = ld.supplier_id
            WHERE po.status != 'Cancelled'
              AND po.order_date <= ?
              AND po.system_available_at <= ?
              AND pl.requested_delivery_date <= ?
              AND pl.system_available_at <= ?
            GROUP BY po.supplier_id;
            """,
            (as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date, as_of_date)
        )
        capacity_map = {
            row["supplier_id"]: (
                row["total_ordered"], row["total_delivered"], row["line_count"]
            )
            for row in cursor.fetchall()
        }

        # 5. Risk Signals (Compliance & Disruption) per Supplier
        cursor.execute(
            """
            SELECT supplier_id, category, severity
            FROM risk_signals
            WHERE signal_date <= ?
              AND system_available_at <= ?;
            """,
            (as_of_date, as_of_date)
        )
        risk_map = {}
        for row in cursor.fetchall():
            sup = row["supplier_id"]
            risk_map.setdefault(sup, []).append((row["category"], row["severity"]))

        scores_data = []
        severity_penalties = SEVERITY_PENALTIES

        for sup_id in suppliers:
            # --- DELIVERY SCORE ---
            del_data = delivery_map.get(sup_id, (0, 0))
            del_total, del_on_time = del_data[0], del_data[1]
            if del_total > 0:
                delivery_score = round((del_on_time / del_total) * 100.0, 2)
                delivery_sample = del_total
                delivery_conf = "High" if delivery_sample >= 5 else "Low (Sparse Data)"
            else:
                delivery_score = NO_DATA_SCORE
                delivery_sample = 0
                delivery_conf = "No Data"

            # --- QUALITY SCORE ---
            qual_data = quality_map.get(sup_id, (0.0, 0.0, 0))
            tot_inspected, tot_defective, insp_count = qual_data[0], qual_data[1], qual_data[2]
            if tot_inspected > 0:
                defect_rate = tot_defective / tot_inspected
                quality_score = round(max(0.0, 100.0 - (defect_rate * 100.0)), 2)
                quality_sample = insp_count
                quality_conf = "High" if quality_sample >= 5 else "Low (Sparse Data)"
            else:
                quality_score = NO_DATA_SCORE
                quality_sample = 0
                quality_conf = "No Data"

            # --- COST SCORE ---
            cost_data = cost_map.get(sup_id, (0, 0))
            cost_total, cost_matching = cost_data[0], cost_data[1]
            if cost_total > 0:
                cost_score = round((cost_matching / cost_total) * 100.0, 2)
                cost_sample = cost_total
                cost_conf = "High" if cost_sample >= 3 else "Low (Sparse Data)"
            else:
                cost_score = NO_DATA_SCORE
                cost_sample = 0
                cost_conf = "No Data"

            # --- CAPACITY SCORE ---
            cap_data = capacity_map.get(sup_id, (0.0, 0.0, 0))
            cap_ordered, cap_delivered, cap_line_count = cap_data
            if cap_ordered > 0:
                fulfillment_ratio = min(1.0, cap_delivered / cap_ordered)
                capacity_score = round(fulfillment_ratio * 100.0, 2)
                capacity_sample = cap_line_count
                capacity_conf = "High" if capacity_sample >= 5 else "Low (Sparse Data)"
            else:
                capacity_score = NO_DATA_SCORE
                capacity_sample = 0
                capacity_conf = "No Data"

            # --- COMPLIANCE & DISRUPTION SCORES ---
            sup_risks = risk_map.get(sup_id, [])

            comp_signals = [sev for cat, sev in sup_risks if cat == 'Compliance']
            comp_score = NO_DATA_SCORE if not comp_signals else 100.0
            for sev in comp_signals:
                comp_score -= severity_penalties.get(sev, 15.0)
            compliance_score = max(0.0, comp_score)
            compliance_sample = len(comp_signals)
            compliance_conf = "No Data" if compliance_sample == 0 else "Medium"

            disp_signals = [sev for cat, sev in sup_risks if cat == 'Disruption']
            disp_score = NO_DATA_SCORE if not disp_signals else 100.0
            for sev in disp_signals:
                disp_score -= severity_penalties.get(sev, 15.0)
            disruption_score = max(0.0, disp_score)
            disruption_sample = len(disp_signals)
            disruption_conf = "No Data" if disruption_sample == 0 else "Medium"

            # --- FINAL WEIGHTED SCORE ---
            final_score = round(
                (delivery_score * weights["delivery"]) +
                (quality_score * weights["quality"]) +
                (cost_score * weights["cost"]) +
                (capacity_score * weights["capacity"]) +
                (compliance_score * weights["compliance"]) +
                (disruption_score * weights["disruption"]),
                2
            )

            sample_counts = [delivery_sample, quality_sample, cost_sample, compliance_sample, disruption_sample, capacity_sample]
            total_samples = sum(sample_counts)
            if total_samples >= 15:
                overall_conf = "High"
            elif total_samples >= 5:
                overall_conf = "Medium"
            else:
                overall_conf = "Low (Sparse Data)"

            score_id = f"SCR-{uuid.uuid4().hex[:8]}"
            # Exactly 23 values matching the 23 columns in supplier_scores
            scores_data.append((
                score_id, run_id, sup_id,
                delivery_score, delivery_sample, delivery_conf,
                quality_score, quality_sample, quality_conf,
                cost_score, cost_sample, cost_conf,
                capacity_score, capacity_sample, capacity_conf,
                compliance_score, compliance_sample, compliance_conf,
                disruption_score, disruption_sample, disruption_conf,
                final_score, overall_conf
            ))

        cursor.executemany(
            """
            INSERT INTO supplier_scores (
                score_id, run_id, supplier_id,
                delivery_score, delivery_sample_count, delivery_confidence,
                quality_score, quality_sample_count, quality_confidence,
                cost_score, cost_sample_count, cost_confidence,
                capacity_score, capacity_sample_count, capacity_confidence,
                compliance_score, compliance_sample_count, compliance_confidence,
                disruption_score, disruption_sample_count, disruption_confidence,
                final_score, overall_confidence_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            scores_data
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Scoring completed successfully for run_id: {run_id}")
    return run_id

if __name__ == "__main__":
    calculate_supplier_scores(as_of_date="2026-12-31")
