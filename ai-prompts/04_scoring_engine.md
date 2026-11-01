> **AI tool:** Not verified from the retained record. **Record status:** reconstructed summary; not a verbatim historical prompt. See [the prompt-history README](README.md).

# Reconstructed Prompt 4 — Supplier Reliability Scoring Engine

The synthetic data generator and database are now ready. I want to implement the supplier reliability scoring engine using the existing project structure, database schema, and generated source data.

Please follow these requirements:

1. Create a modular scoring engine that calculates six independent dimensions:
   - Delivery performance
   - Quality performance
   - Cost performance
   - Capacity performance
   - Compliance performance
   - Disruption risk

2. Use documented scoring formulas and configurable weights. Start with these weights:
   - Delivery: 25%
   - Quality: 25%
   - Cost: 15%
   - Capacity: 15%
   - Compliance: 10%
   - Disruption: 10%

3. Ensure the weights add up to 100%. Validate the configuration and reject invalid weights.

4. Calculate scores using only operational source records. Never use hidden supplier profiles, ground-truth labels, or anomaly labels as scoring inputs.

5. Implement point-in-time scoring. A supplier's score for a given date must use only information available on or before that date. Consider both event dates and system availability timestamps to prevent future-data leakage.

6. Handle missing data explicitly. Do not treat missing performance history as perfect performance. Use a documented neutral fallback and expose a confidence or data-completeness indicator.

7. Make scoring deterministic. Identical source data, configuration, and scoring dates must produce identical results.

8. Save individual dimension scores, the overall score, confidence information, scoring date, and scoring run metadata in the database.

9. Keep scoring logic modular and beginner-friendly. Separate data retrieval, dimension calculations, aggregation, and persistence into understandable functions.

10. Add unit and integration tests covering score ranges, weight validation, missing data, reproducibility, point-in-time correctness, and exclusion of ground-truth information.

11. Update the README and data dictionary to explain the formulas, assumptions, limitations, and how to run the scoring engine.

Show all complete changed files and exact PowerShell commands. Run the tests if possible, and report only results you actually verify.