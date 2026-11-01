# Complete Field-Level Data Dictionary

Column definitions below are generated from `data/schema.sql` and supplemented with generator/scoring validation rules. `Required = No` means SQL NULL is permitted. SQLite's declared type is shown (SQLite uses type affinity).

| Entity / table | Column | SQLite type | Required? | Allowed values / units | Unique? | Validation / constraints |
|---|---|---|---|---|---|---|
| suppliers | supplier_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| suppliers | name | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| suppliers | category | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| suppliers | country | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| suppliers | status | TEXT | No | Active / Inactive / Probation; NULL allowed | No | CHECK: status IN ('Active', 'Inactive', 'Probation') |
| suppliers | created_at | TEXT | Yes | — | No | ISO 8601 date/time representation |
| suppliers | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| sites | site_id | TEXT | Yes | — | Composite PK (site_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| sites | supplier_id | TEXT | Yes | — | Composite PK (site_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| sites | site_name | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| sites | location | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| sites | is_active | INTEGER | No | NULL allowed | No | Default: 1 |
| sites | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| contracts | contract_id | TEXT | Yes | — | Composite PK (contract_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| contracts | supplier_id | TEXT | Yes | — | Composite PK (contract_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| contracts | start_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| contracts | end_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| contracts | agreed_terms | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| contracts | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| purchase_orders | po_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_orders | supplier_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_orders | site_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_orders | contract_id | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_orders | order_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| purchase_orders | status | TEXT | No | Draft / Issued / Fulfilled / Cancelled; NULL allowed | No | CHECK: status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled') |
| purchase_orders | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| po_lines | po_line_id | TEXT | Yes | — | Composite PK (po_line_id, po_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| po_lines | po_id | TEXT | Yes | — | Composite PK (po_line_id, po_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| po_lines | item_code | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| po_lines | ordered_qty | REAL | Yes | item quantity; strictly positive | No | CHECK: `ordered_qty > 0`; cumulative shipped quantity must not exceed ordered quantity |
| po_lines | unit_price | REAL | Yes | synthetic currency units per item; unit_price >= 0 | No | CHECK: unit_price >= 0 |
| po_lines | requested_delivery_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| po_lines | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| shipments | shipment_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| shipments | po_line_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| shipments | po_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| shipments | shipped_qty | REAL | Yes | item quantity; shipped_qty >= 0 | No | CHECK: shipped_qty >= 0; Must be non-negative; cross-row quantity reconciliation applies |
| shipments | dispatch_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| shipments | expected_delivery_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| shipments | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| delivery_events | delivery_event_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| delivery_events | shipment_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| delivery_events | actual_delivery_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| delivery_events | delivered_qty | REAL | Yes | item quantity; delivered_qty >= 0 | No | CHECK: delivered_qty >= 0; Must be non-negative; cross-row quantity reconciliation applies |
| delivery_events | receiver_notes | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| delivery_events | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| inspections | inspection_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| inspections | delivery_event_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| inspections | inspection_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| inspections | inspected_qty | REAL | Yes | item quantity; strictly positive | No | CHECK: `inspected_qty > 0`; cumulative inspected quantity must not exceed delivered quantity |
| inspections | defective_qty | REAL | Yes | item quantity; defective_qty >= 0 | No | CHECK: defective_qty >= 0; Must be non-negative; cross-row quantity reconciliation applies |
| inspections | result_status | TEXT | No | Passed / Failed / Conditionally Accepted; NULL allowed | No | CHECK: result_status IN ('Passed', 'Failed', 'Conditionally Accepted') |
| inspections | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| invoices | invoice_id | TEXT | Yes | — | Composite PK (invoice_id, po_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| invoices | po_id | TEXT | Yes | — | Composite PK (invoice_id, po_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| invoices | invoice_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| invoices | status | TEXT | No | Matched / Discrepancy / Paid; NULL allowed | No | CHECK: status IN ('Matched', 'Discrepancy', 'Paid') |
| invoices | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| invoice_lines | invoice_line_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| invoice_lines | invoice_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| invoice_lines | po_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| invoice_lines | po_line_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| invoice_lines | invoiced_qty | REAL | Yes | item quantity; invoiced_qty >= 0 | No | CHECK: invoiced_qty >= 0; Must be non-negative; cross-row quantity reconciliation applies |
| invoice_lines | billed_unit_price | REAL | Yes | synthetic currency units per item; billed_unit_price >= 0 | No | CHECK: billed_unit_price >= 0 |
| invoice_lines | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| risk_signals | risk_signal_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| risk_signals | supplier_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| risk_signals | signal_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| risk_signals | category | TEXT | No | Compliance / Disruption; NULL allowed | No | CHECK: category IN ('Compliance', 'Disruption') |
| risk_signals | severity | TEXT | No | Low / Medium / High / Critical; NULL allowed | No | CHECK: severity IN ('Low', 'Medium', 'High', 'Critical') |
| risk_signals | description | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| risk_signals | source | TEXT | Yes | Non-empty text; surrounding whitespace is ignored for validation | No | CHECK: `length(trim(source)) > 0` |
| risk_signals | system_available_at | TEXT | Yes | — | No | Point-in-time filter: must be <= scoring as-of date; ISO 8601 date/time representation |
| quarantine_log | quarantine_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| quarantine_log | source_table | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| quarantine_log | raw_payload | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| quarantine_log | error_reason | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| quarantine_log | logged_at | TEXT | Yes | — | No | ISO 8601 date/time representation |
| score_runs | run_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| score_runs | run_timestamp | TEXT | Yes | — | No | ISO 8601 date/time representation |
| score_runs | as_of_date | TEXT | Yes | — | No | ISO 8601 date/time representation |
| score_runs | config_version | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| score_runs | config_hash | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| score_runs | generator_version | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| score_runs | random_seed | INTEGER | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| supplier_scores | score_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| supplier_scores | run_id | TEXT | Yes | — | Composite unique (run_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| supplier_scores | supplier_id | TEXT | Yes | — | Composite unique (run_id, supplier_id) | Identifier format and/or application-level domain validation; see generator/scorer |
| supplier_scores | delivery_score | REAL | No | NULL allowed; delivery_score BETWEEN 0 AND 100 | No | CHECK: delivery_score BETWEEN 0 AND 100 |
| supplier_scores | delivery_sample_count | INTEGER | No | NULL allowed; delivery_sample_count >= 0 | No | CHECK: delivery_sample_count >= 0; Default: 0 |
| supplier_scores | delivery_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `delivery_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | quality_score | REAL | No | NULL allowed; quality_score BETWEEN 0 AND 100 | No | CHECK: quality_score BETWEEN 0 AND 100 |
| supplier_scores | quality_sample_count | INTEGER | No | NULL allowed; quality_sample_count >= 0 | No | CHECK: quality_sample_count >= 0; Default: 0 |
| supplier_scores | quality_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `quality_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | cost_score | REAL | No | NULL allowed; cost_score BETWEEN 0 AND 100 | No | CHECK: cost_score BETWEEN 0 AND 100 |
| supplier_scores | cost_sample_count | INTEGER | No | NULL allowed; cost_sample_count >= 0 | No | CHECK: cost_sample_count >= 0; Default: 0 |
| supplier_scores | cost_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `cost_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | capacity_score | REAL | No | NULL allowed; capacity_score BETWEEN 0 AND 100 | No | CHECK: capacity_score BETWEEN 0 AND 100 |
| supplier_scores | capacity_sample_count | INTEGER | No | NULL allowed; capacity_sample_count >= 0 | No | CHECK: capacity_sample_count >= 0; Default: 0 |
| supplier_scores | capacity_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `capacity_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | compliance_score | REAL | No | NULL allowed; compliance_score BETWEEN 0 AND 100 | No | CHECK: compliance_score BETWEEN 0 AND 100 |
| supplier_scores | compliance_sample_count | INTEGER | No | NULL allowed; compliance_sample_count >= 0 | No | CHECK: compliance_sample_count >= 0; Default: 0 |
| supplier_scores | compliance_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `compliance_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | disruption_score | REAL | No | NULL allowed; disruption_score BETWEEN 0 AND 100 | No | CHECK: disruption_score BETWEEN 0 AND 100 |
| supplier_scores | disruption_sample_count | INTEGER | No | NULL allowed; disruption_sample_count >= 0 | No | CHECK: disruption_sample_count >= 0; Default: 0 |
| supplier_scores | disruption_confidence | TEXT | No | High / Medium / Low (Sparse Data) / No Data; NULL allowed | No | CHECK: `disruption_confidence IN ('High', 'Medium', 'Low (Sparse Data)', 'No Data')` |
| supplier_scores | final_score | REAL | No | NULL allowed; final_score BETWEEN 0 AND 100 | No | CHECK: final_score BETWEEN 0 AND 100 |
| supplier_scores | overall_confidence_tier | TEXT | No | High / Medium / Low (Sparse Data); NULL allowed | No | CHECK: `overall_confidence_tier IN ('High', 'Medium', 'Low (Sparse Data)')` |
| purchase_order_status_events | event_id | TEXT | Yes | — | Primary key | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_order_status_events | po_id | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_order_status_events | previous_status | TEXT | No | NULL allowed | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_order_status_events | new_status | TEXT | Yes | Draft / Issued / Fulfilled / Cancelled | No | CHECK: new_status IN ('Draft', 'Issued', 'Fulfilled', 'Cancelled') |
| purchase_order_status_events | changed_at | TEXT | Yes | — | No | ISO 8601 date/time representation |
| purchase_order_status_events | changed_by | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |
| purchase_order_status_events | reason | TEXT | Yes | — | No | Identifier format and/or application-level domain validation; see generator/scorer |

### supplier_decisions

`supplier_decisions` persists one operational decision for each supplier score row. `score_id` is both the table's primary key and a foreign key to `supplier_scores(score_id)` with `ON DELETE CASCADE`. `classification` is restricted to `Reliable`, `Watch`, `At Risk`, or `Insufficient Evidence`; `decision_reason` stores the explanation and `policy_version` records the policy used.

| supplier_decisions | score_id | TEXT | Yes | — | Primary key; also foreign key | References `supplier_scores(score_id)`; `ON DELETE CASCADE` |
| supplier_decisions | classification | TEXT | Yes | Reliable / Watch / At Risk / Insufficient Evidence | No | CHECK: classification IN ('Reliable', 'Watch', 'At Risk', 'Insufficient Evidence') |
| supplier_decisions | decision_reason | TEXT | Yes | Human-readable explanation for the persisted decision | No | Non-null explanation; generated by the classification policy |
| supplier_decisions | policy_version | TEXT | Yes | Version identifier for the decision policy | No | Non-null policy version for reproducibility |

## Table-level relationships and additional validation

- Composite primary keys: `sites(site_id, supplier_id)`, `contracts(contract_id, supplier_id)`, `po_lines(po_line_id, po_id)`, and `invoices(invoice_id, po_id)`. These components are not individually unique.
- `supplier_scores` has a composite unique constraint on `(run_id, supplier_id)`; neither component is individually unique.
- Purchase orders reference sites and contracts using supplier-scoped composite foreign keys, preventing cross-supplier site/contract assignment.
- Shipment, delivery, inspection and invoice quantities are reconciled cumulatively against their parent quantities by database triggers and validation queries.
- Delivery dates cannot precede dispatch; inspection dates cannot precede delivery; invoice dates cannot precede the latest delivery on the PO.
- `purchase_order_status_events` contains one initial-state event per PO plus one immutable event for each status transition. The event timestamp, actor and reason are required.
- The five labelled edge-case fixtures are intentionally invalid, exported to `data/malformed_cases.json`, and persisted in `quarantine_log`; they are excluded from clean operational facts and scoring features.
- Ground-truth profile labels and expected metrics live in `ground_truth.json`; they are evaluation-only and must never be included as scoring features.

## Identifier formats

- Supplier: `SUP-000001`; site: `SITE-SUP-000001-01`; PO: `PO-2026-000001`; shipment: `SHP-2026-000001`; risk signal: `RSK-SUP-000001-2026-01`; supplier score: `SCORE-2026-000001`.
- Event and supporting-table identifiers use their entity prefixes and zero-padded counters. Primary keys are immutable; foreign keys must match the exact referenced identifier.

- **Many-to-many cardinality:** No explicit many-to-many relationship is modeled in the current scope. Operational associations are represented through transaction/line entities (for example, purchase orders and PO lines), while the supplier, site, contract, shipment, delivery, inspection, invoice, and score relationships use parent-child foreign keys. If a supplier-to-catalog-item relationship is introduced later, it should be normalized through a `supplier_items` bridge table rather than duplicated on either parent.
