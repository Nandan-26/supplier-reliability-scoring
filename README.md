# Supplier Reliability & Risk Scoring Engine

<p align="center">
  <strong>A reproducible supplier risk analytics pipeline built with Python and SQLite.</strong><br/>
  Generate procurement data, validate relationships, score suppliers as of a historical date, and evaluate risk decisions against separate synthetic labels.
</p>

<p align="center">
  <a href="https://github.com/Nandan-26/supplier-reliability-scoring/actions/workflows/tests.yml"><img src="https://github.com/Nandan-26/supplier-reliability-scoring/actions/workflows/tests.yml/badge.svg?branch=main" alt="Python tests"/></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/Tests-55%20passing-2ea44f" alt="55 tests passed in local fresh-clone verification"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"/></a>
</p>

**Supplier Reliability Scoring** evaluates procurement partners across delivery, quality, cost, capacity, compliance, and disruption. The engine combines point-in-time data selection, relational integrity rules, evidence-aware decisions, and reproducible evaluation.

> **Important scope note:** This is a synthetic assessment project, not a production procurement system. The reported precision and recall measure agreement with generated labels; they do not establish performance on real supplier data. Scoring weights and guardrails are illustrative business rules that require domain validation before operational use.

## Project at a glance

| Dataset / engineering evidence | Current project result |
|---|---:|
| Synthetic suppliers | 1,000 |
| Purchase orders | 10,000 |
| Shipments | 15,000 |
| Inspection records | 20,000 |
| Automated tests | 55 passed locally in a fresh clone |
| Supplier score dimensions | 6 |
| Labelled challenge edge cases | 5 |

### Evaluation highlights

| Evaluation set | Seed | Precision | Recall |
|---|---:|---:|---:|
| Active synthetic dataset | 20261022 | **95.73%** | **95.25%** |
| Independent synthetic holdout | 20261023 | **96.94%** | **95.00%** |

