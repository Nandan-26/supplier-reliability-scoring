# Contributing

Thank you for your interest in improving Supplier Reliability & Risk Scoring.

## Before opening a change

1. Open an issue describing the defect or proposed improvement.
2. Keep changes focused and explain the business or validation rule they affect.
3. Never add real supplier, customer, employee, or confidential procurement data. This repository uses synthetic fixtures.
4. Do not commit generated SQLite databases, virtual environments, caches, secrets, or local editor files.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Validation before a pull request

Run the relevant checks from the repository root:

```powershell
python -m pytest -v
python scripts/validate_full_dataset.py
python scripts/check_reproducibility.py
```

If a change affects scoring, data generation, evaluation, schema, or exported artifacts, also run:

```powershell
python scripts/refresh_dataset.py
python scripts/evaluate_ground_truth.py
```

Explain any generated artifact changes in the pull request. Keep active-dataset and independent-holdout results separate.

## Pull request expectations

- Describe the problem and the chosen solution.
- List schema, scoring-policy, and data-contract changes.
- Include test commands and their actual results.
- Update the data dictionary and metric documentation when applicable.
- Add or update edge-case tests for new validation rules.
- Do not claim real-world model performance from synthetic evaluation results.

## Project scope

This is an educational/assessment project, not a production supplier approval service. Changes that affect supplier decisions should preserve point-in-time correctness, evidence minimums, explainability, and the synthetic-data limitations documented in the README.
