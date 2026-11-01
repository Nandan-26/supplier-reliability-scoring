# Reconstructed Prompt 5 — Evaluation, Ground Truth, and Testing

I want to evaluate the supplier reliability scoring engine and verify that it identifies unreliable suppliers correctly.

Please implement a separate evaluation process without allowing ground-truth labels to influence scoring.

1. Keep ground-truth data separate from operational source tables and scoring features.

2. Define a documented rule for converting the generated supplier behavior into reliable/unreliable ground-truth labels. Explain the thresholds and assumptions.

3. Create an evaluation module that compares the final supplier decisions against the independent ground-truth labels.

4. Calculate and report:
   - True positives
   - False positives
   - True negatives
   - False negatives
   - Precision
   - Recall
   - F1-score
   - Accuracy
   - Confusion matrix

5. Handle division-by-zero cases safely and document how missing or unclassified suppliers are treated.

6. Create an independent synthetic holdout dataset using a different fixed seed. Do not tune scoring thresholds using the holdout labels.

7. Define clear evaluation acceptance criteria. Make the thresholds configurable and explain why they are appropriate for this synthetic project.

8. Add tests for metric calculations, label separation, reproducibility, holdout independence, and edge cases.

9. Save evaluation results as machine-readable JSON and provide a concise human-readable summary.

10. Ensure the evaluation process can be reproduced using documented commands.

11. Update README documentation to distinguish development evaluation from independent holdout evaluation. Explain that synthetic results do not establish real-world predictive performance.

Show complete changed files and exact PowerShell commands. Run tests if possible, and do not claim that anything passed unless you actually ran it.