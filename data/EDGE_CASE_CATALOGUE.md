# Round 2 Edge-Case Catalogue

These are deliberate, labelled assessment scenarios. They are kept out of clean operational tables unless a scenario is explicitly marked as a quarantine payload. Never repair these examples by silently changing unrelated baseline records.

| ID | Required scenario | Source entity | Detection rule | Expected handling | Score impact |
|---|---|---|---|---|---|
| EC-01 | Shipment has no purchase order | Shipment | `po_id` or `po_line_id` does not resolve to a valid PO/line pair | Reject into quarantine with raw payload and reason; do not join to a supplier | Exclude |
| EC-02 | Delivery date precedes dispatch | DeliveryEvent + Shipment | `actual_delivery_date < dispatch_date` | Quarantine the event; preserve the shipment and record the temporal violation | Exclude |
| EC-03 | Supplier score uses future data | SupplierScore / ScoreRun | Any contributing business-event date or `system_available_at` is after the run's `as_of_date` | Fail the point-in-time validation; score must be reproducible using only evidence available by the cutoff | Must not influence score |
| EC-04 | Risk signal has no source or timestamp | RiskSignal | `source` is null/blank or `signal_date` is null | Quarantine the signal with both missing-field reasons; do not score it | Exclude |
| EC-05 | Supplier sites are conflated | Supplier / Site / PurchaseOrder | PO supplier does not match the supplier owning its referenced site | Reject the PO relationship; preserve both master records and record the mismatch | Exclude |

## Required separation

- Clean baseline data must pass PK, FK, enum, date, quantity, lifecycle and duplicate validation before any edge case is introduced.
- Each deliberate case must carry its `edge_case_id` and expected outcome in a separate ground-truth artefact.
- Do not place ground-truth labels or anomaly flags in model/scoring input columns.
- Historical archived data is immutable evidence. Audit it separately; do not rewrite its IDs or rows to make current-format checks pass.

## Current implementation status

All five scenarios now have separate labelled fixtures in [edge_case_fixtures.json](edge_case_fixtures.json). The isolated validator in `src/edge_cases.py` reports the detected reason(s) and expected handling without inserting deliberately invalid rows into clean operational tables or scoring inputs. Automated coverage is in `tests/test_edge_cases.py`.

These fixtures are assessment test records, not production quarantine rows. EC-01 is tested as a missing PO/PO-line relationship; EC-02 as a delivery date before dispatch; EC-03 checks both event date and system availability against the score cutoff; EC-04 checks missing source and signal date; EC-05 checks the PO supplier against the referenced site's owner.
