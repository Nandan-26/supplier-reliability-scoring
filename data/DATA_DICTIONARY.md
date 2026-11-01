# Complete Field-Level Schema Reference

Generated from the current SQLite schema. SQLite declarations, CHECK constraints, primary keys, unique indexes, and foreign keys are authoritative. Date fields use ISO `YYYY-MM-DD` text unless otherwise noted; prices use synthetic currency units; quantities are item-specific units; scores are points from 0 to 100.

Required includes NOT NULL or primary-key membership. `Allowed / units` summarizes CHECK constraints and business units. Cross-row rules are listed at the end.

## suppliers

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| supplier_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| name | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| category | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| country | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| status | TEXT | No | status IN ('Active', 'Inactive', 'Probation')) | No | CHECK(status IN ('Active', 'Inactive', 'Probation')) |
| created_at | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## sites

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| site_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| supplier_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| site_name | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| location | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| is_active | INTEGER | No | — | No | Default 1 |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## contracts

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| contract_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| supplier_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| start_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| end_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| agreed_terms | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## purchase_orders

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| po_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| site_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| contract_id | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| order_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| status | TEXT | No | status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled')) | No | CHECK(status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled')) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## po_lines

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| po_line_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| po_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| item_code | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| ordered_qty | REAL | Yes | ordered_qty > 0); item quantity | No | CHECK(ordered_qty > 0) |
| unit_price | REAL | Yes | unit_price >= 0); synthetic currency units | No | CHECK(unit_price >= 0) |
| requested_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## shipments

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| shipment_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| po_line_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| po_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| shipped_qty | REAL | Yes | shipped_qty >= 0); item quantity | No | CHECK(shipped_qty >= 0) |
| dispatch_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| expected_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## delivery_events

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| delivery_event_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| shipment_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| actual_delivery_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| delivered_qty | REAL | Yes | delivered_qty >= 0); item quantity | No | CHECK(delivered_qty >= 0) |
| receiver_notes | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## inspections

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| inspection_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| delivery_event_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| inspection_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| inspected_qty | REAL | Yes | inspected_qty > 0); item quantity | No | CHECK(inspected_qty > 0) |
| defective_qty | REAL | Yes | defective_qty >= 0); item quantity | No | CHECK(defective_qty >= 0) |
| result_status | TEXT | No | result_status IN ('Passed', 'Failed', 'Conditionally Accepted')) | No | CHECK(result_status IN ('Passed', 'Failed', 'Conditionally Accepted')) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## invoices

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| invoice_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| po_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| invoice_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| status | TEXT | No | status IN ('Matched', 'Discrepancy', 'Paid')) | No | CHECK(status IN ('Matched', 'Discrepancy', 'Paid')) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## invoice_lines

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| invoice_line_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| invoice_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| po_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| po_line_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| invoiced_qty | REAL | Yes | invoiced_qty >= 0); item quantity | No | CHECK(invoiced_qty >= 0) |
| billed_unit_price | REAL | Yes | billed_unit_price >= 0); synthetic currency units | No | CHECK(billed_unit_price >= 0) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## risk_signals

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| risk_signal_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| supplier_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| signal_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| category | TEXT | No | category IN ('Compliance', 'Disruption')) | No | CHECK(category IN ('Compliance', 'Disruption')) |
| severity | TEXT | No | severity IN ('Low', 'Medium', 'High', 'Critical')) | No | CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')) |
| description | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| source | TEXT | Yes | length(trim(source)) > 0) | No | CHECK(length(trim(source)) > 0) |
| system_available_at | TEXT | Yes | ISO date/time | No | Point-in-time availability date; ISO date/time text |

## quarantine_log

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| quarantine_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| source_table | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| raw_payload | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| error_reason | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| logged_at | TEXT | Yes | ISO date/time | No | ISO date/time text |

## score_runs

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| run_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| run_timestamp | TEXT | Yes | ISO date/time | No | ISO date/time text |
| as_of_date | TEXT | Yes | ISO date/time | No | ISO date/time text |
| config_version | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| config_hash | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| generator_version | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| random_seed | INTEGER | No | — | No | No inline CHECK; application/business validation applies |

