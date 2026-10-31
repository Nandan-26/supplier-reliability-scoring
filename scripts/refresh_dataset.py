"""Archive the previously committed dataset, then publish a fresh validated dataset.

The archive is created before any generation. If the archive path already
exists, the script stops rather than overwriting historical files.
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores
from src.export_artifacts import main as export_artifacts

DATA = ROOT / "data"
DB = DATA / "supplier_scoring.db"
EXPORTS = DATA / "exports"
SEED = 20261022
AS_OF_DATE = "2026-12-31"


def archive_existing_dataset():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = DATA / "archive" / f"pre_refresh_{stamp}"
    archive.mkdir(parents=True, exist_ok=False)

    paths = [
        DB,
        EXPORTS,
        DATA / "ground_truth.json",
        DATA / "malformed_cases.json",
        DATA / "validation_summary.json",
        DATA / "source_manifest.json",
        DATA / "historical_score_anomalies.md",
    ]
    moved = []
    for source in paths:
        if source.exists():
            destination = archive / source.name
            shutil.move(str(source), str(destination))
            moved.append(str(destination.relative_to(ROOT)))

    return archive, moved


def main():
    archive, archived_paths = archive_existing_dataset()

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

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator_version": "1.1.0",
        "scoring_config_version": "v1.1",
        "random_seed": SEED,
        "as_of_date": AS_OF_DATE,
        "score_run_id": run_id,
        "generated_counts": generated,
        "historical_snapshot": str(archive.relative_to(ROOT)),
        "historical_files_archived": archived_paths,
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
            "Fresh dataset failed validation; the historical snapshot remains "
            f"preserved at {archive.relative_to(ROOT)}."
        )

    manifest_path = DATA / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generation_metadata"] = "data/generation_metadata.json"
    manifest["historical_snapshot"] = str(archive.relative_to(ROOT))
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    historical_report = f"""# Historical Dataset Archive

The previous committed database and exports were preserved before the active dataset was regenerated.

- Archive directory: `{archive.relative_to(ROOT).as_posix()}`
- Archived files: {len(archived_paths)}
- Active database: `data/supplier_scoring.db`
- Active dataset seed: `{SEED}`
- Active scoring run: `{run_id}`

The archive contains the previous SQLite database, CSV exports, ground-truth file, malformed-case file, validation summary, source manifest, and historical anomaly report. The archive is retained for audit and comparison; it is not used for current scoring.

The active dataset passed SQLite integrity, foreign-key, expected-count, business-rule, historical score-range, and latest-run validation.
"""
    (DATA / "historical_score_anomalies.md").write_text(
        historical_report,
        encoding="utf-8",
    )

    print(json.dumps({
        "result": "PASS",
        "archive": str(archive.relative_to(ROOT)),
        "archived_files": archived_paths,
        "active_database": str(DB.relative_to(ROOT)),
        "generated_counts": generated,
        "score_run_id": run_id,
        "random_seed": SEED,
        "validation_overall_passed": validation["overall_passed"],
        "validation_summary": str((DATA / "validation_summary.json").relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
