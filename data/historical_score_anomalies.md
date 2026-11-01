# Historical Dataset and Anomaly Notes

## Repository retention policy

Generated SQLite databases and pre-refresh snapshots are not committed. The database is recreated by `scripts/refresh_dataset.py`; deterministic CSV/JSON artifacts and provenance metadata remain version-controlled. This keeps the repository reviewable and prevents every refresh from adding another full database copy to the Git tree. Older snapshots may still exist in earlier Git commits; this cleanup removes them from the current branch tip but does not rewrite Git history.

## Previously observed legacy anomalies

Earlier pre-refresh datasets contained issues including cancelled purchase orders with shipments or invoices, fulfilled orders with incomplete shipped quantities, inspection quantities above received quantities, invoice lines above delivered quantities, invoices dated before the latest delivery, and out-of-range legacy scores. These are historical findings from superseded synthetic datasets, not claims about the current active dataset. The old raw snapshots have been removed from the current repository tree to reduce size.

## Current active dataset

The current active dataset and its validation status are described by:

- `data/validation_summary.json`
- `data/source_manifest.json`
- `data/generation_metadata.json`
- `data/ground_truth_evaluation.json`

All records are synthetic. Passing validation demonstrates internal consistency and reproducibility, not predictive performance on real supplier data.
