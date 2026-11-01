> **AI tool:** Gemini (identified by the candidate). **Record status:** original prompt text.

# Original Prompt 2 — Synthetic Data Generator

The database setup is now working on my PC. I ran `python -m src.db` successfully, and all 6 database tests passed.

Now I want to build the synthetic data generator for my supplier reliability scoring project. Please work with the schema and files we have already created instead of redesigning everything.

Please implement it step by step:

1. Create `src/generator.py` to generate realistic synthetic data for 1,000 suppliers, 10,000 purchase orders, 15,000 shipments, and 20,000 inspections. Make the target counts configurable so I can also run smaller datasets while developing.

2. Use a fixed random seed, defaulting to `20261022`, so repeated runs with the same configuration produce identical data. Make sure generated IDs, dates, relationships, and values are reproducible too.

3. Generate realistic differences between suppliers. Include generally reliable suppliers, suppliers with deteriorating delivery performance, suppliers with quality problems, and suppliers with incomplete performance history. Don't assign random labels that have no relationship to their generated behavior.

4. Generate valid baseline records first. Respect all the foreign keys, quantity constraints, lifecycle rules, and date rules in our existing schema. Handle multiple shipments and delivery events without double-counting the same PO line later during scoring.

5. Make the data useful for all six scoring dimensions: delivery, quality, cost, capacity, compliance, and disruption. Include enough contract, invoice, quantity, inspection, and risk-event information to calculate those dimensions from source records.

6. Keep the hidden supplier profiles and anomaly ground truth separate from the source tables used by the scoring engine. Save ground truth in a separate file, and make sure the scorer will not need to read it. Ground-truth labels should be based on documented generation rules, not used as input features.

7. Create separate malformed test cases for issues such as shipments without a valid PO relationship, impossible delivery dates, future information leakage, risk signals with missing source or timing, and inconsistent supplier-site relationships. Keep these cases separate from valid baseline records so they can be tested by a validator and quarantined.

8. Add validation and summary output showing actual table counts, foreign-key violations, invalid date or quantity checks, and generated anomaly-case counts. If anything fails validation, report it clearly rather than silently ignoring it.

9. Add tests in `tests/test_generator.py` for small dataset generation, valid foreign-key relationships, expected counts, fixed-seed reproducibility, and separation of ground truth from scoring inputs. Include tests for malformed cases being detected by validation rather than trusted simply because of labels.

10. Update `requirements.txt` and `README.md` only if needed. Explain the folder structure and give me exact PowerShell commands to generate a small dataset, run the tests, and then generate the full dataset.

Please keep the implementation understandable to a beginner. Show the complete contents of every new or changed file, explain the important decisions, and tell me which commands to run and what output I should expect.

Do not implement the scoring engine yet. First, make the generator reliable, testable, and compatible with the database schema we already have.