The two evaluation sets are independent and must not be combined. See the detailed [evaluation artifacts](#evaluation-results) and [limitations](#11-limitations).

### Visual walkthrough

<p align="center">
  <img src="docs/images/architecture.svg" alt="Supplier scoring architecture" width="100%"/>
</p>

### Quick links

- [Setup and run](#5-setup)
- [Scoring methodology](#2-scoring-dimensions)
- [Validation and evaluation](#8-validation-artifacts)
- [Data dictionary](data/DATA_DICTIONARY.md)
- [Metric definitions](docs/METRICS.md)
- [Five labelled edge cases](data/EDGE_CASE_CATALOGUE.md)
- [Contributing](CONTRIBUTING.md)
- [License](LICENSE)

## Architecture

The architecture diagram above shows the flow from generated procurement records through validation, SQLite persistence, scoring guardrails, and independent evaluation.

## 1. What the project does

1. Generates synthetic suppliers, sites, contracts, purchase orders, shipments, delivery events, inspections, invoices, and risk signals.
2. Stores valid baseline records in SQLite with relational constraints.
3. Detects malformed source payloads, records them in `quarantine_log`, and exports eight annotated records to `data/malformed_cases.json`: three general malformed examples plus all five labelled Round 2 edge cases. Invalid fixtures never enter clean operational or scoring tables.
4. Requires provenance on risk signals (`source`) and uses sequential `SCORE-2026-000001` identifiers for supplier score rows.
5. Calculates supplier scores for a requested as-of date.
6. Applies explicit delivery and quality risk guardrails before the composite score bands, so a strong unrelated dimension cannot hide a serious failure.
7. Persists each scoring run and its supplier-level results.
8. Records purchase-order initial states and status transitions in `purchase_order_status_events` using SQLite triggers.
9. Exports CSV tables, a validation summary, and a source manifest.

## 2. Scoring dimensions

| Dimension | Weight | Intended meaning |
|---|---:|---|
| Delivery | 25% | Share of eligible PO lines fulfilled on time |
| Quality | 25% | Defect-free share of inspected quantity |
| Cost | 15% | Invoice unit-price adherence to the PO line price |
| Capacity | 15% | Delivered quantity relative to ordered quantity |
| Compliance | 10% | Penalties for recorded compliance risk signals |
| Disruption | 10% | Penalties for recorded disruption risk signals |

Scores are intended to remain between 0 and 100. Cost measures adherence to the agreed PO price, not whether a supplier is inexpensive. Missing evidence is not proof of good performance: dimension scores must be interpreted together with sample counts and confidence labels. All six dimensions use a neutral 50-point fallback with `No Data` confidence when no evidence is available. For observed records, dimension confidence is based on evidence counts (delivery/quality/capacity/risk: 5 or more for High; cost: 3 or more for High); the overall confidence tier uses the combined sample-count heuristic (15 or more High, 5–14 Medium, otherwise Low/Sparse). These are project heuristics, not statistical confidence intervals.

## 3. Point-in-time scoring

The scoring function accepts an explicit `YYYY-MM-DD` as-of date. Business-event dates and `system_available_at` timestamps are both used to limit evidence to information that had occurred and was available by that date. Scoring appends a new run to the database being scored. A full data regeneration resets the target database. The automated refresh workflow regenerates the SQLite database locally and commits reproducible CSV/JSON artifacts; the generated `.db` file is intentionally excluded from Git to keep the repository lightweight.

## 4. Data-generation rules

- Purchase orders are either cancelled or initially issued. Cancelled orders are excluded from shipment generation.
- Fulfilled status is derived after shipment generation when every PO line has been shipped in full. Incomplete non-cancelled orders remain issued.
- SQLite triggers enforce cumulative shipment quantities per PO line, cumulative receipt quantities per shipment, cumulative inspected quantities per delivery, and cumulative invoiced quantities per PO line. They also block shipments for cancelled POs and invoices dated before the latest delivery on the PO.
- Inspection records are treated as disjoint inspection lots. For each delivery event, the sum of inspected quantities is limited to the received quantity.
- Invoices are generated only for non-cancelled POs with delivery evidence. Invoice lines use delivered quantities, and the invoice date is no earlier than the latest delivery on that PO.
- Detected malformed challenge examples are written to `quarantine_log` with their raw payload and reasons, and are also exported to `data/malformed_cases.json`.

The requested inspection count is distributed across generated delivery events. When more inspections than deliveries are requested, each delivery is split into multiple quantity lots rather than inspected repeatedly at its full quantity.

## 5. Setup

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 6. Generate data and score suppliers

Run commands from the repository root.

```powershell
python -c "from src.generator import generate_synthetic_data; print(generate_synthetic_data())"
python -c "from src.scoring import calculate_supplier_scores; print(calculate_supplier_scores(as_of_date='2026-12-31'))"
python -m src.export_artifacts
```

**Important:** the generator resets all generated tables in the database path passed to it, including prior `score_runs` and `supplier_scores`. Use a new database path or a verified backup when running it manually. The active dataset artifacts are refreshed by GitHub Actions after relevant source/schema changes. The workflow regenerates the SQLite database for validation but commits only the reproducible CSV/JSON artifacts; it does not create or commit historical database snapshots. The full-data CI validator uses a separate temporary database.

## 7. Run tests

```powershell
python -m pytest -v
python scripts/validate_full_dataset.py
python scripts/check_reproducibility.py
python scripts/evaluate_ground_truth.py
```

The full-dataset validator generates the 1,000-supplier dataset in a temporary directory, checks business rules, all five labelled edge-case fixtures, PO lifecycle history, profile-level ground truth, relational integrity, score ranges, and the CSV/manifest/validation exporter. CI also runs `check_reproducibility.py` at the full 1,000-supplier scale: it generates twice in isolated directories and compares every table row count, deterministic CSV SHA-256, ground-truth JSON and malformed-record JSON. `evaluate_ground_truth.py` compares expected supplier profiles with observed delivery/quality metrics and the latest score classifications, then reports differences, confusion counts, precision and recall. The independent holdout evaluator uses a separate seed and dataset. Temporary validation files are removed; validation databases are isolated from the repository's generated artifacts.

The independent holdout check generates a separate 1,000-supplier dataset with seed `20261023` and evaluates the fixed observed-delivery (<75) and observed-quality (<90) risk guardrails without tuning them on the committed seed. CI requires at least 90% precision and 90% recall on that holdout. The committed result and confusion counts are documented separately below. The tests cover schema constraints, requested generation counts, reproducibility, shipment relationships, malformed-case detection, scoring ranges, missing history, point-in-time leakage, capacity aggregation, inspection aggregation, and delivery scoring. A test result applies only to the code and environment in which it was actually run.

## Evaluation results

The following figures are read from the committed active-dataset and retained independent-holdout JSON reports. The active dataset uses seed `20261022`; the separate holdout uses seed `20261023`.

![Synthetic evaluation metrics](docs/images/evaluation-snapshot.svg)

| Evaluation set | True positive | False positive | True negative | False negative |
|---|---:|---:|---:|---:|
| Active dataset (seed 20261022) | 381 | 17 | 583 | 19 |
| Independent holdout (seed 20261023) | 380 | 12 | 588 | 20 |

Do not merge these counts because the reports evaluate different generated datasets. Each refresh regenerates both reports before exporting the source manifest, which records each report path and SHA-256 checksum. The validation summary and source manifest are emitted by the same export pass and their timestamps are checked for consistency.

## Sample supplier decisions

The preview below uses rows from the committed `supplier_scores.csv` and `supplier_decisions.csv` exports. It intentionally includes a supplier with a high composite score but insufficient delivery evidence to demonstrate why evidence guardrails matter.

![Supplier score sample](docs/images/supplier-score-sample.svg)

For the complete data, inspect [supplier_scores.csv](data/exports/supplier_scores.csv) and [supplier_decisions.csv](data/exports/supplier_decisions.csv).

## 8. Validation artifacts

See [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) for field-level types, nullability, enum values, units, composite uniqueness, relationships, and validation rules. The five labelled fixtures are in [`data/edge_case_fixtures.json`](data/edge_case_fixtures.json), validated by `src/edge_cases.py` and `tests/test_edge_cases.py`; the catalogue is [`data/EDGE_CASE_CATALOGUE.md`](data/EDGE_CASE_CATALOGUE.md). Metric definitions and denominators are documented in [`docs/METRICS.md`](docs/METRICS.md). Purchase-order status history is held in `purchase_order_status_events`. Operational decisions (`Reliable`, `Watch`, `At Risk`, `Insufficient Evidence`) and their explanations are persisted in `supplier_decisions` for each scoring result.

`python -m src.export_artifacts` writes:
- `data/exports/*.csv` — CSV exports of database tables.
- `data/validation_summary.json` — SQLite integrity, foreign-key, expected-count, and score-range checks.
- `data/source_manifest.json` — source and evaluation-artifact SHA-256 hashes, database hash, table counts, and export paths.
- `data/ground_truth_evaluation.json` — current active-dataset expected-vs-observed supplier metrics, classification comparison, and binary at-risk confusion counts.
- `data/holdout_evaluation.json` — a retained historical holdout snapshot. For current results, use the fresh `holdout_evaluation.json` attached to the latest successful `Python tests` workflow run.
### Active-dataset classification evaluation

The committed active dataset uses seed `20261022` and contains 1,000 synthetic suppliers. Its current evaluation report (`data/ground_truth_evaluation.json`) records the following binary `At Risk` results:

| Metric | Result |
|---|---:|
| True positives | 381 |
| False positives | 17 |
| True negatives | 583 |
| False negatives | 19 |
| Precision | 95.73% |
| Recall | 95.25% |

These metrics measure agreement with the generator's synthetic ground-truth labels, not performance on real procurement data. The independent holdout uses a separate seed and is evaluated separately; do not combine the two confusion matrices.

Historical score anomalies are retained for traceability and are documented in [the historical score anomaly report](data/historical_score_anomalies.md). A latest scoring run can pass while a legacy validation report contains failures; inspect the individual checks rather than treating an old report as a current failure.

### Independent holdout evaluation

The independent holdout is a second synthetic dataset, generated in CI with seed `20261023` (1,000 suppliers). It is not the active committed database, which was generated with seed `20261022`. The fixed guardrail policy was evaluated without using ground-truth labels as scoring features and without tuning the thresholds on the holdout labels.

The CI workflow regenerates the active-dataset evaluation, full-scale reproducibility report, and independent holdout on every pull request. The workflow publishes the holdout JSON and reproducibility JSON together in the `supplier-risk-v2-evaluation-reports` artifact. Each fresh holdout report records the scoring-engine version, scoring-policy version, and GitHub Actions run/commit provenance. Use the artifact attached to the latest successful run; the committed `data/holdout_evaluation.json` is retained only as a historical snapshot. The active dataset (seed `20261022`) and holdout (seed `20261023`) are different synthetic datasets. Never combine their confusion counts or compare results across policy versions. Neither evaluation establishes performance on real supplier data.

## 9. Repository layout

```text
supplier-reliability-scoring/
├── .github/
│   └── workflows/
│       ├── refresh_dataset.yml
│       └── tests.yml
├── data/
│   ├── exports/                         # CSV exports for the active dataset
│   ├── DATA_DICTIONARY.md
│   ├── EDGE_CASE_CATALOGUE.md
│   ├── edge_case_fixtures.json
│   ├── generation_metadata.json
│   ├── ground_truth.json
│   ├── ground_truth_evaluation.json
│   ├── historical_score_anomalies.md
│   ├── holdout_evaluation.json
│   ├── malformed_cases.json
│   ├── schema.sql
│   ├── source_manifest.json
│   └── validation_summary.json
├── docs/
│   └── METRICS.md
├── scripts/
│   ├── check_reproducibility.py
│   ├── evaluate_ground_truth.py
│   ├── evaluate_holdout.py
│   ├── refresh_dataset.py
│   └── validate_full_dataset.py
├── src/
│   ├── db.py
│   ├── edge_cases.py
│   ├── export_artifacts.py
│   ├── generator.py
│   └── scoring.py
├── tests/
│   ├── test_db.py
│   ├── test_edge_cases.py
│   ├── test_generator.py
│   ├── test_ground_truth_evaluation.py
│   ├── test_lifecycle_events.py
│   ├── test_reproducibility.py
│   └── test_scoring.py
├── requirements.txt
└── README.md
```

## 10. Current generated dataset

The generated `data/supplier_scoring.db` (created locally and in CI, but not committed) and committed `data/exports/` correspond to a dataset generated with seed `20261022`. Refresh metadata distinguishes the synthetic data-generator version from the scoring-engine and scoring-policy versions. The run metadata is in `data/generation_metadata.json`; the validation result is in `data/validation_summary.json`; source hashes and export paths are in `data/source_manifest.json`.

No generated SQLite database or historical dataset archive is committed. The database is rebuilt locally and in CI from the versioned generator and seed; the reproducible CSV/JSON exports in `data/` describe the active synthetic dataset. Historical score anomalies from earlier development runs are summarized in [the historical score anomaly report](data/historical_score_anomalies.md) and should not be interpreted as current normalized scores.

## 11. Limitations

- All source records are synthetic; they do not establish real supplier performance.
- The scoring weights and severity penalties are assumptions, not calibrated policy. No adverse compliance/disruption signals receive 100 for that dimension; a recorded signal applies a severity-based penalty. A missing signal means no adverse signal was recorded, not proof of zero risk.
- Confidence is a simple heuristic and should not be treated as a statistical confidence interval.
- The quarantine log stores three general malformed examples plus five labelled challenge edge cases; it is a reproducible assessment fixture, not a general-purpose production ingestion or remediation queue.
- The invoice model is simplified and does not represent every real-world advance-billing, credit-note, or multi-stage payment workflow.
- The generated PO activity window is intentionally limited to a short synthetic period; it is suitable for deterministic validation but does not demonstrate long-term supplier deterioration. The `Watch` class is rare in the current generated sample because the illustrative policy prioritizes clear risk guardrails; its low frequency should not be interpreted as a real-world prevalence estimate.
- No explicit many-to-many relationship is currently modeled. If supplier-to-item eligibility is added, represent it with a supplier-item bridge table.
- A production implementation would need access controls, audit logging, data-retention policies, monitoring, policy ownership, and human review of consequential supplier decisions.


**Synthetic-data caveat:** The generator's profile mix includes 40% adverse-profile suppliers and 10% sparse-history suppliers. This is a deliberately constructed test distribution, not an estimate of real-world supplier risk prevalence. Sparse-history suppliers must meet the minimum of five delivery observations and five quality observations before receiving a firm Reliable/Watch/At Risk decision.
