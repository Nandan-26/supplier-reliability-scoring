# Complete Field-Level Schema Reference

Generated from the current SQLite schema. SQLite column declarations, CHECK constraints, primary keys, and foreign keys are authoritative. All date values are ISO `YYYY-MM-DD` text; prices are synthetic currency units; quantities are item-specific units; scores are points from 0 to 100.

For each field, Required includes NOT NULL or primary-key membership. `Allowed / units` and `Validation` summarize inline SQL constraints; additional cross-row business rules are enforced by triggers and application validation.

## suppliers

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| supplier_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| name | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| category | TEXT | No | ISO date/time | No | No inline CHECK; see relationship/business rules below |
| country | TEXT | No | count | No | No inline CHECK; see relationship/business rules below |
| status | TEXT | No | status IN ('Active', 'Inactive', 'Probation'; ISO date/time | No | CHECK(status IN ('Active', 'Inactive', 'Probation') |
| created_at | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## sites

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| site_id | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| site_name | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| location | TEXT | No | ISO date/time | No | No inline CHECK; see relationship/business rules below |
| is_active | INTEGER | No | — | No | Default 1 |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## contracts

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| contract_id | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| start_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| end_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| agreed_terms | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## purchase_orders

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| po_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| site_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| contract_id | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| order_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| status | TEXT | No | status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled'; ISO date/time | No | CHECK(status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled') |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## po_lines

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| po_line_id | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| po_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| item_code | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| ordered_qty | REAL | Yes | ordered_qty > 0; item quantity | No | CHECK(ordered_qty > 0) |
| unit_price | REAL | Yes | unit_price >= 0; synthetic currency units | No | CHECK(unit_price >= 0) |
| requested_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## shipments

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| shipment_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| po_line_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| po_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| shipped_qty | REAL | Yes | shipped_qty >= 0; item quantity | No | CHECK(shipped_qty >= 0) |
| dispatch_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| expected_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## delivery_events

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| delivery_event_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| shipment_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| actual_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| delivered_qty | REAL | Yes | delivered_qty >= 0; item quantity | No | CHECK(delivered_qty >= 0) |
| receiver_notes | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## inspections

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| inspection_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| delivery_event_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| inspection_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| inspected_qty | REAL | Yes | inspected_qty > 0; item quantity | No | CHECK(inspected_qty > 0) |
| defective_qty | REAL | Yes | defective_qty >= 0; item quantity | No | CHECK(defective_qty >= 0) |
| result_status | TEXT | No | result_status IN ('Passed', 'Failed', 'Conditionally Accepted'; ISO date/time | No | CHECK(result_status IN ('Passed', 'Failed', 'Conditionally Accepted') |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## invoices

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| invoice_id | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| po_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| invoice_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| status | TEXT | No | status IN ('Matched', 'Discrepancy', 'Paid'; ISO date/time | No | CHECK(status IN ('Matched', 'Discrepancy', 'Paid') |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## invoice_lines

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| invoice_line_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| invoice_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| po_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| po_line_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| invoiced_qty | REAL | Yes | invoiced_qty >= 0; item quantity | No | CHECK(invoiced_qty >= 0) |
| billed_unit_price | REAL | Yes | billed_unit_price >= 0; synthetic currency units | No | CHECK(billed_unit_price >= 0) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## risk_signals

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| risk_signal_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| signal_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| category | TEXT | No | category IN ('Compliance', 'Disruption'; ISO date/time | No | CHECK(category IN ('Compliance', 'Disruption') |
| severity | TEXT | No | severity IN ('Low', 'Medium', 'High', 'Critical' | No | CHECK(severity IN ('Low', 'Medium', 'High', 'Critical') |
| description | TEXT | No | — | No | No inline CHECK; see relationship/business rules below |
| source | TEXT | Yes | length(trim(source | No | CHECK(length(trim(source) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability cutoff; ISO date/time text |

## quarantine_log

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| quarantine_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| source_table | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| raw_payload | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| error_reason | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| logged_at | TEXT | Yes | ISO date/time | No | ISO date/time text |

## score_runs

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| run_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| run_timestamp | TEXT | Yes | ISO date/time | No | No inline CHECK; see relationship/business rules below |
| as_of_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| config_version | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| config_hash | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| generator_version | TEXT | Yes | ISO date/time | No | No inline CHECK; see relationship/business rules below |
| random_seed | INTEGER | No | — | No | No inline CHECK; see relationship/business rules below |

## supplier_scores

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| score_id | TEXT | Yes | 0–100 points | Primary key | No inline CHECK; see relationship/business rules below |
| run_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| delivery_score | REAL | No | delivery_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(delivery_score BETWEEN 0 AND 100) |
| delivery_sample_count | INTEGER | No | delivery_sample_count >= 0; count | No | CHECK(delivery_sample_count >= 0); Default 0 |
| delivery_confidence | TEXT | No | delivery_confidence IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(delivery_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| quality_score | REAL | No | quality_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(quality_score BETWEEN 0 AND 100) |
| quality_sample_count | INTEGER | No | quality_sample_count >= 0; count | No | CHECK(quality_sample_count >= 0); Default 0 |
| quality_confidence | TEXT | No | quality_confidence IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(quality_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| cost_score | REAL | No | cost_score BETWEEN 0 AND 100; synthetic currency units | No | CHECK(cost_score BETWEEN 0 AND 100) |
| cost_sample_count | INTEGER | No | cost_sample_count >= 0; synthetic currency units | No | CHECK(cost_sample_count >= 0); Default 0 |
| cost_confidence | TEXT | No | cost_confidence IN ('High', 'Medium', 'Low (Sparse Data; synthetic currency units | No | CHECK(cost_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| capacity_score | REAL | No | capacity_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(capacity_score BETWEEN 0 AND 100) |
| capacity_sample_count | INTEGER | No | capacity_sample_count >= 0; count | No | CHECK(capacity_sample_count >= 0); Default 0 |
| capacity_confidence | TEXT | No | capacity_confidence IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(capacity_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| compliance_score | REAL | No | compliance_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(compliance_score BETWEEN 0 AND 100) |
| compliance_sample_count | INTEGER | No | compliance_sample_count >= 0; count | No | CHECK(compliance_sample_count >= 0); Default 0 |
| compliance_confidence | TEXT | No | compliance_confidence IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(compliance_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| disruption_score | REAL | No | disruption_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(disruption_score BETWEEN 0 AND 100) |
| disruption_sample_count | INTEGER | No | disruption_sample_count >= 0; count | No | CHECK(disruption_sample_count >= 0); Default 0 |
| disruption_confidence | TEXT | No | disruption_confidence IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(disruption_confidence IN ('High', 'Medium', 'Low (Sparse Data) |
| final_score | REAL | No | final_score BETWEEN 0 AND 100; 0–100 points | No | CHECK(final_score BETWEEN 0 AND 100) |
| overall_confidence_tier | TEXT | No | overall_confidence_tier IN ('High', 'Medium', 'Low (Sparse Data | No | CHECK(overall_confidence_tier IN ('High', 'Medium', 'Low (Sparse Data) |

## purchase_order_status_events

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| event_id | TEXT | Yes | — | Primary key | No inline CHECK; see relationship/business rules below |
| po_id | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| previous_status | TEXT | No | ISO date/time | No | No inline CHECK; see relationship/business rules below |
| new_status | TEXT | Yes | new_status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled'; ISO date/time | No | CHECK(new_status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled') |
| changed_at | TEXT | Yes | ISO date/time | No | ISO date/time text |
| changed_by | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |
| reason | TEXT | Yes | — | No | No inline CHECK; see relationship/business rules below |

## Additional cross-column and cross-row rules

- `sites` and `contracts` use composite primary keys `(site_id, supplier_id)` and `(contract_id, supplier_id)`; purchase orders reference these composite keys to prevent supplier/site and supplier/contract mismatches.
- `po_lines` use `(po_line_id, po_id)` as a composite primary key; shipments and invoice lines must reference the matching PO line and PO together.
- `invoices` use `(invoice_id, po_id)` as a composite primary key; invoice lines must match both values.
- `supplier_scores` has a unique index on `(run_id, supplier_id)`; each supplier receives at most one score per run.
- Quantity triggers enforce cumulative shipped <= ordered, delivered <= shipped, inspected <= delivered, and invoiced <= delivered quantities.
- Date triggers enforce delivery on/after dispatch, inspection on/after delivery, and invoice date on/after the latest PO delivery.
- `purchase_order_status_events` is populated by insert/update triggers: initial state plus each status transition are recorded with actor and reason. The event rows are not updated by application logic.
- `ground_truth.json` and `edge_case_fixtures.json` are evaluation labels and must not be joined into scoring features.
- Fields without explicit CHECK constraints may still be required by the generator, scorer, or business validation; see `src/generator.py`, `src/scoring.py`, and `src/edge_cases.py`.
