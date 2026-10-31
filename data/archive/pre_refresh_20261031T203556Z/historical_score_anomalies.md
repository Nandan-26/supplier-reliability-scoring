# Historical Dataset Audit — Pre-Refresh Snapshot

## Scope

This report describes the preserved database at `data/archive/pre_refresh_20261031T203556Z/supplier_scoring.db` and its matching CSV exports. The snapshot was archived before the active dataset was regenerated. Its rows have not been edited or silently corrected.

The archived database passes SQLite integrity and foreign-key checks, but several business-rule and score-range checks fail.

## Historical business-rule violations

| Check | Violating records |
|---|---:|
| Cancelled purchase orders with shipments | 776 |
| Cancelled purchase orders with invoices | 248 |
| Fulfilled purchase orders with incomplete shipped quantities | 3,967 |
| Deliveries inspected beyond their received quantity | 5,000 |
| Invoice lines exceeding delivered quantity | 2,831 |
| Invoices dated before the latest delivery on their PO | 1,161 |
| PO lines shipped beyond ordered quantity | 0 |
| Delivery quantity exceeding shipment quantity | 0 |
| Duplicate supplier score rows within a run | 0 |

## Historical score anomalies

The archived score export contains four scoring runs with 1,000 supplier rows each. All out-of-range score values are in the legacy run `RUN-c52cdf63`:

| Score column | Out-of-range values | Run |
|---|---:|---|
| `delivery_score` | 58 | `RUN-c52cdf63` |
| `final_score` | 2 | `RUN-c52cdf63` |
| Other five dimension scores | 0 | All runs |
| `final_score` in the other three runs | 0 | Other three runs |

Examples include delivery scores of 112.50 and 109.09 and a final score of 100.03. The three later runs have no scores outside 0–100. The latest archived scoring run passes its score-range check, but historical score validation and overall validation fail.

## Preservation and remediation decision

- The original database, exports, ground-truth file, malformed-case file, validation summary, and source manifest are preserved together in this archive.
- The historical score rows and operational records were not rewritten.
- The active `data/supplier_scoring.db` and `data/exports/` now contain a newly generated dataset using the corrected generator and scoring implementation.
- The active dataset has its own `data/validation_summary.json`, which reports all current business checks and score-range checks passing.

Do not use the archived legacy scores as current normalized supplier scores. They are retained only for audit and comparison.

## Verification

The current GitHub Actions workflow validates both a fresh full-size temporary dataset and the archived historical database. It does not modify this archive.
