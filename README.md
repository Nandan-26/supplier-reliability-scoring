logo
more
question-ai-logo
managemanage
managemanage
useruser
fullfull
closeclose
Chat AI
Hello! Is there any question I can help you with?
What is the purpose of student government in the United States?
What is the highest peak in the United States?

Ask AI
logo
more

















































































































Supplier Reliability & Risk Scoring Engine
A Python and SQLite project for generating synthetic procurement data
and calculating point-in-time supplier reliability scores across
delivery, quality, cost, capacity, compliance, and disruption.

Scope: This is an assessment project using synthetic data, not a
production procurement system. The default weights and rules are
starting assumptions, not calibrated business policy.

1. Overview
The project generates a synthetic supplier/procurement dataset, checks
selected data-integrity rules, calculates supplier scores for a
specified as-of date, and persists scoring results in SQLite. Malformed
challenge examples are kept separate from the valid baseline data.

Main capabilities: - Reproducible synthetic data generation. -
Relational schema and integrity constraints. - Supplier scoring across
six dimensions. - Point-in-time filters intended to prevent future-data
leakage. - Persisted score runs and automated tests. - Separate
synthetic ground-truth labels for evaluation.

2. Architecture
Synthetic data generator
        |
        v
SQLite schema and generated records
        |
        +--> Integrity and relationship checks
        |
        +--> Malformed cases --> data/malformed_cases.json
        |
        v
Point-in-time scoring engine
        |
        v
Persisted supplier score results
        |
        v
Automated tests and SQL inspection
Main files
src/generator.py --- generates the synthetic dataset and
supporting artifacts.
src/db.py --- database helpers.
src/scoring.py --- calculates and stores supplier scores for an
as-of date.
data/schema.sql --- SQLite schema and constraints.
data/supplier_scoring.db --- generated SQLite database, if
included in the checkout.
data/ground_truth.json --- separate synthetic reference labels.
data/malformed_cases.json --- malformed challenge examples
exported by the generator.
tests/ --- database, generator, and scoring tests.
3. Scoring model
Default composite-score weights:

Dimension Weight Intended meaning

Delivery 25% Delivery timeliness and fulfillment behavior
Quality 25% Inspection outcomes and defect performance
Cost 15% Adherence to the relevant PO or contract price
Capacity 15% Ability to fulfill ordered quantities
Compliance 10% Recorded compliance-related signals
Disruption 10% Recorded disruption-related signals

The composite score is intended to be on a 0--100 scale. Dimension
calculations use source records rather than the separate ground-truth
labels.

Interpretation notes
Cost is price adherence, not cheapness. The current rule checks
billed unit price against the purchase-order line price.
Capacity is distinct from delivery timing. Capacity should
reflect quantity fulfillment rather than count the same timing
behavior again.
Missing history matters. A default dimension value when no
evidence exists is not proof of strong observed performance. Review
sample counts and confidence metadata alongside scores.
Scores are point-in-time results. The as-of date limits which
business events and system-available records can contribute.
Weights and thresholds are assumptions and should be calibrated with
domain experts before real procurement decisions rely on them.
4. Point-in-time scoring
The implementation applies business-event timing and system-availability
timing when filtering evidence. This is intended to prevent information
learned after the selected as-of date from influencing a historical
score.

The tests include an as-of-date leakage check comparing results with
future information present against results from data truncated to the
relevant point in time.

A historical score must distinguish: - when a business event occurred;
and - when the system learned or recorded that event.

5. Data generation and reproducibility
The generator creates synthetic records with deterministic behavior for
a fixed seed and configuration. Dataset profiles are intended to
represent differing patterns, including reliable suppliers,
deteriorating delivery performance, quality incidents, and incomplete
performance history.

Malformed challenge cases are kept separate from the valid baseline so
invalid records do not need to violate core database constraints.

Generate the dataset from the repository root:

python -c "from src.generator import generate_synthetic_data; generate_synthetic_data()"
The generator writes the database and supporting artifacts under
data/. Check the terminal output and generated files after running it.

