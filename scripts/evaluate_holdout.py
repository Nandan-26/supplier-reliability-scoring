"""Evaluate fixed risk guardrails on an independent deterministic synthetic seed.

The holdout is generated separately from the committed dataset. Thresholds are
predeclared business rules and are not tuned against holdout labels.
"""
import argparse
import json
import os
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator import generate_synthetic_data
from src.scoring import SCORING_CONFIG_VERSION, SCORING_ENGINE_VERSION, calculate_supplier_scores
from scripts.evaluate_ground_truth import evaluate

SEED = 20261023
AS_OF_DATE = "2026-12-31"
MINIMUM_PRECISION = 0.90
MINIMUM_RECALL = 0.90


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the machine-readable holdout report.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="supplier-risk-holdout-") as tmp:
        root = Path(tmp)
        db_path = root / "holdout.db"
        truth_path = root / "ground_truth.json"
        malformed_path = root / "malformed_cases.json"
        evaluation_path = root / "evaluation.json"

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
        report = evaluate(db_path, truth_path, evaluation_path)
        metrics = report["at_risk_binary_evaluation"]
        result = {
            "evaluation_type": "independent_synthetic_holdout",
            "holdout_seed": SEED,
            "supplier_count": report["supplier_count_evaluated"],
            "run_id": run_id,
            "scoring_engine_version": SCORING_ENGINE_VERSION,
            "scoring_config_version": SCORING_CONFIG_VERSION,
            "generated_counts": counts,
            "classification_policy": report["classification_policy"],
            "at_risk_binary_evaluation": metrics,
            "classification_counts": report["classification_counts"],
            "ground_truth_used_as_features": report["ground_truth_used_as_features"],
            "ci_acceptance_thresholds": {
                "minimum_precision": MINIMUM_PRECISION,
                "minimum_recall": MINIMUM_RECALL,
                "passed": (
                    metrics["precision"] is not None
                    and metrics["recall"] is not None
                    and metrics["precision"] >= MINIMUM_PRECISION
                    and metrics["recall"] >= MINIMUM_RECALL
                ),
            },
        }

        run_id_env = os.getenv("GITHUB_RUN_ID")
        if run_id_env:
            server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
            repository = os.getenv("GITHUB_REPOSITORY", "")
            result["source_workflow"] = {
                "name": os.getenv("GITHUB_WORKFLOW"),
                "run_number": int(os.environ["GITHUB_RUN_NUMBER"]) if os.getenv("GITHUB_RUN_NUMBER") else None,
                "run_id": int(run_id_env),
                "commit": os.getenv("GITHUB_SHA"),
                "url": f"{server}/{repository}/actions/runs/{run_id_env}",
            }

        serialized = json.dumps(result, indent=2)
        print(serialized)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")

        if report["supplier_count_evaluated"] != 1000:
            raise SystemExit("Holdout must evaluate all 1,000 suppliers.")
        if report["ground_truth_used_as_features"]:
            raise SystemExit("Ground truth must not be used as scoring features.")
        if not result["ci_acceptance_thresholds"]["passed"]:
            raise SystemExit("Holdout precision or recall is below the 0.90 acceptance target.")


if __name__ == "__main__":
    main()
