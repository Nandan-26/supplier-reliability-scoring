# Historical Score Anomaly Report

## Scope

This report describes the committed historical export `data/exports/supplier_scores.csv` inspected during the repository audit. The original database and its historical score rows were not modified during this audit.

## Findings

The export contains four scoring runs with 1,000 supplier rows each. All observed out-of-range values are in the legacy run `RUN-c52cdf63`:

| Score column | Out-of-range values | Run |
|---|---:|---|
| `delivery_score` | 58 | `RUN-c52cdf63` |
| `final_score` | 2 | `RUN-c52cdf63` |
| Other five dimension scores | 0 | All runs |
| `final_score` in the other three runs | 0 | Other three runs |

Examples include delivery scores above 100 (for example 112.50 and 109.09) and a final score of 100.03. Scores are not clamped or silently rewritten in this historical export.

The three later historical runs in the export have no scores outside the 0–100 range. The updated scoring implementation additionally calculates delivery performance from distinct PO-line outcomes and checks all dimension and final scores are within 0–100 in the isolated full-dataset validation.

## Handling decision

- Preserve the original historical rows for audit traceability.
- Do not interpret `RUN-c52cdf63` as a valid normalized score run.
- Use the updated scoring implementation for new scoring runs.
- The existing `data/validation_summary.json` correctly reports historical score-range validation as failed while the latest historical run passes. Its overall historical status therefore remains failed until a separately approved correction or archival policy is applied.

## Verification

The GitHub Actions full-dataset validator creates a fresh database in a temporary directory, generates 1,000 suppliers, 10,000 purchase orders, 15,000 shipments, and 20,000 inspection lots, runs scoring, and checks the 1,000 resulting supplier scores. It also checks relational integrity, lifecycle and quantity rules, invoice timing, profile-level ground truth, and malformed-record quarantine. The temporary database is deleted at the end; the committed historical database is not overwritten.

See the [validation workflow](https://github.com/Nandan-26/supplier-reliability-scoring/actions) for the latest run.