For reproducible comparisons, use the same code version, seed, and
configuration. Output may differ if those inputs change.

6. Setup and run
Python 3.10 or newer is recommended. The current development environment
used Python 3.13.

Create a virtual environment (recommended):

python -m venv .venv
Windows PowerShell activation:

.\.venv\Scripts\Activate.ps1
Install dependencies:

python -m pip install -r requirements.txt
Generate data if it is not already present:

python -c "from src.generator import generate_synthetic_data; generate_synthetic_data()"
Run scoring for an explicit as-of date:

python -c "from src.scoring import calculate_supplier_scores; print(calculate_supplier_scores(as_of_date='2026-12-31'))"
The scoring function returns a run identifier. Use that identifier to
inspect the corresponding score rows in SQLite.

7. Tests and validation
Run the test suite:

python -m pytest -v
The tests cover: - SQLite foreign-key enforcement and expected tables. -
Supplier/site/contract and invoice/order-line relationships. -
Inspection quantity constraints. - Requested generation counts and
invalid configurations. - Shipment-to-purchase-order-line consistency. -
Reproducibility and supplier-profile behavior. - Detection of malformed
challenge cases. - Weight validation, score bounds, and score
persistence. - Sparse or missing history. - As-of-date leakage
protection. - Capacity and inspection aggregation. - Partial-delivery
evaluation.

Passing tests provides evidence for tested behaviors only; it does not
prove production readiness or guarantee that all possible data-quality
issues are detected.

8. Database and data-quality notes
The schema defines constraints for key relationships and selected
business rules, including checks on date ordering and inspection
quantities. The tests exercise a subset of these constraints.

The schema defines a quarantine_log table for quarantine-related
records. The current generator exports malformed challenge cases to
data/malformed_cases.json; it does not actively insert those cases
into quarantine_log. Do not treat the table as a populated
quarantine workflow unless that behavior is implemented and tested.

The ground-truth artifact is intended for evaluating synthetic challenge
cases. It should not be used as an input to the scoring calculation.

9. Project structure
supplier_scoring/
├── data/
│   ├── ground_truth.json
│   ├── malformed_cases.json
│   ├── schema.sql
│   └── supplier_scoring.db
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── generator.py
│   └── scoring.py
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_generator.py
│   └── test_scoring.py
├── requirements.txt
└── README.md
This describes the expected layout. If the SQLite database is excluded
from version control, recreate it with the generation command above.

10. Dependencies
The current requirements.txt lists: - pytest --- automated tests. -
pandas --- data handling.

SQLite support is available through Python's standard library in typical
Python installations.

11. Limitations and next improvements
The data is synthetic and cannot establish real-world supplier
performance.
Weights, defaults, confidence thresholds, and business rules need
stakeholder review and calibration.
A default score for a dimension with no evidence should be read
together with sample counts and confidence, not as demonstrated
strong performance.
The quarantine table exists in the schema, but the current
malformed-case export path writes JSON rather than populating that
table.
A production version would need operational monitoring, access
controls, retention rules, documented policy ownership, and review
of how scores affect supplier decisions.
Add validation tests whenever new record types, lifecycle
transitions, or scoring rules are introduced.
12. Design priorities
Reproducibility: use a consistent seed and configuration.
Traceability: retain source entities and persisted score-run
results.
Point-in-time correctness: avoid using information unavailable
at the selected scoring date.
Data integrity: use relational constraints and tests to catch
invalid relationships.
Explicit limitations: distinguish observed evidence from
defaults and synthetic evaluation labels.
Quick start
python -m pip install -r requirements.txt
python -c "from src.generator import generate_synthetic_data; generate_synthetic_data()"
python -m pytest -v
python -c "from src.scoring import calculate_supplier_scores; print(calculate_supplier_scores(as_of_date='2026-12-31'))"
⋮⋮⋮⋮⋮⋮⋮⋮