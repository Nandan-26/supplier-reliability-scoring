# Historical Dataset Archive

The previous committed database and its matching exports were preserved before the active dataset was regenerated.

- Archive: `data/archive/pre_refresh_20261031T203556Z/`
- Archived database: `data/archive/pre_refresh_20261031T203556Z/supplier_scoring.db`
- Active database: `data/supplier_scoring.db`
- Active generation seed: `20261022`
- The current active score run ID is recorded in `data/generation_metadata.json`.

The archived dataset passed SQLite integrity and foreign-key checks but contained historical business-rule and score anomalies. The most important counts were:

- 776 cancelled POs with shipments
- 248 cancelled POs with invoices
- 3,967 fulfilled POs with incomplete shipped quantities
- 5,000 deliveries with inspection quantities above received quantity
- 2,831 invoice lines above delivered quantity
- 1,161 invoices dated before the latest delivery on their PO
- 58 out-of-range delivery scores and 2 out-of-range final scores in legacy run `RUN-c52cdf63`

The detailed report is preserved at [the archived anomaly report](archive/pre_refresh_20261031T203556Z/historical_score_anomalies.md). The old database, CSV exports, ground truth, malformed examples, validation summary, and source manifest remain in the archive unchanged.

The active dataset is a fresh 1,000-supplier dataset. Its current validation summary reports SQLite integrity, foreign-key, expected-count, business-rule, and all historical/current score-range checks passing. See `data/validation_summary.json` and `data/generation_metadata.json`.
