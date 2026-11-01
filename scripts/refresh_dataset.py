"""Regenerate, evaluate, validate, and publish one coordinated artifact set.

The active dataset and independent holdout are regenerated before the manifest
is written, so report paths and SHA-256 values describe the same refresh run.
"""
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generator import GENERATOR_VERSION, generate_synthetic_data
from src.scoring import SCORING_CONFIG_VERSION, SCORING_ENGINE_VERSION, calculate_supplier_scores
from src.export_artifacts import main as export_artifacts
from scripts.evaluate_ground_truth import evaluate as evaluate_ground_truth

DATA = ROOT / "data"
DB = DATA / "supplier_scoring.db"
EXPORTS = DATA / "exports"
SEED = 20261022
AS_OF_DATE = "2026-12-31"


def main():
    generated = generate_synthetic_data(
        db_path=DB,
        ground_truth_path=DATA / "ground_truth.json",
        malformed_path=DATA / "malformed_cases.json",
        num_suppliers=1000,
        num_pos=10000,
        num_shipments=15000,
        num_inspections=20000,
        seed=SEED,
    )

    run_id = calculate_supplier_scores(
        as_of_date=AS_OF_DATE,
        db_path=DB,
    )

    # The refresh script knows the generation seed, so it can populate this
    # field accurately. Direct scoring of an unknown database leaves it NULL.
    with sqlite3.connect(DB) as connection:
        connection.execute(
            "UPDATE score_runs SET random_seed = ? WHERE run_id = ?;",
            (SEED, run_id),
        )

    evaluation_report = evaluate_ground_truth(
        DB,
        DATA / "ground_truth.json",
        DATA / "ground_truth_evaluation.json",
    )

    # Regenerate the independent seed-20261023 report in this same refresh.
    # The exporter below will include its path and SHA-256 in the manifest.
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "evaluate_holdout.py"),
            "--output",
            str(DATA / "holdout_evaluation.json"),
        ],
        check=True,
        cwd=ROOT,
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,  # Backward-compatible data-generator version.
        "data_generator_version": GENERATOR_VERSION,
        "scoring_engine_version": SCORING_ENGINE_VERSION,
        "scoring_config_version": SCORING_CONFIG_VERSION,
        "random_seed": SEED,
        "as_of_date": AS_OF_DATE,
        "score_run_id": run_id,
        "ground_truth_evaluation": "data/ground_truth_evaluation.json",
        "ground_truth_evaluation_suppliers": evaluation_report["supplier_count_evaluated"],
        "holdout_evaluation": str((DATA / "holdout_evaluation.json").relative_to(ROOT)),
        "holdout_evaluation": "data/holdout_evaluation.json",
        "holdout_seed": 20261023,
        "generated_counts": generated,
        "historical_snapshot": None,
        "historical_files_archived": [],
    }
    (DATA / "generation_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    export_artifacts(
        db_path=DB,
        exports_dir=EXPORTS,
        validation_path=DATA / "validation_summary.json",
        manifest_path=DATA / "source_manifest.json",
    )

    validation = json.loads(
        (DATA / "validation_summary.json").read_text(encoding="utf-8")
    )
    if not validation["overall_passed"]:
        raise RuntimeError(
            "Fresh generated dataset failed validation; inspect the validation summary before publishing."
        )

    manifest_path = DATA / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generation_metadata"] = "data/generation_metadata.json"
    manifest["ground_truth_evaluation"] = "data/ground_truth_evaluation.json"
    manifest["holdout_evaluation"] = "data/holdout_evaluation.json"
    for report_name in ("ground_truth_evaluation", "holdout_evaluation"):
        report_path = DATA / f"{report_name}.json"
        if not report_path.exists():
            raise RuntimeError(f"Required evaluation report is missing: {report_path}")
        manifest[report_name] = f"data/{report_name}.json"
        manifest[f"{report_name}_sha256"] = hashlib.sha256(
            report_path.read_bytes()
        ).hexdigest()
    manifest.pop("historical_snapshot", None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    # The validation summary and source manifest are emitted by the same
    # exporter call; reject an artifact set whose timestamps have drifted.
    validation_time = datetime.fromisoformat(validation["created_at_utc"])
    manifest_time = datetime.fromisoformat(manifest["created_at_utc"])
    if abs((manifest_time - validation_time).total_seconds()) > 2:
        raise RuntimeError("Validation summary and source manifest timestamps differ by more than two seconds.")


    print(json.dumps({
        "result": "PASS",
        "archive": None,
        "archived_files": [],
        "active_database": str(DB.relative_to(ROOT)),
        "generated_counts": generated,
        "score_run_id": run_id,
        "random_seed": SEED,
        "validation_overall_passed": validation["overall_passed"],
        "validation_summary": str((DATA / "validation_summary.json").relative_to(ROOT)),
        "ground_truth_evaluation": str((DATA / "ground_truth_evaluation.json").relative_to(ROOT)),
        "ground_truth_evaluation_suppliers": evaluation_report["supplier_count_evaluated"],
    }, indent=2))


if __name__ == "__main__":
    main()
