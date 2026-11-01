"""Compare generated supplier profiles with observed metrics and the latest scores."""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def classify(score, confidence, delivery_score, quality_score, delivery_sample_count, quality_sample_count):
    """Apply explicit dimension guardrails before the composite score bands.

    A strong result in unrelated dimensions must not hide a serious delivery
    or quality failure. These fixed business-rule thresholds are not fitted
    to the evaluation labels.
    """
    if confidence == "Low (Sparse Data)":
        return "Insufficient Evidence"
    if (
        (delivery_sample_count > 0 and delivery_score < 75)
        or (quality_sample_count > 0 and quality_score < 90)
    ):
        return "At Risk"
    if score >= 80:
        return "Reliable"
    return "Watch"


def evaluate(db_path, ground_truth_path, output_path):
    truth = json.loads(Path(ground_truth_path).read_text(encoding="utf-8"))
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        run = con.execute(
            "SELECT run_id, as_of_date FROM score_runs ORDER BY run_timestamp DESC, rowid DESC LIMIT 1"
        ).fetchone()
        if run is None:
            raise RuntimeError("No scoring run found. Score the database before evaluation.")
        rows = con.execute("""
            WITH line_delivery AS (
                SELECT po.supplier_id, pl.po_id, pl.po_line_id, pl.ordered_qty,
                       pl.requested_delivery_date,
                       COALESCE(MAX(de.actual_delivery_date), '9999-12-31') AS final_delivery_date,
                       SUM(CASE WHEN de.actual_delivery_date <= pl.requested_delivery_date
                                THEN de.delivered_qty ELSE 0 END) AS delivered_on_time_qty
                FROM purchase_orders po
                JOIN po_lines pl ON pl.po_id = po.po_id
                LEFT JOIN shipments s ON s.po_id = pl.po_id AND s.po_line_id = pl.po_line_id
                     AND s.system_available_at <= ?
                LEFT JOIN delivery_events de ON de.shipment_id = s.shipment_id
                     AND de.actual_delivery_date <= ? AND de.system_available_at <= ?
                WHERE po.status <> 'Cancelled'
                  AND po.order_date <= ? AND po.system_available_at <= ?
                  AND pl.requested_delivery_date <= ? AND pl.system_available_at <= ?
                GROUP BY po.supplier_id, pl.po_id, pl.po_line_id
            ),
            delivery AS (
                SELECT supplier_id,
                       SUM(CASE WHEN final_delivery_date <= requested_delivery_date
                                     OR delivered_on_time_qty >= ordered_qty
                                THEN 1 ELSE 0 END) AS on_time_lines,
                       COUNT(*) AS total_lines
                FROM line_delivery GROUP BY supplier_id
            ),
            quality AS (
                SELECT po.supplier_id, SUM(i.defective_qty) AS defective,
                       SUM(i.inspected_qty) AS inspected
                FROM purchase_orders po
                JOIN shipments s ON s.po_id = po.po_id
                JOIN delivery_events de ON de.shipment_id = s.shipment_id
                JOIN inspections i ON i.delivery_event_id = de.delivery_event_id
                WHERE po.order_date <= ? AND po.system_available_at <= ?
                  AND s.system_available_at <= ?
                  AND de.actual_delivery_date <= ? AND de.system_available_at <= ?
                  AND i.inspection_date <= ? AND i.system_available_at <= ?
                GROUP BY po.supplier_id
            )
            SELECT ss.supplier_id, ss.final_score, ss.overall_confidence_tier,\n                   sd.classification AS persisted_classification,\n                   sd.decision_reason,
                   ss.delivery_score, ss.quality_score,
                   COALESCE(1.0 * d.on_time_lines / NULLIF(d.total_lines, 0), 0) AS observed_on_time_rate,
                   COALESCE(q.defective / NULLIF(q.inspected, 0), 0) AS observed_defect_rate,
                   ss.delivery_sample_count, ss.quality_sample_count
            FROM supplier_scores ss
            LEFT JOIN delivery d ON d.supplier_id = ss.supplier_id
            LEFT JOIN quality q ON q.supplier_id = ss.supplier_id
            WHERE ss.run_id = ?
            ORDER BY ss.supplier_id
        """, (run["as_of_date"],) * 7 + (run["as_of_date"],) * 7 + (run["run_id"],)).fetchall()

        details = []
        tp = fp = tn = fn = 0
        delivery_abs_errors = []
        defect_abs_errors = []
        for row in rows:
            expected = truth.get(row["supplier_id"])
            if expected is None:
                continue
            expected_profile = expected["profile"]
            expected_class = {
                "reliable": "Reliable",
                "worsening_delivery": "At Risk",
                "quality_issues": "At Risk",
                "sparse_history": "Insufficient Evidence",
            }.get(expected_profile, "Unlabelled")
            actual_class = row["persisted_classification"]
            expected_risk = expected_class == "At Risk"
            actual_risk = actual_class == "At Risk"
            if expected_risk and actual_risk: tp += 1
            elif not expected_risk and actual_risk: fp += 1
            elif not expected_risk and not actual_risk: tn += 1
            else: fn += 1

            expected_delivery = expected.get("expected_on_time_rate")
            expected_defect = expected.get("expected_defect_rate")
            observed_delivery = row["observed_on_time_rate"]
            observed_defect = row["observed_defect_rate"]
            if expected_delivery is not None and row["delivery_sample_count"]:
                delivery_abs_errors.append(abs(observed_delivery - expected_delivery))
            if expected_defect is not None and row["quality_sample_count"]:
                defect_abs_errors.append(abs(observed_defect - expected_defect))
            details.append({
                "supplier_id": row["supplier_id"],
                "expected_profile": expected_profile,
                "expected_classification": expected_class,
                "actual_classification": actual_class,
                "final_score": row["final_score"],
                "overall_confidence": row["overall_confidence_tier"],
                "expected_on_time_rate": expected_delivery,
                "observed_on_time_rate": round(observed_delivery, 6),
                "on_time_rate_difference": None if expected_delivery is None else round(observed_delivery - expected_delivery, 6),
                "expected_defect_rate": expected_defect,
                "observed_defect_rate": round(observed_defect, 6),
                "defect_rate_difference": None if expected_defect is None else round(observed_defect - expected_defect, 6),
            })

        total = len(details)
        report = {
            "run_id": run["run_id"],
            "as_of_date": run["as_of_date"],
            "classification_policy": {\n                "source": "Persisted supplier_decisions rows created by src.scoring",
                "At Risk": "observed delivery_score < 75 OR observed quality_score < 90, unless confidence is Low (Sparse Data); No Data fallbacks do not trigger a guardrail",
                "Reliable": "final_score >= 80 and neither dimension guardrail is breached",
                "Watch": "no dimension guardrail breached and final_score < 80",
                "Insufficient Evidence": "overall confidence is Low (Sparse Data)",
                "policy_note": "Dimension guardrails are fixed domain rules, not thresholds optimized against the reported evaluation set.",
            },
            "supplier_count_evaluated": total,
            "expected_vs_observed_mean_absolute_error": {
                "on_time_rate": None if not delivery_abs_errors else round(sum(delivery_abs_errors) / len(delivery_abs_errors), 6),
                "defect_rate": None if not defect_abs_errors else round(sum(defect_abs_errors) / len(defect_abs_errors), 6),
                "on_time_supplier_count": len(delivery_abs_errors),
                "quality_supplier_count": len(defect_abs_errors),
            },
            "at_risk_binary_evaluation": {
                "positive_class": "At Risk (worsening_delivery or quality_issues)",
                "true_positive": tp, "false_positive": fp,
                "true_negative": tn, "false_negative": fn,
                "precision": None if tp + fp == 0 else round(tp / (tp + fp), 4),
                "recall": None if tp + fn == 0 else round(tp / (tp + fn), 4),
            },
            "classification_counts": {
                label: sum(1 for item in details if item["actual_classification"] == label)
                for label in ("Reliable", "Watch", "At Risk", "Insufficient Evidence")
            },
            "suppliers": details,
            "ground_truth_used_as_features": False,
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "suppliers"}, indent=2))
        return report
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT / "data" / "supplier_scoring.db"))
    parser.add_argument("--ground-truth", default=str(ROOT / "data" / "ground_truth.json"))
    parser.add_argument("--output", default=str(ROOT / "data" / "ground_truth_evaluation.json"))
    args = parser.parse_args()
    evaluate(args.db, args.ground_truth, args.output)