## supplier_scores

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| score_id | TEXT | Yes | 0–100 points | Primary key | No inline CHECK; application/business validation applies |
| run_id | TEXT | Yes | — | Unique index | No inline CHECK; application/business validation applies |
| supplier_id | TEXT | Yes | — | Unique index | No inline CHECK; application/business validation applies |
| delivery_score | REAL | No | delivery_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(delivery_score BETWEEN 0 AND 100) |
| delivery_sample_count | INTEGER | No | delivery_sample_count >= 0); count | No | CHECK(delivery_sample_count >= 0); Default 0 |
| delivery_confidence | TEXT | No | delivery_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) | No | CHECK(delivery_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| quality_score | REAL | No | quality_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(quality_score BETWEEN 0 AND 100) |
| quality_sample_count | INTEGER | No | quality_sample_count >= 0); count | No | CHECK(quality_sample_count >= 0); Default 0 |
| quality_confidence | TEXT | No | quality_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) | No | CHECK(quality_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| cost_score | REAL | No | cost_score BETWEEN 0 AND 100); synthetic currency units | No | CHECK(cost_score BETWEEN 0 AND 100) |
| cost_sample_count | INTEGER | No | cost_sample_count >= 0); synthetic currency units | No | CHECK(cost_sample_count >= 0); Default 0 |
| cost_confidence | TEXT | No | cost_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')); synthetic currency units | No | CHECK(cost_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| capacity_score | REAL | No | capacity_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(capacity_score BETWEEN 0 AND 100) |
| capacity_sample_count | INTEGER | No | capacity_sample_count >= 0); count | No | CHECK(capacity_sample_count >= 0); Default 0 |
| capacity_confidence | TEXT | No | capacity_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) | No | CHECK(capacity_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| compliance_score | REAL | No | compliance_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(compliance_score BETWEEN 0 AND 100) |
| compliance_sample_count | INTEGER | No | compliance_sample_count >= 0); count | No | CHECK(compliance_sample_count >= 0); Default 0 |
| compliance_confidence | TEXT | No | compliance_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) | No | CHECK(compliance_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| disruption_score | REAL | No | disruption_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(disruption_score BETWEEN 0 AND 100) |
| disruption_sample_count | INTEGER | No | disruption_sample_count >= 0); count | No | CHECK(disruption_sample_count >= 0); Default 0 |
| disruption_confidence | TEXT | No | disruption_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) | No | CHECK(disruption_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')) |
| final_score | REAL | No | final_score BETWEEN 0 AND 100); 0–100 points | No | CHECK(final_score BETWEEN 0 AND 100) |
| overall_confidence_tier | TEXT | No | overall_confidence_tier IN ('High', 'Medium', 'Low (Sparse Data)')) | No | CHECK(overall_confidence_tier IN ('High', 'Medium', 'Low (Sparse Data)')) |

## purchase_order_status_events

| Column | Type | Required? | Allowed values / units | Unique? | Validation |
|---|---|---:|---|---|---|
| event_id | TEXT | Yes | — | Primary key | No inline CHECK; application/business validation applies |
| po_id | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| previous_status | TEXT | No | — | No | No inline CHECK; application/business validation applies |
| new_status | TEXT | Yes | new_status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled')) | No | CHECK(new_status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled')) |
| changed_at | TEXT | Yes | ISO date/time | No | ISO date/time text |
| changed_by | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |
| reason | TEXT | Yes | — | No | No inline CHECK; application/business validation applies |

## Cross-column and cross-row rules

- Composite primary keys: `sites(site_id, supplier_id)`, `contracts(contract_id, supplier_id)`, `po_lines(po_line_id, po_id)`, and `invoices(invoice_id, po_id)`.
- Purchase orders reference sites and contracts using supplier-scoped composite foreign keys; PO lines and invoice lines must belong to the referenced PO.
- `supplier_scores` has a unique index on `(run_id, supplier_id)`.
- Quantity triggers enforce cumulative shipped <= ordered, delivered <= shipped, inspected <= delivered, and invoiced <= delivered quantities.
- Date triggers enforce delivery on/after dispatch, inspection on/after delivery, and invoice date on/after the latest PO delivery.
- `purchase_order_status_events` records initial PO state and every status transition, including timestamp, actor and reason.
- `ground_truth.json` and `edge_case_fixtures.json` are evaluation labels, not scoring features.
- Columns without inline CHECK constraints may have application-level validation in `src/generator.py`, `src/scoring.py`, or `src/edge_cases.py`.
