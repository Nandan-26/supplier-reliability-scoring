# Business Metric Definitions

All metrics are calculated only from records eligible at the selected as-of date. Unless stated otherwise, report both numerator and denominator; return NULL (not zero) when the denominator is zero.

## Delivery performance
- **On-time delivery rate (receipt-event grain):** 100 × count of eligible delivery events with actual_delivery_date <= expected_delivery_date / count of eligible delivery events. The PO-line-level equivalent counts PO lines fully delivered by their requested_delivery_date / eligible PO lines. Do not mix these grains in one reported figure.
- **Eligible PO line:** non-cancelled PO line with requested_delivery_date and system availability <= as_of_date. For a completed-line KPI, require cumulative delivered quantity >= ordered_qty.
- **Late delivery rate:** 100 × eligible delivered PO lines not fully delivered by requested_delivery_date / eligible PO lines with a delivery outcome.

## Quality
- **Quality rate:** 100 × (total inspected quantity - total defective quantity) / total inspected quantity.
- **Defect rate:** 100 × total defective quantity / total inspected quantity.
- **Denominator:** sum of inspected_qty for eligible inspection lots; do not average row-level defect percentages.

## Invoice and cost
- **Invoice quantity variance:** sum(abs(invoiced_qty - delivered_qty_by_PO_line)) across matched PO lines. Also report percentage variance = 100 × total absolute quantity variance / total delivered quantity for those matched lines. The denominator is delivered quantity; report NULL if zero.
- **Invoice monetary variance:** sum(abs(invoiced_qty × billed_unit_price - delivered_qty × PO unit_price)) across matched PO lines, in synthetic currency units. Also report percentage variance = 100 × absolute monetary variance / total expected delivered value; NULL if expected value is zero.
- **Cost adherence score:** score based on invoice billed unit price compared with the PO-line agreed unit price. This measures contract-price adherence, not whether the absolute price is cheap.

## Capacity
- **Fulfillment rate:** 100 × sum(eligible delivered quantity) / sum(eligible ordered quantity). Denominator is ordered quantity for eligible PO lines; cap at 100 only for presentation, while separately flagging over-delivery as a data-quality violation.

## Missing data and confidence
- **Missing-data percentage:** 100 × count of the six score dimensions with sample_count = 0 / 6 for each supplier. For a portfolio-wide rate, use total zero-sample dimension cells / (eligible suppliers × 6).
- **Confidence distribution:** count and percentage of supplier scores in each overall_confidence_tier (High, Medium, Low (Sparse Data)). Denominator is the number of supplier score rows in the selected run.
- Confidence tiers are rule-based heuristics, not statistical confidence intervals.

## Compliance and disruption
- Report eligible risk-signal counts by category and severity, with source and signal_date provenance.
- Dimension penalties are applied only to signals with event date and system_available_at on or before the as-of date. No signal evidence is not proof of compliance; the existing neutral fallback is labelled No Data.

## Point-in-time rule
A record is eligible only when both its business-event date and system_available_at are on or before as_of_date. Every published metric must identify its as_of_date, entity grain, numerator, denominator and eligible-row filters.

## Risk classification policy

The composite score is accompanied by explainable decision rules. A supplier is classified as Insufficient Evidence when overall confidence is Low (Sparse Data), or when either delivery or quality has fewer than five observations. This prevents a high aggregate sample count in unrelated dimensions from masking sparse evidence in a critical dimension. For suppliers meeting both minimums, a delivery score below 75 or quality score below 90 marks the supplier At Risk. A dimension with zero observations does not trigger its risk guardrail; its neutral No Data fallback is not evidence of good or poor performance. Suppliers that do not breach either guardrail are classified Reliable when the composite score is at least 80, otherwise Watch. These are illustrative business rules and should be reviewed with procurement stakeholders.

The policy is checked on a separate full-scale synthetic holdout generated with seed `20261023`; the committed evaluation dataset uses seed `20261022`. Ground-truth profile labels are used only for evaluation, never as scoring features. CI requires at least 90% precision and 90% recall on the independent holdout.
