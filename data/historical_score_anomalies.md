# Historical Dataset Archive and Anomaly Record

## Immediately preceding active dataset

Before the latest dataset refresh, the previously committed SQLite database and its matching CSV exports were preserved unchanged at:

- Archive: [`data/archive/pre_refresh_20261101T081036Z/`](archive/pre_refresh_20261101T081036Z/)
- Archived database: [`supplier_scoring.db`](archive/pre_refresh_20261101T081036Z/supplier_scoring.db)
- Archived exports: [`exports/`](archive/pre_refresh_20261101T081036Z/exports/)
- Archived ground truth, malformed cases, validation summary, source manifest, generation metadata, and ground-truth evaluation are retained in the same directory.

The active dataset is now regenerated with seed `20261022`. Its run ID, generator/scoring versions, and archive path are recorded in `data/generation_metadata.json`. The matching database hash, source hashes, row counts, and export paths are recorded in `data/source_manifest.json`.

## Earlier legacy anomaly baseline

An earlier dataset with known historical anomalies remains preserved at [`data/archive/pre_refresh_20261031T203556Z/`](archive/pre_refresh_20261031T203556Z/). Its detailed original report is available at [`historical_score_anomalies.md`](archive/pre_refresh_20261031T203556Z/historical_score_anomalies.md).

The legacy baseline had the following recorded issues:

- 776 cancelled purchase orders with shipments
- 248 cancelled purchase orders with invoices
- 3,967 fulfilled purchase orders with incomplete shipped quantities
- 5,000 deliveries with inspection quantities above received quantity
- 2,831 invoice lines above delivered quantity
- 1,161 invoices dated before the latest delivery on their purchase order
- 58 out-of-range delivery scores and 2 out-of-range final scores in legacy run `RUN-c52cdf63`

These findings describe the earlier archived dataset only. They must not be attributed to the current active dataset.

## Current active dataset status

The latest committed `data/validation_summary.json` reports:

- SQLite integrity: PASS
- Foreign-key violations: 0
- Expected record counts: PASS
- Business-rule violations: 0
- Historical and latest score-range checks: PASS
- Overall validation: PASS

The active dataset contains 1,000 suppliers, 10,000 purchase orders, 15,000 shipments, 15,000 delivery events, and 20,000 inspections. Refer to the validation summary and source manifest for the complete checks and table counts.

All records are synthetic. Passing these validations demonstrates internal consistency and reproducibility, not predictive performance on real supplier data.
