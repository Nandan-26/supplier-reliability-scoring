from pathlib import Path

from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores
from scripts.evaluate_ground_truth import evaluate

DB = Path("data/test_evaluation.db")
GT = Path("data/test_evaluation_ground_truth.json")
MAL = Path("data/test_evaluation_malformed.json")
OUT = Path("data/test_evaluation_report.json")


def test_ground_truth_evaluation_reports_metrics_and_confusion_counts():
    generate_synthetic_data(
        db_path=DB, ground_truth_path=GT, malformed_path=MAL,
        num_suppliers=40, num_pos=100, num_shipments=150,
        num_inspections=200, seed=20261022,
    )
    calculate_supplier_scores(as_of_date="2026-12-31", db_path=DB)
    report = evaluate(DB, GT, OUT)
    assert report["supplier_count_evaluated"] == 40
    assert report["ground_truth_used_as_features"] is False
    assert set(report["at_risk_binary_evaluation"]) >= {
        "true_positive", "false_positive", "true_negative", "false_negative",
        "precision", "recall"
    }
    assert len(report["suppliers"]) == 40
    for path in (DB, GT, MAL, OUT):
        if path.exists():
            path.unlink()
