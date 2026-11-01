"""Evaluate the fixed risk guardrails on a separate deterministic seed.

This holdout is generated independently from the committed seed. The risk
thresholds are predeclared business rules in evaluate_ground_truth.py; this
script does not tune them against the holdout labels.
"""
import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores
from scripts.evaluate_ground_truth import evaluate

SEED = 20261023
AS_OF_DATE = "2026-12-31"


def main():
    with tempfile.TemporaryDirectory(prefix="supplier-risk-holdout-") as tmp:
        root = Path(tmp)
        db_path = root / "holdout.db"
        truth_path = root / "ground_truth.json"
        malformed_path = root / "malformed_cases.json"
        report_path = root / "evaluation.json"

        counts = generate_synthetic_data(
            db_path=db_path,
            ground_truth_path=truth_path,
            malformed_path=malformed_path,
            num_suppliers=1000,
            num_pos=10000,
            num_shipments=15000,
            num_inspections=20000,
            seed=SEED,
        )
        run_id = calculate_supplier_scores(
            as_of_date=AS_OF_DATE,
            db_path=db_path,
        )
        report = evaluate(db_path, truth_path, report_path)
        metrics = report["at_risk_binary_evaluation"]
        result = {
            "holdout_seed": SEED,
            "supplier_count": report["supplier_count_evaluated"],
            "run_id": run_id,
            "generated_counts": counts,
            "classification_policy": report["classification_policy"],
            "at_risk_binary_evaluation": metrics,
            "classification_counts": report["classification_counts"],
            "ground_truth_used_as_features": report["ground_truth_used_as_features"],
        }
        print(json.dumps(result, indent=2))

        if report["supplier_count_evaluated"] != 1000:
            raise SystemExit("Holdout must evaluate all 1,000 suppliers.")
        if report["ground_truth_used_as_features"]:
            raise SystemExit("Ground truth must not be used as scoring features.")
        if metrics["recall"] is None or metrics["recall"] < 0.90:
            raise SystemExit("Holdout recall is below the 0.90 acceptance target.")
        if metrics["precision"] is None or metrics["precision"] < 0.90:
            raise SystemExit("Holdout precision is below the 0.90 acceptance target.")


if __name__ == "__main__":
    main()
