# Supplier Reliability & Risk Scoring Engine

[![Python tests](https://github.com/Nandan-26/supplier-reliability-scoring/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Nandan-26/supplier-reliability-scoring/actions/workflows/tests.yml)

A Python and SQLite assessment project that generates synthetic procurement data and calculates point-in-time supplier scores across delivery, quality, cost, capacity, compliance, and disruption.

> **Scope:** This is a synthetic assessment project, not a production procurement system. Scoring weights, thresholds, and fallback values are illustrative assumptions and require business validation before operational use.

## 1. What the project does

1. Generates synthetic suppliers, sites, contracts, purchase orders, shipments, delivery events, inspections, invoices, and risk signals.
2. Stores valid baseline records in SQLite with relational constraints.
3. Detects malformed source payloads, records them in `quarantine_log`, and exports eight annotated records to `data/malformed_cases.json`: three general malformed examples plus all five labelled Round 2 edge cases. Invalid fixtures never enter clean operational or scoring tables.
4. Requires provenance on risk signals (`source`) and uses sequential `SCORE-2026-000001` identifiers for supplier score rows.
5. Calculates supplier scores for a requested as-of date.
6. Persists each scoring run and its supplier-level results.
7. Records purchase-order initial states and status transitions in `purchase_order_status_events` using SQLite triggers.
8. Exports CSV tables, a validation summary, and a source manifest.

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

The scoring function accepts an explicit `YYYY-MM-DD` as-of date. Business-event dates and `system_available_at` timestamps are both used to limit evidence to information that had occurred and was available by that date. Scoring appends a new run to the database being scored. A full data regeneration resets that database; the automated refresh workflow archives the previous database and its exports before publishing a replacement.

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

**Important:** the generator resets all generated tables in the database path passed to it, including prior `score_runs` and `supplier_scores`. Use a new database path or a verified backup when running it manually. The tracked active dataset is refreshed by GitHub Actions after relevant source/schema changes: the previous database, CSV exports, ground truth, malformed examples, validation summary and manifest are archived under `data/archive/` before the new dataset is generated. The full-data CI validator uses a separate temporary database and audits the archived snapshot without modifying it.

## 7. Run tests

```powershell
python -m pytest -v
python scripts/validate_full_dataset.py
python scripts/check_reproducibility.py
python scripts/evaluate_ground_truth.py
```

The full-dataset validator generates the 1,000-supplier dataset in a temporary directory, checks business rules, all five labelled edge-case fixtures, PO lifecycle history, profile-level ground truth, relational integrity, score ranges, and the CSV/manifest/validation exporter. CI also runs `check_reproducibility.py` at the full 1,000-supplier scale: it generates twice in isolated directories and compares every table row count, deterministic CSV SHA-256, ground-truth JSON and malformed-record JSON. `evaluate_ground_truth.py` compares expected supplier profiles with observed delivery/quality metrics and the latest score classifications, then reports differences, confusion counts, precision and recall. It then audits the active committed database and the archived pre-refresh database independently. Temporary validation files are removed; neither committed database is modified by this test.

The tests cover schema constraints, requested generation counts, reproducibility, shipment relationships, malformed-case detection, scoring ranges, missing history, point-in-time leakage, capacity aggregation, inspection aggregation, and delivery scoring. A test result applies only to the code and environment in which it was actually run.

## 8. Validation artifacts

See [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) for field-level types, nullability, enum values, units, composite uniqueness, relationships, and validation rules. The five labelled fixtures are in [`data/edge_case_fixtures.json`](data/edge_case_fixtures.json), validated by `src/edge_cases.py` and `tests/test_edge_cases.py`; the catalogue is [`data/EDGE_CASE_CATALOGUE.md`](data/EDGE_CASE_CATALOGUE.md). Metric definitions and denominators are documented in [`docs/METRICS.md`](docs/METRICS.md). Purchase-order status history is held in `purchase_order_status_events`.

`python -m src.export_artifacts` writes:
- `data/exports/*.csv` — CSV exports of database tables.
- `data/validation_summary.json` — SQLite integrity, foreign-key, expected-count, and score-range checks.
- `data/source_manifest.json` — source hashes, database hash, counts, and export paths.
- `data/ground_truth_evaluation.json` — latest-run expected-vs-observed supplier metrics, classification comparison, and binary at-risk confusion counts; the prior report is archived before each refresh.

Historical score anomalies are retained for traceability and are documented in [the historical score anomaly report](data/historical_score_anomalies.md). A latest scoring run can pass while the overall historical validation remains failed; inspect the individual checks rather than treating the latest-run result as a complete pass.

## 9. Repository layout

```text
supplier-reliability-scoring/
├── data/
│   ├── archive/
│   │   └── pre_refresh_20261031T203556Z/
│   ├── exports/
│   ├── schema.sql
│   ├── DATA_DICTIONARY.md
│   ├── generation_metadata.json
│   ├── ground_truth.json
│   ├── malformed_cases.json
│   ├── supplier_scoring.db
│   ├── validation_summary.json
│   └── source_manifest.json
├── scripts/
│   ├── refresh_dataset.py
│   └── validate_full_dataset.py
├── src/
│   ├── db.py
│   ├── generator.py
│   ├── scoring.py
│   └── export_artifacts.py
├── tests/
│   ├── test_db.py
│   ├── test_generator.py
│   └── test_scoring.py
├── .github/workflows/
│   ├── tests.yml
│   └── refresh_dataset.yml
├── requirements.txt
└── README.md
```

## 10. Current dataset and historical archive

The active `data/supplier_scoring.db` and `data/exports/` contain a fresh validated dataset generated with seed `20261022`. The run metadata is in `data/generation_metadata.json`; the validation result is in `data/validation_summary.json`; source hashes and export paths are in `data/source_manifest.json`.

The previous committed dataset is preserved under `data/archive/pre_refresh_20261031T203556Z/`. Its legacy issues are summarized in [the historical archive report](data/historical_score_anomalies.md) and its original detailed report remains inside the archive. Do not use those legacy scores as current normalized scores.

## 11. Limitations

- All source records are synthetic; they do not establish real supplier performance.
- The scoring weights and penalty values are assumptions, not calibrated policy.
- Confidence is a simple heuristic and should not be treated as a statistical confidence interval.
- The quarantine log stores three general malformed examples plus five labelled challenge edge cases; it is a reproducible assessment fixture, not a general-purpose production ingestion or remediation queue.
- The invoice model is simplified and does not represent every real-world advance-billing, credit-note, or multi-stage payment workflow.
- A production implementation would need access controls, audit logging, data-retention policies, monitoring, policy ownership, and human review of consequential supplier decisions.
