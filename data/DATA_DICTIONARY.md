# Data Dictionary

All records in this project are synthetic. Dates use ISO `YYYY-MM-DD` text unless otherwise noted. Primary and foreign keys are defined in `data/schema.sql`.

| Table | Grain / primary key | Important columns | Relationship / meaning |
|---|---|---|---|
| `suppliers` | One row per supplier; `supplier_id` | `name`, `category`, `country`, `status`, `created_at`, `system_available_at` | Supplier master and the system date on which the record became available. |
| `sites` | One row per supplier site; composite key `site_id, supplier_id` | `site_name`, `location`, `is_active` | A supplier may operate one or more sites. |
| `contracts` | One row per supplier contract; composite key `contract_id, supplier_id` | `start_date`, `end_date`, `agreed_terms` | Contract dates and commercial terms for a supplier. |
| `purchase_orders` | One row per PO; `po_id` | `supplier_id`, `site_id`, `contract_id`, `order_date`, `status` | Header for an order placed with a supplier. Status values are Draft, Issued, Fulfilled, or Cancelled. |
| `po_lines` | One row per PO line; composite key `po_line_id, po_id` | `item_code`, `ordered_qty`, `unit_price`, `requested_delivery_date` | Item-level ordered quantity and agreed price. This is the main grain for fulfillment analysis. |
| `shipments` | One row per shipment; `shipment_id` | `po_line_id`, `po_id`, `shipped_qty`, `dispatch_date`, `expected_delivery_date` | Shipment against a PO line. Cumulative shipped quantity should not exceed the line's ordered quantity. |
| `delivery_events` | One row per receipt event; `delivery_event_id` | `shipment_id`, `actual_delivery_date`, `delivered_qty`, `receiver_notes` | Actual receipt evidence for a shipment. |
| `inspections` | One row per inspected lot; `inspection_id` | `delivery_event_id`, `inspection_date`, `inspected_qty`, `defective_qty`, `result_status` | Quality inspection lot linked to a receipt. Lots for a delivery are disjoint quantity portions in generated data. |
| `invoices` | One row per invoice; composite key `invoice_id, po_id` | `invoice_date`, `status` | Invoice header associated with a purchase order. |
| `invoice_lines` | One row per invoice line; `invoice_line_id` | `invoice_id`, `po_id`, `po_line_id`, `invoiced_qty`, `billed_unit_price` | Quantity and billed price charged for a PO line. |
| `risk_signals` | One row per risk signal; `risk_signal_id` | `supplier_id`, `signal_date`, `category`, `severity`, `description` | Compliance or disruption evidence associated with a supplier. |
| `quarantine_log` | One row per quarantined record; `quarantine_id` | `source_table`, `raw_payload`, `error_reason`, `logged_at` | Rejected source payloads and detected validation reasons. The generator stores each rejected example here and also exports the annotated examples to `data/malformed_cases.json`. |
| `score_runs` | One row per scoring execution; `run_id` | `run_timestamp`, `as_of_date`, `config_version`, `config_hash`, `generator_version`, `random_seed` | Records the scoring run configuration and point-in-time date. |
| `supplier_scores` | One row per supplier per run; `score_id` | Six dimension scores, per-dimension sample counts/confidence, `final_score`, `overall_confidence_tier` | Persisted result for a supplier in a specific scoring run. |

## Point-in-time fields

Business-event dates (for example `actual_delivery_date`, `invoice_date`, and `signal_date`) describe when an event occurred. `system_available_at` describes when the event or record became available to the scoring system. Point-in-time scoring must respect both.

## Score interpretation

- Scores range from 0 to 100.
- A sample count of zero means no supporting records were observed for that dimension.
- A fallback score is not an observed performance result; read it with the confidence label.
- `overall_confidence_tier` is a simple project heuristic, not a statistical confidence interval.
