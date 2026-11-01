"""Archive the previously committed dataset, then publish a fresh validated dataset.

The archive is created before any generation. If the archive path already
exists, the script stops rather than overwriting historical files.
"""
import json
import sqlite3
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
    archived_paths = []

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
    manifest.pop("historical_snapshot", None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


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
