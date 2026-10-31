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

This catalogue defines the five acceptance scenarios. It is not evidence that all five are currently injected, detected, quarantined, or tested by the generator. Check the validation summary and CI results before claiming implementation.
